"""
Morning Summary Service

Sends each Linq user a digest of their day's events at 8 AM in their local timezone.
Called every hour by APScheduler; skips users whose summary was already sent today.
"""

import logging
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import httpx

from config import settings
from database.config import get_async_db_context_manager
from adapter.user_adapter import UserAdapter
from adapter.event_adapter import EventAdapter

logger = logging.getLogger(__name__)

LINQ_API_BASE = "https://api.linqapp.com/api/partner"

# In-memory set of "user_id:YYYY-MM-DD" keys to avoid double-sending within the same process.
# On server restart this resets, which is fine — the hour check prevents duplicate sends.
_sent_today: set[str] = set()


def _get_user_tz(timezone: str | None) -> ZoneInfo:
    if timezone:
        try:
            return ZoneInfo(timezone)
        except (ZoneInfoNotFoundError, KeyError):
            pass
    return ZoneInfo(settings.LINQ_DEFAULT_TIMEZONE)


def _format_time(dt: datetime, tz: ZoneInfo) -> str:
    local = dt.astimezone(tz)
    return local.strftime("%-I:%M %p")


def _build_summary(events: list, tz: ZoneInfo, user_name: str) -> str:
    name = user_name.split()[0] if user_name else "there"
    today_str = datetime.now(tz).strftime("%A, %B %-d")

    if not events:
        return (
            f"Good morning, {name}! Your calendar is clear today — enjoy the free day."
        )

    lines = [f"Good morning, {name}! Here's your day for {today_str}:\n"]
    for i, event in enumerate(events, 1):
        time_str = _format_time(event.startDate, tz)
        line = f"{i}. {time_str} — {event.title}"
        if event.location:
            line += f" @ {event.location}"
        if event.duration and event.duration > 0:
            hours, mins = divmod(event.duration, 60)
            if hours and mins:
                line += f" ({hours}h {mins}m)"
            elif hours:
                line += f" ({hours}h)"
            else:
                line += f" ({mins}m)"
        lines.append(line)

    lines.append(f"\n{len(events)} event{'s' if len(events) > 1 else ''} today. Have a great day!")
    return "\n".join(lines)


async def _send_linq_message(chat_id: str, text: str) -> None:
    headers = {
        "Authorization": f"Bearer {settings.LINQ_API_TOKEN}",
        "Content-Type": "application/json",
    }
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(
            f"{LINQ_API_BASE}/v3/chats/{chat_id}/messages",
            json={"message": {"parts": [{"type": "text", "value": text}]}},
            headers=headers,
        )
        if resp.status_code not in (200, 201, 202):
            logger.error(f"Morning summary send failed [{resp.status_code}] for chat {chat_id}: {resp.text}")
            resp.raise_for_status()


async def send_morning_summaries() -> None:
    """
    Main job — run every hour. Sends summaries to users whose local time is 8:00–8:59 AM
    and who haven't received one yet today.
    """
    logger.info("Morning summary job running")

    async with get_async_db_context_manager() as db:
        user_adapter = UserAdapter(db)
        event_adapter = EventAdapter(db)
        users = await user_adapter.get_all_linq_users()

    for user in users:
        try:
            tz = _get_user_tz(user.timezone)
            now_local = datetime.now(tz)

            # Only send during the 8 AM hour
            if now_local.hour != 8:
                continue

            dedup_key = f"{user.id}:{now_local.date()}"
            if dedup_key in _sent_today:
                continue

            # Fetch today's events
            day_start = now_local.replace(hour=0, minute=0, second=0, microsecond=0)
            day_end = day_start + timedelta(days=1)

            async with get_async_db_context_manager() as db:
                event_adapter = EventAdapter(db)
                events = await event_adapter.get_events_by_date_range(
                    user.id,
                    start_date=day_start,
                    end_date=day_end,
                )

            # Sort by start time
            events.sort(key=lambda e: e.startDate)

            summary = _build_summary(events, tz, user.name)
            await _send_linq_message(user.linq_chat_id, summary)

            _sent_today.add(dedup_key)
            logger.info(f"Morning summary sent to user {user.id} ({user.phone_number}), {len(events)} events")

        except Exception as e:
            logger.error(f"Failed to send morning summary to user {user.id}: {e}", exc_info=True)
