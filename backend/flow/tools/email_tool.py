"""
Email Tool — sends notification emails via Resend.
"""

import asyncio
import logging
from langchain_core.tools import StructuredTool
from pydantic import BaseModel, Field
from config import settings

logger = logging.getLogger(__name__)


class SendEmailInput(BaseModel):
    to_email: str = Field(description="Recipient email address")
    subject: str = Field(description="Email subject line")
    html_body: str = Field(description="HTML content of the email body")


async def send_email_impl(to_email: str, subject: str, html_body: str) -> dict:
    """Send an email via Resend."""
    if not settings.RESEND_API_KEY:
        logger.warning("RESEND_API_KEY not set — skipping email notification")
        return {"success": False, "error": "RESEND_API_KEY not configured"}

    try:
        import resend
        resend.api_key = settings.RESEND_API_KEY

        params = {
            "from": settings.NOTIFICATION_FROM_EMAIL,
            "to": [to_email],
            "subject": subject,
            "html": html_body,
        }
        response = await asyncio.to_thread(resend.Emails.send, params)
        logger.info(f"Email sent to {to_email}, id={response.get('id')}")
        return {"success": True, "id": response.get("id")}
    except Exception as e:
        logger.error(f"Failed to send email to {to_email}: {e}", exc_info=True)
        return {"success": False, "error": str(e)}


def send_email_tool_factory() -> StructuredTool:
    return StructuredTool(
        name="send_email",
        description="Send a notification email to the user summarising the calendar action that was completed.",
        args_schema=SendEmailInput,
        coroutine=send_email_impl,
    )
