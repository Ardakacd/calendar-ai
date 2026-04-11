"""
Event Reminder Service

Runs every 5 minutes via APScheduler.
Sends a push notification to users whose events start in ~15 minutes
and have not already received a reminder.
"""

import logging
from datetime import datetime, timezone, timedelta

import httpx

from database.config import get_async_db_context_manager
from adapter.event_adapter import EventAdapter

logger = logging.getLogger(__name__)

EXPO_PUSH_URL = "https://exp.host/--/api/v2/push/send"
REMINDER_WINDOW_MINUTES = 15
REMINDER_LOOKAHEAD_MINUTES = 5  # cron interval — window width must match


def _format_time(dt: datetime) -> str:
    """Format datetime as '3:00 PM' in its own timezone (or UTC if naive)."""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    hour = dt.hour % 12 or 12
    minute = dt.strftime("%M")
    ampm = "AM" if dt.hour < 12 else "PM"
    return f"{hour}:{minute} {ampm}"


async def _send_push_notifications(messages: list[dict]) -> None:
    """Send a batch of Expo push messages (max 100 per call)."""
    if not messages:
        return
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.post(
                EXPO_PUSH_URL,
                json=messages,
                headers={"Content-Type": "application/json", "Accept": "application/json"},
            )
            if resp.status_code not in (200, 201):
                logger.error(f"Expo push failed [{resp.status_code}]: {resp.text[:200]}")
    except Exception as e:
        logger.error(f"Error sending push notifications: {e}", exc_info=True)


async def send_event_reminders() -> None:
    """
    Main job — run every 5 minutes.
    Queries events starting in the next [REMINDER_WINDOW_MINUTES, REMINDER_WINDOW_MINUTES + LOOKAHEAD]
    window that haven't had a reminder sent yet.
    """
    now = datetime.now(timezone.utc)
    window_start = now + timedelta(minutes=REMINDER_WINDOW_MINUTES)
    window_end = now + timedelta(minutes=REMINDER_WINDOW_MINUTES + REMINDER_LOOKAHEAD_MINUTES)

    logger.info(f"Reminder job: checking events between {window_start.strftime('%H:%M')} and {window_end.strftime('%H:%M')} UTC")

    async with get_async_db_context_manager() as db:
        adapter = EventAdapter(db)
        pairs = await adapter.get_upcoming_events_for_reminder(window_start, window_end)

        if not pairs:
            logger.info("Reminder job: no events to remind")
            return

        messages = []
        event_ids = []

        for event, push_token in pairs:
            time_str = _format_time(event.startDate)
            messages.append({
                "to": push_token,
                "title": f"⏰ {event.title}",
                "body": f"Starting at {time_str} — in about {REMINDER_WINDOW_MINUTES} minutes",
                "sound": "default",
                "data": {"event_id": event.id},
            })
            event_ids.append(event.id)

        await _send_push_notifications(messages)
        await adapter.mark_reminders_sent(event_ids)
        logger.info(f"Reminder job: sent {len(messages)} reminder(s)")
