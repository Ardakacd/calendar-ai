"""
Leisure Search Agent — Agentic Implementation

Handles questions about external events and activities that are outside the user's
personal calendar: concerts, sports, festivals, restaurants, etc.

Uses Tavily internet search to retrieve up-to-date information and responds
conversationally. Maintains full conversation history via router_messages.
"""

import logging
import json
from langchain_core.messages import SystemMessage, AIMessage, HumanMessage, ToolMessage
from tenacity import retry, stop_after_attempt, wait_random_exponential, retry_if_exception_type
from openai import OpenAIError, RateLimitError

from ..state import FlowState
from ..llm import model
from ..trim_utils import trim_messages
from ..tools.search_tool import internet_search_tool_factory
from .prompt import LEISURE_SEARCH_AGENT_PROMPT

logger = logging.getLogger(__name__)

retryable_exceptions = (OpenAIError, RateLimitError)


@retry(
    wait=wait_random_exponential(min=1, max=10),
    stop=stop_after_attempt(3),
    retry=retry_if_exception_type(retryable_exceptions),
)
async def leisure_search_agent(state: FlowState):
    """
    Leisure Search Agent node.

    Searches the internet for external events and activities using Tavily,
    then synthesizes a conversational response. Uses router_messages for
    full conversation history across turns.
    """
    search_tool = internet_search_tool_factory()
    model_with_tools = model.bind_tools([search_tool])

    # Build message list from accumulated router_messages (conversation history)
    # Replace or prepend the system message with the leisure search prompt.
    # Token-aware trim: keep last ~4000 tokens of conversation history
    existing_messages = trim_messages(
        state.get("router_messages", []),
        max_tokens=4000,
        start_on="human",
        include_system=False,
    )

    messages = [SystemMessage(content=LEISURE_SEARCH_AGENT_PROMPT)] + existing_messages

    # Agentic loop: LLM decides when and how many times to search
    max_iterations = 6
    for _ in range(max_iterations):
        response = await model_with_tools.ainvoke(messages)
        messages.append(response)

        if not (hasattr(response, 'tool_calls') and response.tool_calls):
            # LLM is done — no more tool calls
            break

        for tool_call in response.tool_calls:
            tool_name = tool_call.get('name', '')
            tool_args = tool_call.get('args', {})
            tool_call_id = tool_call.get('id', '')

            logger.info(f"Leisure Search Agent calling tool: {tool_name} with args: {tool_args}")

            try:
                result = await search_tool.ainvoke(tool_args)
                tool_result_content = json.dumps(result, default=str) if not isinstance(result, str) else result
            except Exception as e:
                logger.error(f"Search tool error: {e}", exc_info=True)
                tool_result_content = f"Search failed: {str(e)}. Try rephrasing the query."

            messages.append(ToolMessage(
                content=tool_result_content,
                tool_call_id=tool_call_id,
            ))

    final_content = messages[-1].content if messages[-1].content else "I couldn't find relevant information. Please try a more specific query."

    return {
        "router_messages": [AIMessage(content=final_content)],
        "is_success": True,
        # Clear any stale scheduling state from prior turns
        "scheduling_operation": None,
        "scheduling_event_data": None,
        "scheduling_result": None,
        "conflict_check_request": None,
        "conflict_check_result": None,
    }
