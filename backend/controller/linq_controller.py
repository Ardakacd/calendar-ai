import hashlib
import hmac
import json
import logging
import time

from fastapi import APIRouter, BackgroundTasks, HTTPException, Request
from sqlalchemy.dialects.postgresql import insert as pg_insert

from config import settings
from database.config import get_async_db_context_manager
from database.models.webhook import ProcessedWebhookModel
from flow.builder import _checkpointer
from services.assistant_service import AssistantService
from services.event_service import EventService
from services.linq_service import HELP_TEXT, LinqService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/linq", tags=["linq"])

WEBHOOK_TOLERANCE_SECONDS = 300  # reject requests older than 5 minutes


def _verify_signature(raw_body: bytes, timestamp: str, signature: str) -> None:
    """Verify Linq webhook signature. Raises 401 if invalid."""
    if not settings.LINQ_SIGNING_SECRET:
        return  # skip verification in dev when secret is not configured

    message = f"{timestamp}.{raw_body.decode('utf-8')}"
    expected = hmac.new(
        settings.LINQ_SIGNING_SECRET.encode(),
        message.encode(),
        hashlib.sha256,
    ).hexdigest()

    if not hmac.compare_digest(expected, signature):
        raise HTTPException(status_code=401, detail="Invalid webhook signature")

    if abs(time.time() - float(timestamp)) > WEBHOOK_TOLERANCE_SECONDS:
        raise HTTPException(status_code=401, detail="Webhook timestamp too old")


# ---------------------------------------------------------------------------
# Background task — runs after 200 is returned to Linq
# ---------------------------------------------------------------------------

WELCOME_TEXT = (
    "Hey! I'm your AI calendar assistant 👋\n\n"
    "Just message me naturally to manage your schedule:\n"
    "• \"Schedule a meeting tomorrow at 3pm\"\n"
    "• \"Move my 2pm to Friday\"\n"
    "• \"What do I have this week?\"\n"
    "• \"Delete my dentist appointment\"\n\n"
    "Type help anytime to see all commands."
)

WELCOME_TEXT_SMS = (
    "Hey! I'm your AI calendar assistant 👋\n\n"
    "Just message me naturally to manage your schedule:\n"
    "• \"Schedule a meeting tomorrow at 3pm\"\n"
    "• \"Move my 2pm to Friday\"\n"
    "• \"What do I have this week?\"\n"
    "• \"Delete my dentist appointment\"\n\n"
    "Already have an account? Type:\n"
    "link <your-email>\n"
    "to connect this number to your existing account.\n\n"
    "Type help anytime to see all commands."
)


async def _handle_chat_created(chat_id: str, phone_number: str) -> None:
    async with get_async_db_context_manager() as db:
        linq_service = LinqService(db)
        try:
            user = await linq_service.get_or_create_user(phone_number)
            if user.linq_chat_id != chat_id:
                from models import UserUpdate
                await linq_service.user_adapter.update_user(user.id, UserUpdate(linq_chat_id=chat_id))
            welcome = WELCOME_TEXT_SMS if phone_number.startswith("+") else WELCOME_TEXT
            await linq_service.send_message(chat_id, welcome)
        except Exception as e:
            logger.error(f"Error sending welcome to {phone_number}: {e}", exc_info=True)
            try:
                await linq_service.send_message(chat_id, "Something went wrong getting started. Please send a message to try again.")
            except Exception:
                pass


async def _handle_message_failed(message_id: str, chat_id: str, error: str) -> None:
    logger.error(f"Linq message delivery failed: message_id={message_id} chat_id={chat_id} error={error}")


async def _handle_message(chat_id: str, phone_number: str, text: str) -> None:
    async with get_async_db_context_manager() as db:
        linq_service = LinqService(db)
        event_service = EventService(db)
        assistant_service = AssistantService(event_service)

        await linq_service.start_typing(chat_id)
        try:
            user = await linq_service.get_or_create_user(phone_number)
            # Persist chat_id so we can send proactive messages (e.g. morning summary)
            if user.linq_chat_id != chat_id:
                from models import UserUpdate
                await linq_service.user_adapter.update_user(user.id, UserUpdate(linq_chat_id=chat_id))

            # ---- Built-in commands ----------------------------------------
            lower = text.strip().lower()

            if lower == "help":
                reply = HELP_TEXT

            elif lower in ("start", "welcome", "hi", "hello"):
                reply = WELCOME_TEXT_SMS if phone_number.startswith("+") else WELCOME_TEXT

            elif lower.startswith("link "):
                email = text.strip()[len("link "):].strip()
                ok = await linq_service.link_account(user.id, email, phone_number)
                reply = (
                    f"Linked! Your phone is now connected to {email}. "
                    "Future messages will use that account."
                    if ok
                    else f"No account found for {email}. Make sure you're using the email you registered with."
                )

            elif lower.startswith("set password "):
                pwd = text.strip()[len("set password "):]
                ok = await linq_service.update_user_password(user.id, pwd)
                if ok:
                    reply = (
                        f"Password set! Log in to the app with:\n"
                        f"Email: {user.email}\n"
                        f"Password: (the one you just set)"
                    )
                else:
                    reply = "Password must be at least 6 characters. Please try again."

            elif lower.startswith("set timezone "):
                tz = text.strip()[len("set timezone "):]
                ok = await linq_service.update_user_timezone(user.id, tz)
                reply = (
                    f"Timezone updated to {tz}."
                    if ok
                    else f"Unknown timezone '{tz}'. Use an IANA name like 'America/Chicago'."
                )

            elif lower in ("reset", "clear"):
                thread_id = str(user.id)
                _checkpointer.storage.pop(thread_id, None)
                _checkpointer.writes.pop(thread_id, None)
                reply = "Conversation history cleared. Starting fresh!"

            else:
                # ---- Run the AI agent ------------------------------------
                dt_context = linq_service.build_datetime_context(user.timezone)
                result = await assistant_service.process_for_user(
                    user_id=user.id,
                    text=text,
                    **dt_context,
                )
                reply = result.get("message") or "I couldn't process that. Please try again."

                # Append formatted event list for LIST responses
                events = result.get("events")
                if events:
                    lines = ["\n"]
                    for e in events:
                        lines.append(f"• {e['title']} — {e['startDate']}")
                    reply += "\n".join(lines)

        except Exception as e:
            logger.error(f"Error handling Linq message from {phone_number}: {e}", exc_info=True)
            reply = "Something went wrong. Please try again in a moment."
        finally:
            await linq_service.stop_typing(chat_id)

        reply = (reply or "").strip() or "Something went wrong. Please try again in a moment."
        logger.info(f"Sending reply to {phone_number}: {repr(reply[:80])}")

        try:
            await linq_service.send_message(chat_id, reply)
        except Exception as e:
            logger.error(f"Failed to send reply to {phone_number} (chat={chat_id}): {e}", exc_info=True)


# ---------------------------------------------------------------------------
# Webhook deduplication
# ---------------------------------------------------------------------------

async def _mark_processed(event_id: str) -> bool:
    """
    Atomically insert event_id into processed_webhooks.
    Returns True if this is the first time we've seen it (should process),
    False if it's a duplicate (should skip).
    """
    async with get_async_db_context_manager() as db:
        stmt = (
            pg_insert(ProcessedWebhookModel)
            .values(event_id=event_id)
            .on_conflict_do_nothing(index_elements=["event_id"])
        )
        result = await db.execute(stmt)
        await db.commit()
        return result.rowcount == 1


# ---------------------------------------------------------------------------
# Webhook endpoint
# ---------------------------------------------------------------------------

@router.post("/webhook")
async def webhook(request: Request, background_tasks: BackgroundTasks):
    """
    Receive incoming iMessage/SMS events from Linq.
    Returns 200 immediately; processing happens in a background task.
    """
    raw_body = await request.body()
    timestamp = request.headers.get("X-Webhook-Timestamp", "")
    signature = request.headers.get("X-Webhook-Signature", "")
    _verify_signature(raw_body, timestamp, signature)

    body = json.loads(raw_body)
    event = body.get("event_type")
    event_id = body.get("event_id")
    data = body.get("data", {})
    logger.info(f"Linq webhook received: event={event} event_id={event_id} trace={body.get('trace_id')}")

    # Deduplicate — Linq delivers at-least-once; skip already-processed events
    if event_id:
        is_new = await _mark_processed(event_id)
        if not is_new:
            logger.info(f"Duplicate webhook ignored: event_id={event_id}")
            return {"status": "duplicate"}

    # ---- message.received ------------------------------------------------
    if event == "message.received":
        chat_id = data.get("chat", {}).get("id")
        phone_number = data.get("sender_handle", {}).get("handle")

        parts = data.get("parts", [])
        text = " ".join(
            p.get("value", "") for p in parts if p.get("type") == "text"
        ).strip()

        if not chat_id or not phone_number or not text:
            logger.warning(f"Linq webhook missing required fields: chat_id={chat_id} phone={phone_number} text={bool(text)}")
            return {"status": "ignored"}

        background_tasks.add_task(_handle_message, chat_id, phone_number, text)

    # ---- chat.created ----------------------------------------------------
    elif event == "chat.created":
        chat_id = data.get("id")
        handles = data.get("handles", [])
        phone_number = next(
            (h.get("handle") for h in handles if not h.get("is_me") and h.get("handle")),
            None,
        )

        if not chat_id or not phone_number:
            logger.warning(f"chat.created missing fields: chat_id={chat_id} phone={phone_number}")
            return {"status": "ignored"}

        background_tasks.add_task(_handle_chat_created, chat_id, phone_number)

    # ---- message.failed --------------------------------------------------
    elif event == "message.failed":
        background_tasks.add_task(
            _handle_message_failed,
            message_id=data.get("id"),
            chat_id=data.get("chat", {}).get("id"),
            error=data.get("error") or "unknown",
        )

    else:
        return {"status": "ignored"}

    return {"status": "ok"}
