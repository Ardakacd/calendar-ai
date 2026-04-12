import hashlib
import hmac
import json
import logging
import time
from datetime import datetime
from urllib.parse import quote
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


def _handle_label(handle: str) -> str:
    """Return a non-reversible 8-char hex label for a phone/email handle — keeps PII out of logs."""
    return hashlib.sha256(handle.encode()).hexdigest()[:8]

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


def _calendar_event_app_url(event_id: str) -> str:
    """Custom-scheme deep link (mobile app registers scheme `calendarai`)."""
    return f"calendarai://calendar?eventId={quote(event_id, safe='')}"


def _is_sms_synthetic_email(email: str | None) -> bool:
    """Phone-SMS auto-created users get {digits}@sms.linqapp.com — not a mailbox they know until we show it."""
    return bool(email and email.strip().lower().endswith("@sms.linqapp.com"))


def _apple_id_style_handle(phone_number: str) -> bool:
    """Linq handle is a real email (e.g. user@icloud.com), not a +E.164 phone mapped to @sms.linqapp.com."""
    if "@" not in phone_number:
        return False
    return not phone_number.strip().lower().endswith("@sms.linqapp.com")


def _welcome_for_handle(phone_number: str) -> str:
    """Shorter app hints for Apple ID / iCloud handles; full guidance for SMS phone users."""
    if _apple_id_style_handle(phone_number):
        return _WELCOME_BODY + _WELCOME_APP_HINT_APPLE
    return WELCOME_TEXT


def _format_event_dt(iso: str, user_tz: str | None) -> str:
    """Format an ISO datetime string for display in the user's local timezone."""
    try:
        dt = datetime.fromisoformat(iso)
        if user_tz:
            try:
                dt = dt.astimezone(ZoneInfo(user_tz))
            except (ZoneInfoNotFoundError, KeyError):
                pass
        h = dt.hour % 12 or 12
        minute = dt.strftime("%M")
        ampm = "AM" if dt.hour < 12 else "PM"
        day_str = dt.strftime("%a %b") + f" {dt.day}"
        return f"{day_str} {h}:{minute} {ampm}"
    except Exception:
        return iso


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

_WELCOME_BODY = (
    "Hey! I'm your AI calendar assistant 👋\n\n"
    "Just message me naturally to manage your schedule:\n"
    "• \"Schedule a meeting tomorrow at 3pm\"\n"
    "• \"Move my 2pm to Friday\"\n"
    "• \"What do I have this week?\"\n"
    "• \"Delete my dentist appointment\"\n\n"
)

_WELCOME_APP_HINT = (
    "— Calendar AI app —\n"
    "Already signed up in the app? Type:\n"
    "link <your-email>\n"
    "(connects this chat to that account.)\n\n"
    "New to the app? Set a password, then log in with the same email we show you:\n"
    "set password <your-password>\n"
    "(After that, type my email anytime to copy your login email.)\n\n"
    "Type help anytime to see all commands."
)

# iMessage / Apple ID handles: login email is already their handle — less copy than SMS synthetic path
_WELCOME_APP_HINT_APPLE = (
    "— Calendar AI app —\n"
    "Already use the app? Type: link <your-email> to connect this chat.\n"
    "Need a password for the app? Type: set password <your-password>\n\n"
    "Type help anytime to see all commands."
)

WELCOME_TEXT = _WELCOME_BODY + _WELCOME_APP_HINT


async def _handle_chat_created(chat_id: str, phone_number: str, event_id: str | None) -> None:
    if event_id and not await _mark_processed(event_id):
        logger.info(f"Duplicate chat.created ignored: event_id={event_id}")
        return
    label = _handle_label(phone_number)
    async with get_async_db_context_manager() as db:
        linq_service = LinqService(db)
        try:
            user = await linq_service.get_or_create_user(phone_number)
            if user.linq_chat_id != chat_id:
                from models import UserUpdate
                await linq_service.user_adapter.update_user(user.id, UserUpdate(linq_chat_id=chat_id))
            await linq_service.send_message(chat_id, _welcome_for_handle(phone_number))
        except Exception as e:
            logger.error(f"Error sending welcome [{label}]: {e}", exc_info=True)
            try:
                await linq_service.send_message(chat_id, "Something went wrong getting started. Please send a message to try again.")
            except Exception:
                pass


async def _handle_message_failed(message_id: str, error: str, event_id: str | None) -> None:
    if event_id and not await _mark_processed(event_id):
        return
    logger.error(f"Linq message delivery failed: message_id={message_id} error={error}")


async def _handle_message(chat_id: str, phone_number: str, text: str, event_id: str | None) -> None:
    if event_id and not await _mark_processed(event_id):
        logger.info(f"Duplicate message.received ignored: event_id={event_id}")
        return

    label = _handle_label(phone_number)
    reply = "Something went wrong. Please try again in a moment."
    reply_effect: str | None = None
    linq_svc = None

    async with get_async_db_context_manager() as db:
        linq_svc = LinqService(db)

        # Show typing bubble and mark as read immediately — before any processing
        await linq_svc.start_typing(chat_id)
        await linq_svc.mark_read(chat_id)

        # Dedup check — bubble already visible so user sees activity during DB call
        if event_id and not await _mark_processed(event_id):
            logger.info(f"Duplicate message.received ignored: event_id={event_id}")
            await linq_svc.stop_typing(chat_id)
            return

        event_service = EventService(db)
        assistant_service = AssistantService(event_service)

        try:
            user = await linq_svc.get_or_create_user(phone_number)
            # Persist chat_id so we can send proactive messages (e.g. morning summary)
            if user.linq_chat_id != chat_id:
                from models import UserUpdate
                await linq_svc.user_adapter.update_user(user.id, UserUpdate(linq_chat_id=chat_id))

            # ---- Built-in commands ----------------------------------------
            lower = text.strip().lower()

            if lower == "help":
                reply = HELP_TEXT

            elif lower in ("start", "welcome", "hi", "hello"):
                reply = _welcome_for_handle(phone_number)

            elif lower == "my email":
                em = (user.email or "").strip() or "(none on file)"
                if _is_sms_synthetic_email(em):
                    reply = (
                        "Your app login email (copy this into Calendar AI):\n"
                        f"{em}\n\n"
                        "You need a password before sign-in works. If you haven’t set one yet, send:\n"
                        "set password <your-password>\n"
                        "Then open the app and sign in with this email and that password.\n\n"
                        "Already have an account under another email? Use link <that-email> instead."
                    )
                else:
                    reply = (
                        "Your app login email (copy this into Calendar AI):\n"
                        f"{em}\n\n"
                        "Use this email with your app password. "
                        "If you haven’t set one yet, send: set password <your-password>\n\n"
                        "Already have an account under a different email? Use: link <that-email>"
                    )

            elif lower.startswith("link "):
                email = text.strip()[len("link "):].strip()
                ok = await linq_svc.link_account(user.id, email, phone_number)
                reply = (
                    (
                        f"Linked! Your phone is now connected to {email}. "
                        "Future messages will use that account.\n\n"
                        "Log in to the Calendar AI app with:\n"
                        f"Email: {email}\n"
                        "Password: the one you use for that account. "
                        "If you haven’t set an app password yet, send: set password <your-password>"
                    )
                    if ok
                    else f"No account found for {email}. Make sure you're using the email you registered with."
                )

            elif lower.startswith("set password "):
                pwd = text.strip()[len("set password "):]
                ok = await linq_svc.update_user_password(user.id, pwd)
                if ok:
                    reply = (
                        "Password set! Open Calendar AI and sign in with:\n"
                        f"Email: {user.email}\n"
                        "Password: the one you just sent above.\n\n"
                        "Already have an account in the app under a different email? "
                        "Use link <that-email> next time instead — that merges this chat into your existing account.\n\n"
                        "Need the email line again? Type: my email"
                    )
                else:
                    reply = "Password must be at least 6 characters. Please try again."

            elif lower.startswith("set timezone "):
                tz = text.strip()[len("set timezone "):]
                ok = await linq_svc.update_user_timezone(user.id, tz)
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
                dt_context = linq_svc.build_datetime_context(user.timezone)
                result = await assistant_service.process_for_user(
                    user_id=user.id,
                    text=text,
                    **dt_context,
                )
                reply = result.get("message") or "I couldn't process that. Please try again."

                if result.get("type") == "create":
                    reply_effect = "confetti"

                # Append formatted event list for LIST responses
                events = result.get("events")
                if events:
                    lines = ["\n"]
                    for e in events:
                        time_str = _format_event_dt(e["startDate"], user.timezone)
                        eid = e.get("id")
                        if eid:
                            lines.append(
                                f"• {e['title']} — {time_str}\n"
                                f"  {_calendar_event_app_url(eid)}"
                            )
                        else:
                            lines.append(f"• {e['title']} — {time_str}")
                    reply += "\n".join(lines)

        except Exception as e:
            logger.error(f"Error handling Linq message [{label}]: {e}", exc_info=True)
            reply = "Something went wrong. Please try again in a moment."

    # DB session is now closed — send_message and stop_typing use HTTP headers only.
    reply = (reply or "").strip() or "Something went wrong. Please try again in a moment."
    logger.info(f"Sending reply [{label}]: {repr(reply[:80])}")
    try:
        await linq_svc.send_message(chat_id, reply, screen_effect=reply_effect)
    except Exception as e:
        logger.error(f"Failed to send reply [{label}] (chat={chat_id}): {e}", exc_info=True)
    finally:
        # Stop bubble only after message is sent (or failed) — bubble stays up the entire time
        await linq_svc.stop_typing(chat_id)


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
    webhook_version = body.get("webhook_version", "2025-01-01")
    logger.info(f"Linq webhook received: event={event} event_id={event_id} version={webhook_version} trace={body.get('trace_id')}")

    # ---- message.received ------------------------------------------------
    if event == "message.received":
        # Normalize v2025-01-01 layout to v2026-02-03 shape so the rest of the
        # handler is version-agnostic.
        if webhook_version < "2026-02-03":
            chat_id = data.get("chat_id")
            phone_number = (data.get("from_handle") or {}).get("handle") or data.get("from")
            parts = (data.get("message") or {}).get("parts", [])
        else:
            chat_id = (data.get("chat") or {}).get("id")
            phone_number = (data.get("sender_handle") or {}).get("handle")
            parts = data.get("parts", [])

        text = " ".join(
            p.get("value", "") for p in parts if p.get("type") == "text"
        ).strip()

        if not chat_id or not phone_number or not text:
            logger.warning(f"Linq webhook missing required fields: chat_id={chat_id} phone={bool(phone_number)} text={bool(text)}")
            return {"status": "ignored"}

        background_tasks.add_task(_handle_message, chat_id, phone_number, text, event_id)

    # ---- chat.created ----------------------------------------------------
    elif event == "chat.created":
        chat_id = data.get("id")
        handles = data.get("handles", [])
        phone_number = next(
            (h.get("handle") for h in handles if not h.get("is_me") and h.get("handle")),
            None,
        )

        if not chat_id or not phone_number:
            logger.warning(f"chat.created missing fields: chat_id={chat_id} phone={bool(phone_number)}")
            return {"status": "ignored"}

        background_tasks.add_task(_handle_chat_created, chat_id, phone_number, event_id)

    # ---- message.failed --------------------------------------------------
    elif event == "message.failed":
        code = data.get("code")
        background_tasks.add_task(
            _handle_message_failed,
            message_id=data.get("message_id"),
            error=data.get("reason") or (str(code) if code is not None else "unknown"),
            event_id=event_id,
        )

    # ---- message.delivered -----------------------------------------------
    elif event == "message.delivered":
        logger.info(
            f"Linq message delivered: message_id={data.get('message_id')} "
            f"chat={data.get('chat_id')} event_id={event_id}"
        )

    # ---- message.read ----------------------------------------------------
    elif event == "message.read":
        logger.info(
            f"Linq message read: chat={data.get('chat_id')} "
            f"message_id={data.get('message_id')} event_id={event_id}"
        )

    else:
        return {"status": "ignored"}

    return {"status": "ok"}
