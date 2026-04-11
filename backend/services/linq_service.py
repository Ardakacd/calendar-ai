import calendar
import logging
import uuid
from datetime import datetime
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from adapter.user_adapter import UserAdapter
from config import settings
from models import User, UserCreate
from utils.password import get_password_hash

logger = logging.getLogger(__name__)

LINQ_API_BASE = "https://api.linqapp.com/api/partner"

# Commands users can send via iMessage
HELP_TEXT = (
    "Calendar AI — available commands:\n"
    "• Just chat naturally to create, update, delete, or list events\n"
    "• set timezone <tz> — e.g. 'set timezone America/Chicago'\n"
    "• set password <pw> — set a password to log in to the app\n"
    "• reset — clear conversation history\n"
    "• help — show this message"
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
        user = await self.user_adapter.create_user(user_data)
        logger.info(f"Auto-created Linq user for phone: {phone_number}, id: {user.id}")
        return user

    async def link_account(self, sms_user_id: int, email: str, phone_number: str) -> bool:
        """Link a phone number to an existing account by email, removing the SMS-created duplicate."""
        from models import UserUpdate
        target = await self.user_adapter.get_user_by_email(email)
        if not target:
            return False
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

    async def send_message(self, chat_id: str, text: str) -> None:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                f"{LINQ_API_BASE}/v3/chats/{chat_id}/messages",
                json={"message": {"parts": [{"type": "text", "value": text}]}},
                headers=self._headers,
            )
            if resp.status_code not in (200, 201, 202):
                logger.error(f"Linq send_message failed [{resp.status_code}]: {resp.text}")
                resp.raise_for_status()

    async def start_typing(self, chat_id: str) -> None:
        async with httpx.AsyncClient(timeout=10) as client:
            await client.post(
                f"{LINQ_API_BASE}/v3/chats/{chat_id}/typing",
                headers=self._headers,
            )

    async def stop_typing(self, chat_id: str) -> None:
        async with httpx.AsyncClient(timeout=10) as client:
            await client.delete(
                f"{LINQ_API_BASE}/v3/chats/{chat_id}/typing",
                headers=self._headers,
            )
