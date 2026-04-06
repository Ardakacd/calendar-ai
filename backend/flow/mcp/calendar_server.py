"""
Calendar AI — MCP Server

Exposes calendar CRUD operations as MCP tools so any MCP client
(Claude Desktop, etc.) can manage the user's calendar.

Configuration (environment variables):
    CALENDAR_API_URL    Backend base URL  (default: http://localhost:8000)
    CALENDAR_API_TOKEN  JWT access token  (obtain via POST /auth/login)

Run:
    python flow/mcp/calendar_server.py

Claude Desktop config (~/.claude_desktop_config.json):
    {
      "mcpServers": {
        "calendar-ai": {
          "command": "python",
          "args": ["/absolute/path/to/backend/flow/mcp/calendar_server.py"],
          "env": {
            "CALENDAR_API_URL": "http://localhost:8000",
            "CALENDAR_API_TOKEN": "<your_jwt_token>"
          }
        }
      }
    }
"""

import os
import sys
import json
import urllib.request
import urllib.parse
import urllib.error
from typing import Optional
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("calendar-ai")

_BASE_URL = os.environ.get("CALENDAR_API_URL", "http://localhost:8000").rstrip("/")
_TOKEN = os.environ.get("CALENDAR_API_TOKEN", "")


# ---------------------------------------------------------------------------
# HTTP helpers
# ---------------------------------------------------------------------------

def _headers() -> dict:
    return {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {_TOKEN}",
    }


def _request(method: str, path: str, body: dict | None = None) -> dict:
    url = f"{_BASE_URL}{path}"
    data = json.dumps(body).encode() if body else None
    req = urllib.request.Request(url, data=data, headers=_headers(), method=method)
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        return {"error": f"HTTP {e.code}: {e.read().decode()}"}
    except Exception as e:
        return {"error": str(e)}


# ---------------------------------------------------------------------------
# MCP Tools
# ---------------------------------------------------------------------------

@mcp.tool()
def list_events(start_date: str, end_date: str) -> dict:
    """
    List calendar events within a date range.

    Args:
        start_date: ISO 8601 start datetime  e.g. "2026-04-06T00:00:00-04:00"
        end_date:   ISO 8601 end datetime    e.g. "2026-04-06T23:59:59-04:00"

    Returns a list of events with id, title, startDate, endDate, duration, location.
    """
    params = urllib.parse.urlencode({"start_date": start_date, "end_date": end_date})
    return _request("GET", f"/events/range/?{params}")


@mcp.tool()
def create_event(
    title: str,
    start_date: str,
    duration: int = 60,
    location: Optional[str] = None,
) -> dict:
    """
    Create a new calendar event.

    Args:
        title:      Event title
        start_date: ISO 8601 start datetime  e.g. "2026-04-07T09:00:00-04:00"
        duration:   Duration in minutes (default 60)
        location:   Optional location string

    Returns the created event with its id.
    """
    body = {
        "title": title,
        "startDate": start_date,
        "duration": duration,
        "location": location,
    }
    return _request("POST", "/events", body)


@mcp.tool()
def update_event(
    event_id: str,
    title: Optional[str] = None,
    start_date: Optional[str] = None,
    duration: Optional[int] = None,
    location: Optional[str] = None,
) -> dict:
    """
    Update an existing calendar event. Only supply the fields you want to change.

    Args:
        event_id:   UUID of the event to update
        title:      New title (optional)
        start_date: New ISO 8601 start datetime (optional)
        duration:   New duration in minutes (optional)
        location:   New location (optional)

    Returns the updated event.
    """
    body = {}
    if title is not None:
        body["title"] = title
    if start_date is not None:
        body["startDate"] = start_date
    if duration is not None:
        body["duration"] = duration
    if location is not None:
        body["location"] = location

    return _request("PATCH", f"/events/{event_id}", body)


@mcp.tool()
def delete_event(event_id: str) -> dict:
    """
    Delete a calendar event by its ID.

    Args:
        event_id: UUID of the event to delete

    Returns a confirmation message.
    """
    return _request("DELETE", f"/events/{event_id}")


@mcp.tool()
def get_event(event_id: str) -> dict:
    """
    Get a single calendar event by its ID.

    Args:
        event_id: UUID of the event

    Returns event details: id, title, startDate, endDate, duration, location.
    """
    return _request("GET", f"/events/{event_id}")


# ---------------------------------------------------------------------------

if __name__ == "__main__":
    if not _TOKEN:
        print(
            "ERROR: CALENDAR_API_TOKEN is not set.\n"
            "Get a token by calling POST /auth/login with your credentials.",
            file=sys.stderr,
        )
        sys.exit(1)

    mcp.run(transport="stdio")
