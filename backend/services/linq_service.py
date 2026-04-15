import calendar
import logging
import uuid
from datetime import datetime
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import httpx
from sqlalchemy.ext.asyncio import AsyncSession
from tenacity import AsyncRetrying, retry_if_exception_type, stop_after_attempt, wait_exponential

from adapter.event_adapter import EventAdapter
from adapter.user_adapter import UserAdapter
from config import settings, LINQ_API_BASE
from models import User, UserCreate
from utils.password import get_password_hash

logger = logging.getLogger(__name__)

# Commands users can send via iMessage
HELP_TEXT = (
    "Just message me like you'd text a friend:\n"
    "• \"Add lunch with Sarah tomorrow at noon\"\n"
    "• \"What do I have this week?\"\n"
    "• \"Move my 3pm to Friday\"\n"
    "• \"Cancel tomorrow's meeting\"\n\n"
    "Other commands:\n"
    "• set timezone <tz> — e.g. America/Chicago\n"
    "• reset — clear conversation history\n"
    "• link <email> — connect to the Calen app\n"
    "• set password <pw> — set an app password\n"
    "• my email — show your app login email"
)


class LinqService:

    def __init__(self, db: AsyncSession):
        self.db = db
        self.user_adapter = UserAdapter(db)
        self._headers = {
            "Authorization": f"Bearer {settings.LINQ_API_TOKEN}",
            "Content-Type": "application/json",
        }

    # ------------------------------------------------------------------
    # User management
    # ------------------------------------------------------------------

    async def get_or_create_user(self, phone_number: str) -> User:
        """Return existing user for this phone number, or auto-register one."""
        user = await self.user_adapter.get_user_by_phone(phone_number)
        if user:
            return user

        # Handle can be a phone number (+15551234567) or an iCloud email (user@icloud.com)
        if "@" in phone_number:
            synthetic_email = phone_number
        else:
            digits = phone_number.replace("+", "").replace("-", "").replace(" ", "")
            synthetic_email = f"{digits}@sms.linqapp.com"
        synthetic_password = get_password_hash(uuid.uuid4().hex)

        user_data = UserCreate(
            user_id=str(uuid.uuid4()),
            name=phone_number,
            email=synthetic_email,
            password=synthetic_password,
            phone_number=phone_number,
            timezone=settings.LINQ_DEFAULT_TIMEZONE,
        )

        try:
            created = await self.user_adapter.create_user(user_data)
            if created:
                logger.info(f"Auto-created Linq user for phone: {phone_number}, id: {created.id}")
                return created
        except Exception:
            pass  # race condition — another concurrent request created the user first

        # Re-fetch: concurrent request won the insert race
        user = await self.user_adapter.get_user_by_phone(phone_number)
        if user:
            logger.info(f"Linq user already created by concurrent request for phone: {phone_number}")
            return user

        raise RuntimeError(f"Failed to create or find user for phone: {phone_number}")

    async def link_account(self, sms_user_id: int, email: str, phone_number: str) -> bool:
        """
        Link a phone number to an existing account by email.

        Migrates any events created under the SMS-created user to the target
        account before deleting the temporary account, so no calendar data is lost.
        Returns False if the target account does not exist or already has a
        different phone number associated with it.
        """
        from models import UserUpdate
        target = await self.user_adapter.get_user_by_email(email)
        if not target:
            return False

        # Refuse to overwrite a different phone number already on the target account
        if target.phone_number and target.phone_number != phone_number:
            logger.warning(
                f"Link refused: target user {target.id} already has phone {target.phone_number}"
            )
            return False

        # Migrate events before deleting (cascade would destroy them otherwise)
        event_adapter = EventAdapter(self.db)
        await event_adapter.migrate_events_to_user(sms_user_id, target.id)

        await self.user_adapter.update_user(target.id, UserUpdate(phone_number=phone_number))
        await self.user_adapter.delete_user(sms_user_id)
        return True

    async def update_user_password(self, user_id: int, new_password: str) -> bool:
        """Validate and store a new password for a user."""
        if len(new_password) < 6:
            return False
        from models import UserUpdate
        hashed = get_password_hash(new_password)
        await self.user_adapter.update_user(user_id, UserUpdate(password=hashed))
        return True

    async def update_user_timezone(self, user_id: int, timezone: str) -> bool:
        """Validate and store a new timezone for a user."""
        try:
            ZoneInfo(timezone)
        except (ZoneInfoNotFoundError, KeyError):
            return False
        from models import UserUpdate
        await self.user_adapter.update_user(user_id, UserUpdate(timezone=timezone))
        return True

    # ------------------------------------------------------------------
    # Datetime context (replaces client-side calculation)
    # ------------------------------------------------------------------

    def build_datetime_context(self, timezone: str | None) -> dict:
        tz_name = timezone or settings.LINQ_DEFAULT_TIMEZONE
        try:
            tz = ZoneInfo(tz_name)
        except (ZoneInfoNotFoundError, KeyError):
            tz = ZoneInfo(settings.LINQ_DEFAULT_TIMEZONE)
        now = datetime.now(tz)
        return {
            "current_datetime": now.isoformat(),
            "weekday": now.strftime("%A"),
            "days_in_month": calendar.monthrange(now.year, now.month)[1],
        }

    # ------------------------------------------------------------------
    # Linq API calls
    # ------------------------------------------------------------------

    async def send_message(self, chat_id: str, text: str, screen_effect: str | None = None) -> None:
        """
        Send a message via Linq with retry (up to 3 attempts, exponential backoff).
        Uses an idempotency_key so Linq deduplicates if we retry after a timeout.
        screen_effect: optional iMessage screen effect name (e.g. "confetti", "fireworks").
        """
        idempotency_key = str(uuid.uuid4())
        msg: dict = {
            "parts": [{"type": "text", "value": text}],
            "idempotency_key": idempotency_key,
        }
        if screen_effect:
            msg["effect"] = {"type": "screen", "name": screen_effect}

        async for attempt in AsyncRetrying(
            retry=retry_if_exception_type(httpx.HTTPError),
            wait=wait_exponential(multiplier=1, min=1, max=8),
            stop=stop_after_attempt(3),
            reraise=True,
        ):
            with attempt:
                async with httpx.AsyncClient(timeout=30) as client:
                    resp = await client.post(
                        f"{LINQ_API_BASE}/v3/chats/{chat_id}/messages",
                        json={"message": msg},
                        headers=self._headers,
                    )
                    if resp.status_code not in (200, 201, 202):
                        logger.error(f"Linq send_message failed [{resp.status_code}]: {resp.text}")
                        resp.raise_for_status()

    async def start_typing(self, chat_id: str) -> None:
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                await client.post(
                    f"{LINQ_API_BASE}/v3/chats/{chat_id}/typing",
                    headers=self._headers,
                )
        except Exception as e:
            logger.debug(f"start_typing failed for chat {chat_id}: {e}")

    async def stop_typing(self, chat_id: str) -> None:
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                await client.delete(
                    f"{LINQ_API_BASE}/v3/chats/{chat_id}/typing",
                    headers=self._headers,
                )
        except Exception as e:
            logger.debug(f"stop_typing failed for chat {chat_id}: {e}")

    async def mark_read(self, chat_id: str) -> None:
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                await client.post(
                    f"{LINQ_API_BASE}/v3/chats/{chat_id}/read",
                    headers=self._headers,
                )
        except Exception as e:
            logger.debug(f"mark_read failed for chat {chat_id}: {e}")
