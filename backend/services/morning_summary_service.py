"""
Morning Summary Service

Sends each Linq user a digest of their day's events at 8 AM in their local timezone.
Called every hour by APScheduler; deduplication is DB-backed (summary_sent_date column)
so duplicate sends are prevented even across server restarts.
"""

import asyncio
import logging
import uuid
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception

from config import settings, LINQ_API_BASE
from database.config import get_async_db_context_manager
from adapter.user_adapter import UserAdapter
from adapter.event_adapter import EventAdapter

logger = logging.getLogger(__name__)

# Seconds to wait between individual sends to avoid bursting the Linq line.
_SEND_INTERVAL = 0.5


def _get_user_tz(timezone: str | None) -> ZoneInfo:
    if timezone:
        try:
            return ZoneInfo(timezone)
        except (ZoneInfoNotFoundError, KeyError):
            pass
    return ZoneInfo(settings.LINQ_DEFAULT_TIMEZONE)


def _format_time(dt: datetime, tz: ZoneInfo) -> str:
    """12-hour clock in user's zone — portable (no strftime %-I, which breaks on Windows)."""
    local = dt.astimezone(tz)
    h = local.hour % 12 or 12
    minute = local.strftime("%M")
    ampm = "AM" if local.hour < 12 else "PM"
    return f"{h}:{minute} {ampm}"


def _format_today_heading(tz: ZoneInfo) -> str:
    """e.g. Monday, March 10 — day without leading zero, all platforms."""
    now = datetime.now(tz)
    return f"{now.strftime('%A')}, {now.strftime('%B')} {now.day}"


def _build_summary(events: list, tz: ZoneInfo, user_name: str) -> str:
    name = user_name.split()[0] if user_name else "there"
    today_str = _format_today_heading(tz)

    if not events:
        return f"Good morning, {name}! Your calendar is clear today — enjoy the free day."

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


def _is_retryable(exc: BaseException) -> bool:
    """Retry only on network/transport errors and 5xx responses — not 4xx."""
    if isinstance(exc, httpx.HTTPStatusError):
        return exc.response.status_code >= 500
    return isinstance(exc, (httpx.TransportError, httpx.TimeoutException))


async def _send_linq_message(chat_id: str, text: str) -> None:
    """Send a morning summary message with retry (5xx/network only) and idempotency_key."""
    idempotency_key = str(uuid.uuid4())
    headers = {
        "Authorization": f"Bearer {settings.LINQ_API_TOKEN}",
        "Content-Type": "application/json",
    }

    @retry(
        retry=retry_if_exception(_is_retryable),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        stop=stop_after_attempt(3),
        reraise=True,
    )
    async def _attempt() -> None:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                f"{LINQ_API_BASE}/v3/chats/{chat_id}/messages",
                json={"message": {"parts": [{"type": "text", "value": text}], "idempotency_key": idempotency_key}},
                headers=headers,
            )
            if resp.status_code not in (200, 201, 202):
                logger.error(f"Morning summary send failed [{resp.status_code}] for chat {chat_id}: {resp.text}")
                resp.raise_for_status()

    await _attempt()


async def send_morning_summaries() -> None:
    """
    Main job — run every hour. Sends summaries to users whose local time is 8:00–8:59 AM
    and who haven't received one yet today (checked via DB summary_sent_date column).
    """
    logger.info("Morning summary job running")

    async with get_async_db_context_manager() as db:
        user_adapter = UserAdapter(db)
        users = await user_adapter.get_all_linq_users()

    for user in users:
        claimed = False
        today = None
        try:
            tz = _get_user_tz(user.timezone)
            now_local = datetime.now(tz)

            # Only send during the 8 AM hour
            if now_local.hour != 8:
                continue

            today = now_local.date()

            # Atomically claim this user's summary slot.
            # Returns False if another worker already claimed it — skip to avoid duplicate sends.
            async with get_async_db_context_manager() as db:
                user_adapter = UserAdapter(db)
                claimed = await user_adapter.mark_summary_sent(user.id, today)

            if not claimed:
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

            events.sort(key=lambda e: e.startDate)

            summary = _build_summary(events, tz, user.name)
            await _send_linq_message(user.linq_chat_id, summary)

            logger.info(f"Morning summary sent to user {user.id}, {len(events)} events")

            # Space messages to avoid bursting the Linq line
            await asyncio.sleep(_SEND_INTERVAL)

        except Exception as e:
            if claimed:
                try:
                    async with get_async_db_context_manager() as db:
                        ua = UserAdapter(db)
                        await ua.revert_summary_claim(user.id, today)
                except Exception as rev_err:
                    logger.error(
                        f"Failed to revert summary claim for user {user.id}: {rev_err}",
                        exc_info=True,
                    )
            logger.error(
                f"Failed to send morning summary to user {user.id}: {e}",
                exc_info=True,
            )
