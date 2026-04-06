"""
Python MCP Server — Email via Resend

Run as a subprocess by the notification agent.
Exposes a single `send_email` tool over stdio transport.
"""

import os
import sys
import asyncio
import resend
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("resend-email")


@mcp.tool()
def send_email(to_email: str, subject: str, html_body: str, from_email: str) -> dict:
    """Send an HTML email via Resend."""
    api_key = os.environ.get("RESEND_API_KEY", "")
    if not api_key:
        return {"success": False, "error": "RESEND_API_KEY not set"}

    resend.api_key = api_key

    try:
        response = resend.Emails.send({
            "from": from_email,
            "to": [to_email],
            "subject": subject,
            "html": html_body,
        })
        return {"success": True, "id": response.get("id")}
    except Exception as e:
        return {"success": False, "error": str(e)}


if __name__ == "__main__":
    mcp.run(transport="stdio")
