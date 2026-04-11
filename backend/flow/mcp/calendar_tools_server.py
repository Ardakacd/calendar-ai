"""
Calendar Tools MCP Server

Exposes all calendar CRUD and conflict tools as MCP tools.
User identity is injected via USER_ID environment variable.

Run by the MCP client (calendar_tools_mcp.py) as a subprocess per request.
"""

import os
import sys
import logging

# MCP uses stdio for the JSON-RPC protocol — any logging to stdout will corrupt
# the pipe. Force ALL loggers (including SQLAlchemy) to write to stderr only.
logging.basicConfig(stream=sys.stderr, level=logging.WARNING, force=True)
for _name in ("sqlalchemy", "sqlalchemy.engine", "sqlalchemy.pool"):
    logging.getLogger(_name).setLevel(logging.WARNING)

import asyncio
from typing import Optional
from datetime import datetime
from mcp.server.fastmcp import FastMCP

# Add backend root to path so imports work when run as subprocess
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from flow.tools.list_event_tool import list_event_impl
from flow.tools.create_event_tool import create_event_impl
from flow.tools.update_event_tool import update_event_impl
from flow.tools.delete_event_tool import delete_event_impl
from flow.tools.conflict_resolution_tools import (
    check_conflict_impl,
    suggest_alternative_times_impl,
    find_free_slots_impl,
)

mcp = FastMCP("calendar-tools")

_USER_ID = int(os.environ.get("USER_ID", "0"))
_USER_TZ_STR = os.environ.get("USER_TZ", "")


def _user_tz():
    """Parse timezone from offset string like '+05:30' or '-04:00'."""
    from datetime import timezone, timedelta
    if not _USER_TZ_STR:
        return timezone.utc
    try:
        sign = 1 if _USER_TZ_STR[0] != "-" else -1
        parts = _USER_TZ_STR.lstrip("+-").split(":")
        hours = int(parts[0])
        minutes = int(parts[1]) if len(parts) > 1 else 0
        return timezone(timedelta(hours=sign * hours, minutes=sign * minutes))
    except Exception:
        return timezone.utc


# ---------------------------------------------------------------------------
# CRUD tools
# ---------------------------------------------------------------------------

@mcp.tool()
async def list_event(startDate: str, endDate: Optional[str] = None) -> dict:
    """
    List calendar events within a date range.
    startDate and endDate must be ISO 8601 strings e.g. "2026-04-06T00:00:00-04:00".
    """
    start = datetime.fromisoformat(startDate)
    end = datetime.fromisoformat(endDate) if endDate else None
    return await list_event_impl(start, end, _USER_ID, _user_tz())


@mcp.tool()
async def create_event(
    title: str,
    startDate: str,
    endDate: Optional[str] = None,
    location: Optional[str] = None,
    description: Optional[str] = None,
    category: Optional[str] = None,
    recurrence_type: Optional[str] = None,
    recurrence_count: Optional[int] = None,
    recurrence_interval: Optional[int] = None,
    recurrence_byweekday: Optional[str] = None,
    recurrence_bysetpos: Optional[int] = None,
) -> dict:
    """Create a new calendar event. For recurring events set recurrence_type ('daily','weekly','monthly','yearly') and recurrence_count.
    Use recurrence_interval for bi-weekly (2) etc., recurrence_byweekday for specific days ('MO,WE,FR'),
    and recurrence_bysetpos for positional rules (1=first, -1=last occurrence in period)."""
    start = datetime.fromisoformat(startDate)
    end = datetime.fromisoformat(endDate) if endDate else None
    return await create_event_impl(
        title, start, end, location, description, category,
        recurrence_type=recurrence_type,
        recurrence_count=recurrence_count,
        recurrence_interval=recurrence_interval,
        recurrence_byweekday=recurrence_byweekday,
        recurrence_bysetpos=recurrence_bysetpos,
        user_id=_USER_ID,
    )


@mcp.tool()
async def update_event(
    event_id: str,
    title: Optional[str] = None,
    startDate: Optional[str] = None,
    duration: Optional[int] = None,
    location: Optional[str] = None,
    description: Optional[str] = None,
    category: Optional[str] = None,
) -> dict:
    """Update an existing calendar event. Only supply fields to change."""
    start = datetime.fromisoformat(startDate) if startDate else None
    return await update_event_impl(event_id, _USER_ID, title, start, duration, location, description, category)


@mcp.tool()
async def delete_event(event_id: str) -> dict:
    """Delete a calendar event by its UUID."""
    return await delete_event_impl(event_id, _USER_ID)


# ---------------------------------------------------------------------------
# Conflict resolution tools
# ---------------------------------------------------------------------------

@mcp.tool()
async def check_conflict(
    startDate: str,
    endDate: str,
    exclude_event_id: Optional[str] = None,
) -> dict:
    """Check if a time slot conflicts with existing events."""
    start = datetime.fromisoformat(startDate)
    end = datetime.fromisoformat(endDate)
    return await check_conflict_impl(start, end, _USER_ID, exclude_event_id)


@mcp.tool()
async def suggest_alternative_times(
    requested_startDate: str,
    requested_endDate: str,
    duration_minutes: int = 60,
    search_window_days: int = 7,
    max_suggestions: int = 3,
) -> dict:
    """Suggest alternative time slots when a conflict is detected."""
    start = datetime.fromisoformat(requested_startDate)
    end = datetime.fromisoformat(requested_endDate)
    return await suggest_alternative_times_impl(
        start, end, duration_minutes, _USER_ID, search_window_days, max_suggestions
    )


@mcp.tool()
async def find_free_slots(
    startDate: str,
    endDate: str,
    duration_minutes: int = 60,
    preferred_times: Optional[list] = None,
    buffer_minutes: int = 15,
) -> dict:
    """Find free time slots in a date range."""
    start = datetime.fromisoformat(startDate)
    end = datetime.fromisoformat(endDate)
    return await find_free_slots_impl(
        start, end, _USER_ID, duration_minutes, preferred_times, buffer_minutes
    )


# ---------------------------------------------------------------------------

if __name__ == "__main__":
    mcp.run(transport="stdio")
