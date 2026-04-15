"""
Event Reminder Service

Runs every 5 minutes via APScheduler.
Sends a push notification to users whose events start in ~15 minutes
and have not already received a reminder.
"""

import logging
from datetime import datetime, timezone, timedelta
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
from typing import Optional

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception

from database.config import get_async_db_context_manager
from adapter.event_adapter import EventAdapter

logger = logging.getLogger(__name__)

EXPO_PUSH_URL = "https://exp.host/--/api/v2/push/send"
REMINDER_WINDOW_MINUTES = 15
REMINDER_LOOKAHEAD_MINUTES = 5   # must match the APScheduler interval
EXPO_BATCH_SIZE = 100            # Expo hard limit per request

# Expo per-message error codes that indicate a permanently invalid token.
# These should NOT be retried — the token must be cleared from the DB.
_PERMANENT_EXPO_ERRORS = {"DeviceNotRegistered", "InvalidCredentials"}


def _format_time(dt: datetime, user_tz: Optional[str] = None) -> str:
    """Format datetime in the user's local timezone (falls back to UTC if unknown)."""
    if user_tz:
        try:
            dt = dt.astimezone(ZoneInfo(user_tz))
        except (ZoneInfoNotFoundError, KeyError):
            pass
    elif dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    hour = dt.hour % 12 or 12
    minute = dt.strftime("%M")
    ampm = "AM" if dt.hour < 12 else "PM"
    return f"{hour}:{minute} {ampm}"


def _is_retryable_error(exc: BaseException) -> bool:
    """
    Only retry on network/timeout errors and 5xx responses.
    4xx from Expo (e.g. 400 Bad Request) indicate a request format problem
    that won't be resolved by retrying — don't waste attempts on them.
    """
    if isinstance(exc, httpx.HTTPStatusError):
        return exc.response.status_code >= 500
    return isinstance(exc, (httpx.TransportError, httpx.TimeoutException))


@retry(
    retry=retry_if_exception(_is_retryable_error),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    stop=stop_after_attempt(3),
    reraise=True,
)
async def _send_batch(batch: list[dict]) -> tuple[list[int], list[int]]:
    """
    Send one Expo push batch (≤100 messages).

    Returns (retryable_failed_indices, permanent_failed_indices):
      - retryable: transient failures — claim will be reverted so next tick retries
      - permanent: DeviceNotRegistered / InvalidCredentials — claim stays (no retry),
                   push token will be cleared from the DB

    Raises on 5xx / network errors → tenacity retries up to 3 times.
    4xx responses are NOT retried (bad request format won't be fixed by retry).
    """
    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.post(
            EXPO_PUSH_URL,
            json=batch,
            headers={"Content-Type": "application/json", "Accept": "application/json"},
        )
        resp.raise_for_status()

    retryable: list[int] = []
    permanent: list[int] = []

    for i, item in enumerate(resp.json().get("data", [])):
        if item.get("status") == "ok":
            continue
        error_code = item.get("details", {}).get("error", "")
        msg = item.get("message", "")
        if error_code in _PERMANENT_EXPO_ERRORS:
            logger.warning(f"Expo push message {i}: permanent failure ({error_code}) — token will be cleared")
            permanent.append(i)
        else:
            logger.warning(f"Expo push message {i}: transient failure — {msg} ({error_code})")
            retryable.append(i)

    return retryable, permanent


async def _send_push_notifications(
    messages: list[dict], event_ids: list[str]
) -> tuple[list[str], list[str]]:
    """
    Send all messages in EXPO_BATCH_SIZE chunks.

    Returns (ids_to_revert, ids_to_clear_token):
      - ids_to_revert: transient failures + full HTTP failures — claim reverted for retry
      - ids_to_clear_token: permanent device failures — token cleared, claim kept (no retry)

    Batch 1 success + batch 2 HTTP failure → only batch 2 IDs in ids_to_revert,
    preventing duplicate notifications for batch 1.
    """
    ids_to_revert: list[str] = []
    ids_to_clear_token: list[str] = []

    for batch_start in range(0, len(messages), EXPO_BATCH_SIZE):
        batch_msgs = messages[batch_start : batch_start + EXPO_BATCH_SIZE]
        batch_ids = event_ids[batch_start : batch_start + EXPO_BATCH_SIZE]

        try:
            retryable_indices, permanent_indices = await _send_batch(batch_msgs)
            for i in retryable_indices:
                ids_to_revert.append(batch_ids[i])
            for i in permanent_indices:
                ids_to_clear_token.append(batch_ids[i])
        except Exception as e:
            # HTTP-level failure after all retries: entire batch is retryable
            logger.error(
                f"Batch starting at index {batch_start} failed entirely after retries: {e}",
                exc_info=True,
            )
            ids_to_revert.extend(batch_ids)

    return ids_to_revert, ids_to_clear_token


async def send_event_reminders() -> None:
    """
    Main job — run every 5 minutes.
    Atomically claims unclaimed events in the reminder window, closes the DB session,
    sends push notifications, then:
      - Reverts claims for transient failures so the next tick retries them.
      - Clears stale push tokens for permanent device failures (DeviceNotRegistered).
    """
    now = datetime.now(timezone.utc)
    window_start = now + timedelta(minutes=REMINDER_WINDOW_MINUTES)
    window_end = now + timedelta(minutes=REMINDER_WINDOW_MINUTES + REMINDER_LOOKAHEAD_MINUTES)

    logger.info(
        f"Reminder job: checking events between "
        f"{window_start.strftime('%H:%M')} and {window_end.strftime('%H:%M')} UTC"
    )

    # Claim events atomically — DB session closed before any HTTP call
    async with get_async_db_context_manager() as db:
        adapter = EventAdapter(db)
        triples = await adapter.claim_and_get_reminder_events(window_start, window_end)

    if not triples:
        logger.info("Reminder job: no events to remind")
        return

    messages: list[dict] = []
    event_ids: list[str] = []

    for event, push_token, user_tz in triples:
        time_str = _format_time(event.startDate, user_tz)
        messages.append({
            "to": push_token,
            "title": f"⏰ {event.title}",
            "body": f"Starting at {time_str} — in about {REMINDER_WINDOW_MINUTES} minutes",
            "sound": "default",
            "data": {"event_id": event.id},
        })
        event_ids.append(event.id)

    ids_to_revert, ids_to_clear_token = await _send_push_notifications(messages, event_ids)

    sent_count = len(event_ids) - len(ids_to_revert) - len(ids_to_clear_token)
    logger.info(
        f"Reminder job: {sent_count}/{len(event_ids)} sent, "
        f"{len(ids_to_revert)} transient failure(s), "
        f"{len(ids_to_clear_token)} permanent failure(s)"
    )

    if ids_to_revert or ids_to_clear_token:
        async with get_async_db_context_manager() as db:
            adapter = EventAdapter(db)
            if ids_to_revert:
                await adapter.revert_reminder_claims(ids_to_revert)
            if ids_to_clear_token:
                await adapter.clear_push_tokens_for_events(ids_to_clear_token)
