"""Lightweight token-aware message trimming.

langchain_core 0.1.x does not ship ``trim_messages``, so we provide a
compatible helper here.  Token counts are *estimated* at ~4 chars per token
(GPT family average) to avoid an extra LLM round-trip.
"""

from __future__ import annotations

from typing import List, Sequence
from langchain_core.messages import BaseMessage, SystemMessage

_CHARS_PER_TOKEN = 4  # conservative estimate for English text


def _estimate_tokens(msg: BaseMessage) -> int:
    content = msg.content if isinstance(msg.content, str) else str(msg.content)
    return max(len(content) // _CHARS_PER_TOKEN, 1)


def trim_messages(
    messages: Sequence[BaseMessage],
    *,
    max_tokens: int = 4000,
    start_on: str = "human",
    include_system: bool = False,
) -> List[BaseMessage]:
    """Return the *last* N messages that fit within ``max_tokens``.

    Parameters
    ----------
    messages:
        Full message list (may include SystemMessage).
    max_tokens:
        Estimated token budget.
    start_on:
        The trimmed window must start with a message of this type
        (``"human"`` or ``"ai"``).  Messages are dropped from the front
        until this condition is met.
    include_system:
        If ``False``, SystemMessages are stripped before trimming.
    """
    if not include_system:
        messages = [m for m in messages if not isinstance(m, SystemMessage)]

    if not messages:
        return []

    # Walk backwards accumulating tokens
    kept: list[BaseMessage] = []
    budget = max_tokens
    for msg in reversed(messages):
        cost = _estimate_tokens(msg)
        if budget - cost < 0 and kept:
            break
        kept.append(msg)
        budget -= cost

    kept.reverse()

    # Ensure the window starts on the requested message type
    type_tag = start_on  # "human" or "ai"
    while kept and getattr(kept[0], "type", None) != type_tag:
        kept.pop(0)

    return kept
