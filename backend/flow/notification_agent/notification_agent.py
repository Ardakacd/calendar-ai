"""
Notification Agent

After a successful CREATE, UPDATE, or DELETE operation, this agent sends
the user an email summarising what was done.

Skipped for:
- LIST operations (no mutation occurred)
- Conflict / clarification responses (operation not completed)
- Missing RESEND_API_KEY
"""

import json
import logging
from datetime import datetime
from langchain_core.messages import SystemMessage, HumanMessage
from adapter.user_adapter import UserAdapter
from database.config import get_async_db_context_manager
from ..state import FlowState
from ..llm import model
from ..tools.email_tool import send_email_tool_factory
from .prompt import NOTIFICATION_AGENT_PROMPT

logger = logging.getLogger(__name__)

# Operations that should trigger a notification email
_NOTIFIABLE_OPERATIONS = {"create", "update", "delete"}


async def notification_agent(state: FlowState):
    """Send an email notification after a successful calendar mutation."""
    operation = state.get("scheduling_operation")
    scheduling_result = state.get("scheduling_result") or {}

    # Skip: not a mutation, not successful, or conflict/clarification pending
    if operation not in _NOTIFIABLE_OPERATIONS:
        return {}
    if not scheduling_result.get("success"):
        return {}
    if scheduling_result.get("has_conflict") or scheduling_result.get("needs_clarification"):
        return {}

    # Fetch user email from DB
    user_id = state["user_id"]
    user_email = await _get_user_email(user_id)
    if not user_email:
        logger.warning(f"Notification agent: could not find email for user_id={user_id}")
        return {}

    # Build structured context for the LLM
    events = scheduling_result.get("events") or []
    context_parts = [
        f"Operation: {operation}",
        f"User email: {user_email}",
    ]
    if events:
        context_parts.append("Events:\n" + json.dumps(_format_events(events), indent=2))
    else:
        context_parts.append(f"Summary: {scheduling_result.get('message', 'Your calendar was updated.')}")
    context = "\n".join(context_parts)

    email_tool = send_email_tool_factory()
    model_with_tools = model.bind_tools([email_tool])

    messages = [
        SystemMessage(content=NOTIFICATION_AGENT_PROMPT),
        HumanMessage(content=context),
    ]

    try:
        response = await model_with_tools.ainvoke(messages)

        if hasattr(response, "tool_calls") and response.tool_calls:
            for tc in response.tool_calls:
                if tc["name"] == "send_email":
                    args = tc.get("args", {})
                    await email_tool.ainvoke(args)
    except Exception as e:
        # Notification failures must never break the main flow response
        logger.error(f"Notification agent error: {e}", exc_info=True)

    return {}


def _format_events(events: list) -> list:
    """Convert raw event dicts to human-readable fields for the LLM."""
    formatted = []
    for e in events:
        start = _fmt_dt(e.get("startDate"))
        end = _fmt_dt(e.get("endDate"))
        entry = {
            "title": e.get("title", "Untitled"),
            "date": start["date"] if start else "",
            "start_time": start["time"] if start else "",
            "end_time": end["time"] if end else "",
        }
        if e.get("location"):
            entry["location"] = e["location"]
        formatted.append(entry)
    return formatted


def _fmt_dt(iso: str | None) -> dict | None:
    if not iso:
        return None
    try:
        dt = datetime.fromisoformat(iso)
        hour = dt.hour % 12 or 12
        minute = dt.strftime("%M")
        ampm = "AM" if dt.hour < 12 else "PM"
        date_str = dt.strftime("%a, %b ") + str(dt.day)
        return {"date": date_str, "time": f"{hour}:{minute} {ampm}"}
    except Exception:
        return {"date": iso, "time": ""}


async def _get_user_email(user_id: int) -> str | None:
    """Look up the user's email address from the database."""
    try:
        async with get_async_db_context_manager() as session:
            adapter = UserAdapter(session)
            user = await adapter.get_user_by_id(user_id)
            return user.email if user else None
    except Exception as e:
        logger.error(f"Failed to fetch email for user_id={user_id}: {e}", exc_info=True)
        return None
