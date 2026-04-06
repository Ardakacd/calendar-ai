"""
Calendar Tools MCP Client

Starts calendar_tools_server.py as a subprocess and returns its tools
as LangChain-compatible tools.

Usage:
    async with get_calendar_tools(user_id, user_tz) as tools:
        tools_by_name = {t.name: t for t in tools}
        list_tool = tools_by_name["list_event"]
        ...
"""

import logging
import os
import sys
from contextlib import asynccontextmanager
from pathlib import Path

logger = logging.getLogger(__name__)

_SERVER_SCRIPT = str(Path(__file__).parent / "calendar_tools_server.py")


def _tz_to_str(user_tz) -> str:
    """Convert a timezone object to an offset string like '-04:00'."""
    try:
        from datetime import datetime, timezone
        if user_tz is None:
            return ""
        offset = datetime.now(user_tz).utcoffset()
        if offset is None:
            return ""
        total_seconds = int(offset.total_seconds())
        sign = "+" if total_seconds >= 0 else "-"
        total_seconds = abs(total_seconds)
        hours, remainder = divmod(total_seconds, 3600)
        minutes = remainder // 60
        return f"{sign}{hours:02d}:{minutes:02d}"
    except Exception:
        return ""


@asynccontextmanager
async def get_calendar_tools(user_id: int, user_tz=None):
    """
    Async context manager that starts calendar_tools_server.py as a subprocess
    and yields the LangChain-compatible tools.
    """
    try:
        from langchain_mcp_adapters.client import MultiServerMCPClient

        env = {
            **os.environ,
            "USER_ID": str(user_id),
            "USER_TZ": _tz_to_str(user_tz),
        }

        client = MultiServerMCPClient(
            {
                "calendar": {
                    "command": sys.executable,
                    "args": [_SERVER_SCRIPT],
                    "env": env,
                    "transport": "stdio",
                }
            }
        )
        tools = await client.get_tools()
        logger.debug(f"Calendar MCP tools loaded: {[t.name for t in tools]}")
        yield tools

    except Exception as e:
        logger.error(f"Failed to start Calendar Tools MCP server: {e}", exc_info=True)
        yield []
