"""
Conflict Resolution Agent - Agentic Implementation

This agent uses LLM with tools to check conflicts and suggest alternatives.
The LLM decides which tools to use and how to respond.
"""

import logging
import json
from langchain_core.messages import SystemMessage, AIMessage, HumanMessage, ToolMessage
from ..state import FlowState
from .system_prompt import CONFLICT_RESOLUTION_AGENT_PROMPT
from ..llm import model
from tenacity import retry, stop_after_attempt, wait_random_exponential, retry_if_exception_type
from openai import OpenAIError, RateLimitError
from ..mcp.calendar_tools_mcp import get_calendar_tools

logger = logging.getLogger(__name__)

retryable_exceptions = (OpenAIError, RateLimitError)


def _parse_mcp_result(result) -> dict:
    """MCP tools (langchain-mcp-adapters 0.1.6) return results as JSON strings."""
    if isinstance(result, str):
        try:
            return json.loads(result)
        except json.JSONDecodeError:
            return {"error": result}
    return result


@retry(
    wait=wait_random_exponential(min=1, max=10),
    stop=stop_after_attempt(3),
    retry=retry_if_exception_type(retryable_exceptions),
)
async def conflict_resolution_agent(state: FlowState):
    """
    Conflict Resolution Agent - Agentic implementation.

    The LLM decides which tools to use and orchestrates conflict checking and suggestions.
    """
    if not state.get('conflict_check_request'):
        logger.warning("No conflict check request found in state")
        return {
            "conflict_check_result": {
                "has_conflict": False,
                "conflicting_events": [],
                "suggestions": [],
                "recommendation": "No conflict check requested"
            },
            "conflict_resolution_messages": [AIMessage(content="No conflict check requested.")],
            "is_success": True
        }

    request = state['conflict_check_request']
    user_id = state['user_id']

    logger.info(f"Conflict Resolution Agent: Checking conflicts for user {user_id}")

    try:
        from ..scheduling_agent.scheduling_agent import _extract_tz
        user_tz = _extract_tz(state.get('current_datetime', ''))

        async with get_calendar_tools(user_id, user_tz) as mcp_tools:
            tools_map = {t.name: t for t in mcp_tools}
            check_conflict_tool = tools_map['check_conflict']
            suggest_tool = tools_map['suggest_alternative_times']
            find_free_slots_tool = tools_map['find_free_slots']
            return await _run_conflict_agent(
                state, request, check_conflict_tool, suggest_tool, find_free_slots_tool
            )

    except Exception as e:
        logger.error(f"Error in conflict resolution agent: {e}", exc_info=True)
        return {
            "conflict_check_result": {
                "has_conflict": False,
                "check_failed": True,
                "conflicting_events": [],
                "suggestions": [],
                "recommendation": f"Error checking conflicts: {str(e)}"
            },
            "conflict_resolution_messages": [AIMessage(content="An error occurred while checking conflicts.")],
            "is_success": False
        }


async def _run_conflict_agent(state, request, check_conflict_tool, suggest_tool, find_free_slots_tool):
    """Inner agentic loop — separated so the outer function can manage the MCP context."""
    model_with_tools = model.bind_tools([check_conflict_tool, suggest_tool, find_free_slots_tool])

    prompt_text = CONFLICT_RESOLUTION_AGENT_PROMPT

    if state.get("conflict_resolution_messages") and isinstance(state["conflict_resolution_messages"][0], SystemMessage):
        state["conflict_resolution_messages"][0] = SystemMessage(content=prompt_text)
        messages = list(state["conflict_resolution_messages"])
    else:
        messages = [SystemMessage(content=prompt_text)]
        if "conflict_resolution_messages" in state:
            messages.extend(state["conflict_resolution_messages"])

    request_text = (
        f"Please check for conflicts for the following time slot:\n"
        f"- Start Date: {request.get('startDate')}\n"
        f"- End Date: {request.get('endDate')}\n"
        f"- Duration: {request.get('duration_minutes', 60)} minutes\n"
        f"- Exclude Event ID: {request.get('exclude_event_id', 'None')}\n\n"
        "Check for conflicts and suggest alternatives if conflicts are found. "
        "Provide a clear recommendation."
    )
    messages.append(HumanMessage(content=request_text))

    max_iterations = 5
    conflict_result_from_tools = None
    suggestions_from_tools = None

    for _ in range(max_iterations):
        response = await model_with_tools.ainvoke(messages)
        messages.append(response)

        if not (hasattr(response, 'tool_calls') and response.tool_calls):
            break

        for tool_call in response.tool_calls:
            tool_name = tool_call['name']
            tool_args = dict(tool_call.get('args', {}))
            logger.info(f"Conflict Resolution Agent calling tool: {tool_name}")

            # MCP tools (langchain-mcp-adapters 0.1.6) return JSON strings — parse them
            if tool_name == 'check_conflict':
                tool_result = _parse_mcp_result(await check_conflict_tool.ainvoke(tool_args))
                conflict_result_from_tools = tool_result
            elif tool_name == 'suggest_alternative_times':
                tool_result = _parse_mcp_result(await suggest_tool.ainvoke(tool_args))
                suggestions_from_tools = tool_result
            elif tool_name == 'find_free_slots':
                tool_result = _parse_mcp_result(await find_free_slots_tool.ainvoke(tool_args))
            else:
                tool_result = {"error": f"Unknown tool: {tool_name}"}

            messages.append(ToolMessage(
                content=json.dumps(tool_result, default=str),
                tool_call_id=tool_call.get('id', '')
            ))

    final_response = messages[-1].content if messages else "No response generated"
    if conflict_result_from_tools:
        conflict_result = {
            "has_conflict": conflict_result_from_tools.get("has_conflict", False),
            "conflicting_events": conflict_result_from_tools.get("conflicting_events", []),
            "conflict_count": conflict_result_from_tools.get("conflict_count", 0),
            "suggestions": suggestions_from_tools.get("suggestions", []) if suggestions_from_tools else [],
            "recommendation": final_response
        }
    else:
        conflict_result = _parse_llm_response(final_response, request)

    logger.info(
        f"Conflict Resolution Agent: Found {conflict_result.get('conflict_count', 0)} conflicts, "
        f"{len(conflict_result.get('suggestions', []))} suggestions"
    )

    return {
        "conflict_check_result": conflict_result,
        "conflict_resolution_messages": messages,
        "is_success": True
    }


def _parse_llm_response(response: str, request: dict) -> dict:
    """Parse LLM response to extract conflict information."""
    try:
        if response.strip().startswith('{'):
            parsed = json.loads(response)
            return {
                "has_conflict": parsed.get('has_conflict', False),
                "conflicting_events": parsed.get('conflicting_events', []),
                "conflict_count": parsed.get('conflict_count', 0),
                "suggestions": parsed.get('suggestions', []),
                "recommendation": parsed.get('recommendation', response)
            }
    except json.JSONDecodeError:
        pass

    return {
        "has_conflict": "conflict" in response.lower() or "conflicts" in response.lower(),
        "conflicting_events": [],
        "conflict_count": 0,
        "suggestions": [],
        "recommendation": response
    }


def conflict_resolution_action(state: FlowState):
    """Determine next action after conflict resolution."""
    result = state.get('conflict_check_result', {})

    if not result.get('has_conflict'):
        return "no_conflict"
    elif result.get('suggestions'):
        return "conflict_with_suggestions"
    else:
        return "conflict_no_suggestions"
