"""
Shared fixtures for flow integration tests.

Provides a compiled LangGraph flow with mocked LLM and MCP tools,
backed by a real MemorySaver for genuine multi-turn memory testing.
"""

import json
import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timezone, timedelta

from langgraph.checkpoint.memory import MemorySaver
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
USER_ID = 42
CURRENT_DT = "2026-04-12T10:00:00-04:00"
WEEKDAY = "Sunday"
DAYS_IN_MONTH = 30


# ---------------------------------------------------------------------------
# Mock LLM
# ---------------------------------------------------------------------------
class SequentialMockLLM:
    """Mock that returns pre-loaded responses in order.

    Supports:
      - .ainvoke(messages) -> AIMessage
      - .with_structured_output(schema) -> mock whose .ainvoke returns a Pydantic obj
      - .bind_tools(tools) -> self (tool_calls handled by responses)
    """

    def __init__(self):
        self._responses: list = []
        self._call_index = 0

    def set_responses(self, responses: list):
        self._responses = list(responses)
        self._call_index = 0

    async def ainvoke(self, messages, **kwargs):
        if self._call_index >= len(self._responses):
            return AIMessage(content="No more mock responses")
        resp = self._responses[self._call_index]
        self._call_index += 1
        return resp

    def with_structured_output(self, schema):
        """Returns a proxy whose ainvoke returns the next response (a Pydantic obj)."""
        parent = self

        class _Proxy:
            async def ainvoke(self_, messages, **kwargs):
                if parent._call_index >= len(parent._responses):
                    raise RuntimeError("No more mock responses for structured output")
                resp = parent._responses[parent._call_index]
                parent._call_index += 1
                return resp

        return _Proxy()

    def bind_tools(self, tools):
        """Returns self — tool_calls are encoded in the AIMessage responses."""
        return self


# ---------------------------------------------------------------------------
# Mock MCP tools
# ---------------------------------------------------------------------------
def make_mock_tool(name: str, return_value=None):
    """Create a mock MCP tool with .name and async .ainvoke()."""
    tool = AsyncMock()
    tool.name = name
    if return_value is not None:
        tool.ainvoke = AsyncMock(return_value=json.dumps(return_value, default=str))
    else:
        tool.ainvoke = AsyncMock(return_value=json.dumps({"success": True}))
    return tool


class MockMCPContext:
    """Async context manager yielding a list of mock tools."""

    def __init__(self, tools: list):
        self.tools = tools

    async def __aenter__(self):
        return self.tools

    async def __aexit__(self, *args):
        pass


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------
@pytest.fixture
def mock_llm():
    return SequentialMockLLM()


@pytest.fixture
def mock_tools():
    """Default set of calendar MCP tools (override return values per test)."""
    return {
        "list_event": make_mock_tool("list_event", []),
        "create_event": make_mock_tool("create_event", {"success": True, "event": {"id": "evt-001", "title": "Test"}}),
        "update_event": make_mock_tool("update_event", {"success": True, "event": {"id": "evt-001", "title": "Updated"}}),
        "delete_event": make_mock_tool("delete_event", {"success": True}),
        "check_conflict": make_mock_tool("check_conflict", {"has_conflict": False, "conflicting_events": [], "conflict_count": 0}),
        "suggest_alternative_times": make_mock_tool("suggest_alternative_times", {"suggestions": []}),
        "find_free_slots": make_mock_tool("find_free_slots", {"free_slots": []}),
    }


@pytest_asyncio.fixture
async def flow(mock_llm, mock_tools):
    """Compile the real graph with mocked LLM, MCP tools, and fresh MemorySaver."""
    checkpointer = MemorySaver()

    mock_mcp_ctx = MockMCPContext(list(mock_tools.values()))

    with (
        patch("flow.llm.model", mock_llm),
        patch("flow.router_agent.router_agent.model", mock_llm),
        patch("flow.scheduling_agent.scheduling_agent.model", mock_llm),
        patch("flow.conflict_resolution.conflict_resolution_agent.model", mock_llm),
        patch("flow.leisure_search_agent.leisure_search_agent.model", mock_llm),
        patch("flow.summarizer.model", mock_llm),
        patch("flow.scheduling_agent.scheduling_agent.get_calendar_tools", return_value=mock_mcp_ctx),
        patch("flow.conflict_resolution.conflict_resolution_agent.get_calendar_tools", return_value=mock_mcp_ctx),
    ):
        from flow.builder import FlowBuilder
        builder = FlowBuilder()

        # Patch the checkpointer
        with patch("flow.builder._get_checkpointer", new_callable=AsyncMock, return_value=checkpointer):
            compiled = await builder.create_flow()

        yield compiled


async def invoke_turn(flow, text: str, user_id: int = USER_ID):
    """Helper: invoke one turn of the conversation."""
    config = {"configurable": {"thread_id": str(user_id)}}
    return await flow.ainvoke(
        {
            "user_id": user_id,
            "router_messages": [HumanMessage(content=text)],
            "input_text": text,
            "current_datetime": CURRENT_DT,
            "weekday": WEEKDAY,
            "days_in_month": DAYS_IN_MONTH,
        },
        config=config,
    )
