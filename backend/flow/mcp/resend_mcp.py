"""
Resend MCP Client

Starts the local Python MCP email server (email_server.py) as a subprocess
and exposes its tools as LangChain-compatible tools.

Usage:
    async with get_resend_tools() as tools:
        model_with_tools = model.bind_tools(tools)
        ...
"""

import logging
import os
import sys
from contextlib import asynccontextmanager
from pathlib import Path
from config import settings

logger = logging.getLogger(__name__)

# Absolute path to the Python MCP server script
_SERVER_SCRIPT = str(Path(__file__).parent / "email_server.py")


@asynccontextmanager
async def get_resend_tools():
    """
    Async context manager that starts email_server.py as a subprocess via
    stdio transport and yields its LangChain-compatible tools.

    Yields an empty list if RESEND_API_KEY is missing or startup fails.
    """
    if not settings.RESEND_API_KEY:
        logger.warning("RESEND_API_KEY not set — Resend MCP tools unavailable")
        yield []
        return

    try:
        from langchain_mcp_adapters.client import MultiServerMCPClient

        env = {**os.environ, "RESEND_API_KEY": settings.RESEND_API_KEY}

        client = MultiServerMCPClient(
            {
                "resend": {
                    "command": sys.executable,   # same Python interpreter as the backend
                    "args": [_SERVER_SCRIPT],
                    "env": env,
                    "transport": "stdio",
                }
            }
        )
        tools = await client.get_tools()
        logger.debug(f"Resend MCP tools loaded: {[t.name for t in tools]}")
        yield tools

    except Exception as e:
        logger.error(f"Failed to start Resend MCP server: {e}", exc_info=True)
        yield []
