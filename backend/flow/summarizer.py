"""Conversation summarization node.

Runs before the router agent.  When ``router_messages`` grows beyond 12
non-system messages the node summarises the oldest messages into a rolling
``conversation_summary`` field.

Older messages are **not** removed from ``router_messages`` (checkpoint size
still grows).  Downstream code uses ``conversation_summary`` plus trimming
(``trim_messages``) so prompts stay bounded; consider ``RemoveMessage`` if
checkpoint size becomes an issue.
"""

import logging
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage

from .state import FlowState
from .llm import model

logger = logging.getLogger(__name__)

_SUMMARY_THRESHOLD = 12  # only summarise when we exceed this many messages


async def summarize_conversation(state: FlowState) -> dict:
    msgs = [m for m in state.get("router_messages", []) if not isinstance(m, SystemMessage)]

    if len(msgs) <= _SUMMARY_THRESHOLD:
        return {}

    # Keep the last 6 messages as-is; summarise everything before them.
    to_summarize = msgs[:-6]
    existing_summary = state.get("conversation_summary", "") or ""

    if existing_summary:
        prompt = (
            "Extend this existing summary with the new messages below. "
            "Keep it concise and preserve key facts (event names, times, "
            "decisions made, pending actions):\n\n"
            f"Existing summary:\n{existing_summary}\n\n"
            "New messages to incorporate:\n"
        )
    else:
        prompt = (
            "Summarize this conversation concisely. Preserve key facts: "
            "event names, times, decisions made, pending actions, user preferences:\n\n"
        )

    prompt += "\n".join(
        f"{'User' if isinstance(m, HumanMessage) else 'Assistant'}: {m.content}"
        for m in to_summarize
        if hasattr(m, "content") and isinstance(m.content, str)
    )

    try:
        summary_response = await model.ainvoke([HumanMessage(content=prompt)])
        logger.info("Conversation summarised (%d msgs → summary)", len(to_summarize))
        return {"conversation_summary": summary_response.content}
    except Exception:
        logger.exception("Summarization failed — continuing without summary")
        return {}
