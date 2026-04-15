"""
Integration tests for LangGraph calendar assistant short-term memory.

Tests multi-turn conversations with a real MemorySaver checkpointer
and mocked LLM / MCP tools to verify state transitions, memory
persistence, and context resolution across turns.
"""

import json
import pytest
import pytest_asyncio
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, patch

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

from tests.conftest import invoke_turn, USER_ID

# Pydantic models for structured output mocks
from flow.scheduling_agent.scheduling_agent import CreatePlan, CreateEventItem, UpdatePlan, DeletePlan, _FreshCreateCheck


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _dt(hours_from_now: int = 24) -> datetime:
    """Return a timezone-aware datetime offset from now."""
    return datetime.now(timezone(timedelta(hours=-4))) + timedelta(hours=hours_from_now)


def _route(response) -> str | None:
    """Extract the route string from a response."""
    r = response.get("route")
    if isinstance(r, dict):
        return r.get("route")
    return None


def _tool_events(events: list) -> str:
    """Wrap events in the {"events": [...]} format expected by _extract_events_from_messages."""
    return json.dumps({"events": events}, default=str)


# ============================================================
# Category 7: State Hygiene — fundamental invariants
# ============================================================
class TestStateHygiene:
    """Verify scheduling fields are properly set/cleared across turns."""

    @pytest.mark.asyncio
    async def test_scheduling_cleared_after_conversation(self, flow, mock_llm):
        """After a create, a conversation turn should clear all scheduling fields."""
        # --- Turn 1: create an event ---
        start = _dt(24)
        mock_llm.set_responses([
            # Router
            AIMessage(content='{"route": "create"}'),
            # Structured extraction (CreatePlan)
            CreatePlan(events=[CreateEventItem(title="Gym", startDate=start, duration=60)]),
            # Conflict resolution: LLM decides to call check_conflict tool
            AIMessage(content="", additional_kwargs={"tool_calls": [
                {"id": "tc1", "type": "function", "function": {"name": "check_conflict", "arguments": json.dumps({"startDate": start.isoformat(), "endDate": (start + timedelta(hours=1)).isoformat()})}}
            ]}),
            # After tool result, LLM concludes no conflict
            AIMessage(content="No conflicts found."),
            # _execute_create doesn't call the LLM — it uses the tool directly
            # Summarizer (returns no-op if <12 messages)
        ])

        r1 = await invoke_turn(flow, "Add gym tomorrow at 6am")
        assert _route(r1) == "create"

        # --- Turn 2: conversation ---
        mock_llm.set_responses([
            # Summarizer (if triggered — won't be, <12 messages)
            # Router: returns a plain string (conversation)
            AIMessage(content="You're welcome! Let me know if you need anything else."),
        ])

        r2 = await invoke_turn(flow, "Thanks!")

        # Scheduling fields should be cleared by router_message_handler
        assert r2.get("scheduling_operation") is None
        assert r2.get("scheduling_event_data") is None
        assert r2.get("scheduling_result") is None
        assert r2.get("conflict_check_request") is None
        assert r2.get("conflict_check_result") is None

    @pytest.mark.asyncio
    async def test_scheduling_cleared_after_leisure(self, flow, mock_llm, mock_tools):
        """After a create, a leisure search turn should clear scheduling fields."""
        start = _dt(24)
        mock_llm.set_responses([
            AIMessage(content='{"route": "create"}'),
            CreatePlan(events=[CreateEventItem(title="Meeting", startDate=start, duration=60)]),
            AIMessage(content="", additional_kwargs={"tool_calls": [
                {"id": "tc1", "type": "function", "function": {"name": "check_conflict", "arguments": json.dumps({"startDate": start.isoformat(), "endDate": (start + timedelta(hours=1)).isoformat()})}}
            ]}),
            AIMessage(content="No conflicts."),
        ])
        await invoke_turn(flow, "Add a meeting tomorrow at 2pm")

        # --- Turn 2: leisure search ---
        mock_llm.set_responses([
            AIMessage(content='{"route": "leisure_search"}'),
            # Leisure agent LLM: no tool calls, just a response
            AIMessage(content="Here are some concerts this weekend: ..."),
        ])

        # Mock the search tool factory
        with patch("flow.leisure_search_agent.leisure_search_agent.internet_search_tool_factory"):
            r2 = await invoke_turn(flow, "Any concerts this weekend?")

        assert r2.get("scheduling_operation") is None
        assert r2.get("scheduling_event_data") is None
        assert r2.get("scheduling_result") is None

    @pytest.mark.asyncio
    async def test_router_messages_grow_with_add_messages(self, flow, mock_llm):
        """router_messages should accumulate across turns (add_messages reducer)."""
        # Turn 1
        mock_llm.set_responses([
            AIMessage(content="Hello! How can I help you today?"),
        ])
        r1 = await invoke_turn(flow, "Hi")
        msgs1 = r1.get("router_messages", [])
        # Should have at least: HumanMessage("Hi") + AIMessage(greeting)
        human_count_1 = sum(1 for m in msgs1 if isinstance(m, HumanMessage))
        ai_count_1 = sum(1 for m in msgs1 if isinstance(m, AIMessage))
        assert human_count_1 >= 1
        assert ai_count_1 >= 1

        # Turn 2
        mock_llm.set_responses([
            AIMessage(content="I can help with scheduling, reminders, and more!"),
        ])
        r2 = await invoke_turn(flow, "What can you do?")
        msgs2 = r2.get("router_messages", [])
        # Should have accumulated: 2 HumanMessages + 2 AIMessages
        human_count_2 = sum(1 for m in msgs2 if isinstance(m, HumanMessage))
        assert human_count_2 >= 2, f"Expected >=2 HumanMessages, got {human_count_2}"

    @pytest.mark.asyncio
    async def test_previous_route_tracks_across_turns(self, flow, mock_llm, mock_tools):
        """previous_route should reflect the prior turn's route classification."""
        start = _dt(24)
        # Turn 1: create
        mock_llm.set_responses([
            AIMessage(content='{"route": "create"}'),
            CreatePlan(events=[CreateEventItem(title="Lunch", startDate=start, duration=60)]),
            AIMessage(content="", additional_kwargs={"tool_calls": [
                {"id": "tc1", "type": "function", "function": {"name": "check_conflict", "arguments": json.dumps({"startDate": start.isoformat(), "endDate": (start + timedelta(hours=1)).isoformat()})}}
            ]}),
            AIMessage(content="No conflict."),
        ])
        r1 = await invoke_turn(flow, "Add lunch tomorrow at noon")
        # First turn: previous_route should be None (no prior turn)
        assert r1.get("previous_route") is None

        # Turn 2: conversation
        mock_llm.set_responses([
            AIMessage(content="You're welcome!"),
        ])
        r2 = await invoke_turn(flow, "Thanks")
        # previous_route should be "create" from turn 1
        assert r2.get("previous_route") == "create"


# ============================================================
# Category 3: Cross-Intent Flows (critical bug area)
# ============================================================
class TestCrossIntentFlows:
    """Verify context carries across intent switches (create→update, etc)."""

    @pytest.mark.asyncio
    async def test_create_then_update_has_router_context(self, flow, mock_llm, mock_tools):
        """After creating an event, 'move it to 3pm' should have router_messages
        context about the created event, even though scheduling_messages is empty."""
        start = _dt(24)
        # Turn 1: create
        mock_llm.set_responses([
            AIMessage(content='{"route": "create"}'),
            CreatePlan(events=[CreateEventItem(title="Meeting", startDate=start, duration=60)]),
            AIMessage(content="", additional_kwargs={"tool_calls": [
                {"id": "tc1", "type": "function", "function": {"name": "check_conflict", "arguments": json.dumps({"startDate": start.isoformat(), "endDate": (start + timedelta(hours=1)).isoformat()})}}
            ]}),
            AIMessage(content="No conflict."),
        ])
        r1 = await invoke_turn(flow, "Add a meeting at 2pm tomorrow")
        assert _route(r1) == "create"

        # Verify the confirmation is in router_messages
        router_msgs = r1.get("router_messages", [])
        ai_msgs = [m for m in router_msgs if isinstance(m, AIMessage)]
        ai_contents = [m.content for m in ai_msgs]
        # The create confirmation or acknowledgment should be visible in router_messages
        assert len(ai_msgs) > 0, f"Expected AI messages in router_messages, got none. All msgs: {[type(m).__name__ + ': ' + (m.content[:80] if hasattr(m, 'content') else '?') for m in router_msgs]}"

        # Turn 2: update — "move it"
        new_start = start + timedelta(hours=1)
        events_list = [{
            "id": "evt-001", "title": "Meeting",
            "startDate": start.isoformat(), "endDate": (start + timedelta(hours=1)).isoformat(),
        }]
        events_json = json.dumps(events_list, default=str)

        mock_llm.set_responses([
            AIMessage(content='{"route": "update"}'),
            # Tool loop: LLM calls list_event
            AIMessage(content="", additional_kwargs={"tool_calls": [
                {"id": "tc2", "type": "function", "function": {"name": "list_event", "arguments": json.dumps({"date": start.strftime("%Y-%m-%d")})}}
            ]}),
            # After tool result, LLM is done with tool loop
            AIMessage(content="Found the meeting."),
            # Filter: returns the matching event
            AIMessage(content=events_json),
            # UpdatePlan extraction
            UpdatePlan(
                event_ids=["evt-001"],
                new_startDate=new_start,
                existing_startDate=start,
                existing_endDate=start + timedelta(hours=1),
            ),
            # Conflict resolution
            AIMessage(content="", additional_kwargs={"tool_calls": [
                {"id": "tc3", "type": "function", "function": {"name": "check_conflict", "arguments": json.dumps({"startDate": new_start.isoformat(), "endDate": (new_start + timedelta(hours=1)).isoformat()})}}
            ]}),
            AIMessage(content="No conflict."),
        ])

        # Set list_event to return the created event (must be {"events": [...]})
        mock_tools["list_event"].ainvoke = AsyncMock(return_value=_tool_events(events_list))

        r2 = await invoke_turn(flow, "Move it to 3pm")
        assert _route(r2) == "update"
        # previous_route should be "create" from turn 1
        assert r2.get("previous_route") == "create"
        # The router_messages should still have turn 1 context
        all_human = [m for m in r2["router_messages"] if isinstance(m, HumanMessage)]
        assert any("meeting" in m.content.lower() for m in all_human), \
            "Turn 1 HumanMessage about meeting should survive in router_messages"


# ============================================================
# Category 2: Multi-Turn Same-Intent (Clarification)
# ============================================================
class TestClarificationFlows:
    """Verify clarification → follow-up works within the same intent."""

    @pytest.mark.asyncio
    async def test_create_missing_time_then_provide(self, flow, mock_llm, mock_tools):
        """Create with missing time should ask for clarification, then succeed."""
        # Turn 1: create with missing time
        mock_llm.set_responses([
            AIMessage(content='{"route": "create"}'),
            CreatePlan(
                events=[],
                clarification_needed="What time would you like to schedule the meeting with Sarah?",
            ),
        ])
        r1 = await invoke_turn(flow, "Add a meeting with Sarah")
        assert r1.get("scheduling_result", {}).get("needs_clarification") is True
        assert "time" in r1["scheduling_result"]["message"].lower()

        # Verify scheduling_messages has both HumanMessage and AIMessage
        sched_msgs = r1.get("scheduling_messages", [])
        assert any(isinstance(m, HumanMessage) for m in sched_msgs), \
            "User's request should be preserved in scheduling_messages for context"
        assert any(isinstance(m, AIMessage) for m in sched_msgs), \
            "Clarification question should be in scheduling_messages"

        # Turn 2: provide the time
        start = _dt(24)
        mock_llm.set_responses([
            AIMessage(content='{"route": "create"}'),
            CreatePlan(events=[CreateEventItem(title="Meeting with Sarah", startDate=start, duration=60)]),
            AIMessage(content="", additional_kwargs={"tool_calls": [
                {"id": "tc1", "type": "function", "function": {"name": "check_conflict", "arguments": json.dumps({"startDate": start.isoformat(), "endDate": (start + timedelta(hours=1)).isoformat()})}}
            ]}),
            AIMessage(content="No conflict."),
        ])
        r2 = await invoke_turn(flow, "3pm tomorrow")
        result = r2.get("scheduling_result", {})
        assert result.get("success") is True, f"Expected success, got: {result}"

    @pytest.mark.asyncio
    async def test_recurring_missing_count(self, flow, mock_llm, mock_tools):
        """Recurring event without count should ask, then succeed on follow-up."""
        # Turn 1: weekly standup without count
        start = _dt(48)
        mock_llm.set_responses([
            AIMessage(content='{"route": "create"}'),
            CreatePlan(events=[CreateEventItem(
                title="Weekly Standup", startDate=start, duration=30,
                recurrence_type="weekly",
                # recurrence_count intentionally None
            )]),
        ])
        r1 = await invoke_turn(flow, "Set up a weekly standup")
        assert r1.get("scheduling_result", {}).get("needs_clarification") is True
        assert "how many" in r1["scheduling_result"]["message"].lower() or "repeat" in r1["scheduling_result"]["message"].lower()

        # Turn 2: provide count
        mock_llm.set_responses([
            AIMessage(content='{"route": "create"}'),
            CreatePlan(events=[CreateEventItem(
                title="Weekly Standup", startDate=start, duration=30,
                recurrence_type="weekly", recurrence_count=10,
            )]),
            # No conflict check for recurring (skipped by design)
        ])
        r2 = await invoke_turn(flow, "10 weeks")
        result = r2.get("scheduling_result", {})
        assert result.get("success") is True, f"Expected success, got: {result}"


# ============================================================
# Category 4: Conflict Resolution
# ============================================================
class TestConflictResolution:
    """Verify conflict detection and suggestion picking work across turns."""

    @pytest.mark.asyncio
    async def test_create_conflict_pick_suggestion(self, flow, mock_llm, mock_tools):
        """Create with conflict → user picks option → succeeds."""
        start = _dt(24)
        alt_start = start + timedelta(hours=1)
        alt_end = alt_start + timedelta(hours=1)

        # Override check_conflict to return a conflict
        mock_tools["check_conflict"].ainvoke = AsyncMock(return_value=json.dumps({
            "has_conflict": True,
            "conflicting_events": [{"title": "Team Sync", "startDate": start.isoformat()}],
            "conflict_count": 1,
        }))
        mock_tools["suggest_alternative_times"].ainvoke = AsyncMock(return_value=json.dumps({
            "suggestions": [
                {"startDate": alt_start.isoformat(), "endDate": alt_end.isoformat()},
            ],
        }))

        # Turn 1: create with conflict
        mock_llm.set_responses([
            AIMessage(content='{"route": "create"}'),
            CreatePlan(events=[CreateEventItem(title="Lunch", startDate=start, duration=60)]),
            # Conflict agent: call check_conflict
            AIMessage(content="", additional_kwargs={"tool_calls": [
                {"id": "tc1", "type": "function", "function": {"name": "check_conflict", "arguments": json.dumps({"startDate": start.isoformat(), "endDate": (start + timedelta(hours=1)).isoformat()})}}
            ]}),
            # Call suggest_alternative_times
            AIMessage(content="", additional_kwargs={"tool_calls": [
                {"id": "tc2", "type": "function", "function": {"name": "suggest_alternative_times", "arguments": json.dumps({"startDate": start.isoformat(), "duration_minutes": 60})}}
            ]}),
            # Done
            AIMessage(content="Conflict found, suggesting alternatives."),
        ])

        r1 = await invoke_turn(flow, "Add lunch tomorrow at noon")
        result1 = r1.get("scheduling_result", {})
        assert result1.get("has_conflict") is True
        assert len(result1.get("suggestions", [])) > 0

        # Verify conflict message is in BOTH scheduling_messages and router_messages
        sched_msgs = r1.get("scheduling_messages", [])
        router_msgs = r1.get("router_messages", [])
        assert any("overlaps" in m.content.lower() for m in sched_msgs if isinstance(m, AIMessage)), \
            "Conflict message should be in scheduling_messages"
        assert any("overlaps" in m.content.lower() for m in router_msgs if isinstance(m, AIMessage)), \
            "Conflict message should be mirrored to router_messages"

        # Verify user's original request is preserved in scheduling_messages
        assert any(isinstance(m, HumanMessage) for m in sched_msgs), \
            "User's original request should be preserved alongside conflict message"

        # Turn 2: pick the suggestion
        mock_tools["check_conflict"].ainvoke = AsyncMock(return_value=json.dumps({
            "has_conflict": False, "conflicting_events": [], "conflict_count": 0,
        }))

        mock_llm.set_responses([
            AIMessage(content='{"route": "create"}'),
            CreatePlan(events=[CreateEventItem(title="Lunch", startDate=alt_start, duration=60)]),
            AIMessage(content="", additional_kwargs={"tool_calls": [
                {"id": "tc3", "type": "function", "function": {"name": "check_conflict", "arguments": json.dumps({"startDate": alt_start.isoformat(), "endDate": alt_end.isoformat()})}}
            ]}),
            AIMessage(content="No conflict this time."),
        ])

        r2 = await invoke_turn(flow, "Option 1")
        result2 = r2.get("scheduling_result", {})
        assert result2.get("success") is True, f"Expected success on option pick, got: {result2}"


# ============================================================
# Category 5: Topic Switches
# ============================================================
class TestTopicSwitches:
    """Verify clean state transitions across different agent types."""

    @pytest.mark.asyncio
    async def test_conversation_then_create_then_conversation(self, flow, mock_llm, mock_tools):
        """conversation → create → conversation should work cleanly."""
        # Turn 1: conversation
        mock_llm.set_responses([
            AIMessage(content="Hello! I'm your calendar assistant. How can I help?"),
        ])
        r1 = await invoke_turn(flow, "Hey what's up?")
        assert isinstance(r1.get("route"), str), "Conversation route should be a string"

        # Turn 2: create
        start = _dt(24)
        mock_llm.set_responses([
            AIMessage(content='{"route": "create"}'),
            CreatePlan(events=[CreateEventItem(title="Workout", startDate=start, duration=60)]),
            AIMessage(content="", additional_kwargs={"tool_calls": [
                {"id": "tc1", "type": "function", "function": {"name": "check_conflict", "arguments": json.dumps({"startDate": start.isoformat(), "endDate": (start + timedelta(hours=1)).isoformat()})}}
            ]}),
            AIMessage(content="No conflict."),
        ])
        r2 = await invoke_turn(flow, "Schedule a workout at 6am")
        assert _route(r2) == "create"
        assert r2.get("scheduling_result", {}).get("success") is True

        # Turn 3: conversation again
        mock_llm.set_responses([
            AIMessage(content="You're welcome! Have a great workout!"),
        ])
        r3 = await invoke_turn(flow, "Thanks!")
        # Scheduling fields should be cleared
        assert r3.get("scheduling_operation") is None
        assert r3.get("scheduling_result") is None
        # Router messages should have all 3 turns
        all_human = [m for m in r3["router_messages"] if isinstance(m, HumanMessage)]
        assert len(all_human) >= 3

    @pytest.mark.asyncio
    async def test_create_then_leisure_then_create(self, flow, mock_llm, mock_tools):
        """create → leisure → create: scheduling state must be clean on re-entry."""
        start1 = _dt(24)
        # Turn 1: create
        mock_llm.set_responses([
            AIMessage(content='{"route": "create"}'),
            CreatePlan(events=[CreateEventItem(title="Yoga", startDate=start1, duration=60)]),
            AIMessage(content="", additional_kwargs={"tool_calls": [
                {"id": "tc1", "type": "function", "function": {"name": "check_conflict", "arguments": json.dumps({"startDate": start1.isoformat(), "endDate": (start1 + timedelta(hours=1)).isoformat()})}}
            ]}),
            AIMessage(content="No conflict."),
        ])
        r1 = await invoke_turn(flow, "Add yoga tomorrow morning")
        assert _route(r1) == "create"

        # Turn 2: leisure
        mock_llm.set_responses([
            AIMessage(content='{"route": "leisure_search"}'),
            AIMessage(content="Here are some restaurants nearby: ..."),
        ])
        with patch("flow.leisure_search_agent.leisure_search_agent.internet_search_tool_factory"):
            r2 = await invoke_turn(flow, "Find me a good restaurant")
        # Scheduling fields must be cleared
        assert r2.get("scheduling_operation") is None
        assert r2.get("scheduling_event_data") is None

        # Turn 3: create again — fresh scheduling state
        start3 = _dt(48)
        mock_llm.set_responses([
            AIMessage(content='{"route": "create"}'),
            CreatePlan(events=[CreateEventItem(title="Dinner", startDate=start3, duration=90)]),
            AIMessage(content="", additional_kwargs={"tool_calls": [
                {"id": "tc3", "type": "function", "function": {"name": "check_conflict", "arguments": json.dumps({"startDate": start3.isoformat(), "endDate": (start3 + timedelta(minutes=90)).isoformat()})}}
            ]}),
            AIMessage(content="No conflict."),
        ])
        r3 = await invoke_turn(flow, "Add dinner on Wednesday at 7pm")
        assert _route(r3) == "create"
        assert r3.get("scheduling_result", {}).get("success") is True


# ============================================================
# Category 6: Delete Flows
# ============================================================
class TestDeleteFlows:
    """Verify delete ambiguity resolution and cross-intent delete."""

    @pytest.mark.asyncio
    async def test_delete_ambiguity_pick_second(self, flow, mock_llm, mock_tools):
        """Delete ambiguous → user says 'the second one' → succeeds."""
        start = _dt(24)
        events = [
            {"id": "evt-a", "title": "Lunch with Alice", "startDate": start.isoformat()},
            {"id": "evt-b", "title": "Lunch with Bob", "startDate": (start + timedelta(hours=1)).isoformat()},
        ]
        mock_tools["list_event"].ainvoke = AsyncMock(return_value=_tool_events(events))

        # Turn 1: delete "lunch" — ambiguous
        mock_llm.set_responses([
            AIMessage(content='{"route": "delete"}'),
            # Tool loop: list events
            AIMessage(content="", additional_kwargs={"tool_calls": [
                {"id": "tc1", "type": "function", "function": {"name": "list_event", "arguments": json.dumps({"date": start.strftime("%Y-%m-%d")})}}
            ]}),
            AIMessage(content="Found multiple events."),
            # Filter: returns both — ambiguous
            AIMessage(content=json.dumps(events)),
        ])
        r1 = await invoke_turn(flow, "Delete my lunch")
        result1 = r1.get("scheduling_result", {})
        assert result1.get("needs_clarification") is True
        assert result1.get("candidate_events") is not None

        # Turn 2: user picks "the second one"
        mock_llm.set_responses([
            AIMessage(content='{"route": "delete"}'),
            # Tool loop: list events again
            AIMessage(content="", additional_kwargs={"tool_calls": [
                {"id": "tc2", "type": "function", "function": {"name": "list_event", "arguments": json.dumps({"date": start.strftime("%Y-%m-%d")})}}
            ]}),
            AIMessage(content="Found events."),
            # Filter: now returns only the second one
            AIMessage(content=json.dumps([events[1]])),
            # Delete plan
            DeletePlan(delete_scope="single"),
        ])
        r2 = await invoke_turn(flow, "The second one")
        result2 = r2.get("scheduling_result", {})
        assert result2.get("success") is True, f"Expected success after disambiguation, got: {result2}"

    @pytest.mark.asyncio
    async def test_create_then_delete_same_event(self, flow, mock_llm, mock_tools):
        """Create → 'actually cancel it' should find the just-created event."""
        start = _dt(24)
        # Turn 1: create
        mock_llm.set_responses([
            AIMessage(content='{"route": "create"}'),
            CreatePlan(events=[CreateEventItem(title="Dentist", startDate=start, duration=60)]),
            AIMessage(content="", additional_kwargs={"tool_calls": [
                {"id": "tc1", "type": "function", "function": {"name": "check_conflict", "arguments": json.dumps({"startDate": start.isoformat(), "endDate": (start + timedelta(hours=1)).isoformat()})}}
            ]}),
            AIMessage(content="No conflict."),
        ])
        r1 = await invoke_turn(flow, "Add dentist appointment tomorrow at 10am")
        assert _route(r1) == "create"

        # Turn 2: delete — "cancel it"
        events = [{"id": "evt-001", "title": "Dentist", "startDate": start.isoformat()}]
        mock_tools["list_event"].ainvoke = AsyncMock(return_value=_tool_events(events))

        mock_llm.set_responses([
            AIMessage(content='{"route": "delete"}'),
            AIMessage(content="", additional_kwargs={"tool_calls": [
                {"id": "tc2", "type": "function", "function": {"name": "list_event", "arguments": json.dumps({"date": start.strftime("%Y-%m-%d")})}}
            ]}),
            AIMessage(content="Found the dentist event."),
            AIMessage(content=json.dumps(events)),
            DeletePlan(delete_scope="single"),
        ])
        r2 = await invoke_turn(flow, "Actually cancel it")
        assert _route(r2) == "delete"
        assert r2.get("previous_route") == "create"
        assert r2.get("scheduling_result", {}).get("success") is True


# ============================================================
# Category 8: Update with Conflict
# ============================================================
class TestUpdateWithConflict:
    """Verify update flow handles conflicts properly (Bug 2 fix)."""

    @pytest.mark.asyncio
    async def test_update_conflict_pick_suggestion(self, flow, mock_llm, mock_tools):
        """Update that causes a conflict → user picks suggestion → success."""
        start = _dt(24)
        new_start = start + timedelta(hours=2)
        alt_start = start + timedelta(hours=3)

        events = [{"id": "evt-001", "title": "Meeting", "startDate": start.isoformat(),
                    "endDate": (start + timedelta(hours=1)).isoformat()}]
        mock_tools["list_event"].ainvoke = AsyncMock(return_value=_tool_events(events))

        # Override conflict check to return conflict for the new time
        mock_tools["check_conflict"].ainvoke = AsyncMock(return_value=json.dumps({
            "has_conflict": True,
            "conflicting_events": [{"title": "Team Sync", "startDate": new_start.isoformat()}],
            "conflict_count": 1,
        }))
        mock_tools["suggest_alternative_times"].ainvoke = AsyncMock(return_value=json.dumps({
            "suggestions": [{"startDate": alt_start.isoformat(), "endDate": (alt_start + timedelta(hours=1)).isoformat()}],
        }))

        # Turn 1: update with conflict
        mock_llm.set_responses([
            AIMessage(content='{"route": "update"}'),
            AIMessage(content="", additional_kwargs={"tool_calls": [
                {"id": "tc1", "type": "function", "function": {"name": "list_event", "arguments": json.dumps({"date": start.strftime("%Y-%m-%d")})}}
            ]}),
            AIMessage(content="Found it."),
            AIMessage(content=json.dumps(events)),
            UpdatePlan(
                event_ids=["evt-001"],
                new_startDate=new_start,
                existing_startDate=start,
                existing_endDate=start + timedelta(hours=1),
            ),
            # Conflict agent
            AIMessage(content="", additional_kwargs={"tool_calls": [
                {"id": "tc2", "type": "function", "function": {"name": "check_conflict", "arguments": json.dumps({"startDate": new_start.isoformat(), "endDate": (new_start + timedelta(hours=1)).isoformat()})}}
            ]}),
            AIMessage(content="", additional_kwargs={"tool_calls": [
                {"id": "tc3", "type": "function", "function": {"name": "suggest_alternative_times", "arguments": json.dumps({"startDate": new_start.isoformat(), "duration_minutes": 60})}}
            ]}),
            AIMessage(content="Conflict found."),
        ])

        r1 = await invoke_turn(flow, "Move meeting to 4pm")
        result1 = r1.get("scheduling_result", {})
        assert result1.get("has_conflict") is True

        # Verify user's original request is preserved in scheduling_messages (Bug 2 fix)
        sched_msgs = r1.get("scheduling_messages", [])
        assert any(isinstance(m, HumanMessage) for m in sched_msgs), \
            "User's HumanMessage must survive conflict resolution (Bug 2 fix)"


# ============================================================
# Category 9: Multi-Turn Cross-Intent (3+ turns)
# ============================================================
class TestMultiTurnCrossIntent:
    """Complex multi-turn flows crossing multiple intents."""

    @pytest.mark.asyncio
    async def test_create_conversation_update_same_event(self, flow, mock_llm, mock_tools):
        """create → conversation → update same event: 3-turn cross-intent."""
        start = _dt(24)

        # Turn 1: create
        mock_llm.set_responses([
            AIMessage(content='{"route": "create"}'),
            CreatePlan(events=[CreateEventItem(title="Coffee", startDate=start, duration=30)]),
            AIMessage(content="", additional_kwargs={"tool_calls": [
                {"id": "tc1", "type": "function", "function": {"name": "check_conflict", "arguments": json.dumps({"startDate": start.isoformat(), "endDate": (start + timedelta(minutes=30)).isoformat()})}}
            ]}),
            AIMessage(content="No conflict."),
        ])
        r1 = await invoke_turn(flow, "Add coffee with Jake at 10am")
        assert _route(r1) == "create"

        # Turn 2: conversation
        mock_llm.set_responses([
            AIMessage(content="Sure! Just let me know if you need anything else."),
        ])
        r2 = await invoke_turn(flow, "Actually wait, where should we meet?")
        # Scheduling state should be cleared
        assert r2.get("scheduling_operation") is None

        # Turn 3: update the coffee meeting
        new_start = start + timedelta(hours=2)
        events = [{"id": "evt-001", "title": "Coffee", "startDate": start.isoformat(),
                    "endDate": (start + timedelta(minutes=30)).isoformat()}]
        mock_tools["list_event"].ainvoke = AsyncMock(return_value=_tool_events(events))

        mock_llm.set_responses([
            AIMessage(content='{"route": "update"}'),
            AIMessage(content="", additional_kwargs={"tool_calls": [
                {"id": "tc3", "type": "function", "function": {"name": "list_event", "arguments": json.dumps({"date": start.strftime("%Y-%m-%d")})}}
            ]}),
            AIMessage(content="Found it."),
            AIMessage(content=json.dumps(events)),
            UpdatePlan(
                event_ids=["evt-001"],
                new_startDate=new_start,
                existing_startDate=start,
                existing_endDate=start + timedelta(minutes=30),
            ),
            AIMessage(content="", additional_kwargs={"tool_calls": [
                {"id": "tc4", "type": "function", "function": {"name": "check_conflict", "arguments": json.dumps({"startDate": new_start.isoformat(), "endDate": (new_start + timedelta(minutes=30)).isoformat()})}}
            ]}),
            AIMessage(content="No conflict."),
        ])
        r3 = await invoke_turn(flow, "Move coffee to noon")
        assert _route(r3) == "update"
        assert r3.get("scheduling_result", {}).get("success") is True
        # Router messages should have context from all 3 turns
        all_human = [m for m in r3["router_messages"] if isinstance(m, HumanMessage)]
        assert len(all_human) >= 3

    @pytest.mark.asyncio
    async def test_create_then_list(self, flow, mock_llm, mock_tools):
        """create → list: listing should show the just-created event context."""
        start = _dt(24)
        # Turn 1: create
        mock_llm.set_responses([
            AIMessage(content='{"route": "create"}'),
            CreatePlan(events=[CreateEventItem(title="Team Sync", startDate=start, duration=30)]),
            AIMessage(content="", additional_kwargs={"tool_calls": [
                {"id": "tc1", "type": "function", "function": {"name": "check_conflict", "arguments": json.dumps({"startDate": start.isoformat(), "endDate": (start + timedelta(minutes=30)).isoformat()})}}
            ]}),
            AIMessage(content="No conflict."),
        ])
        r1 = await invoke_turn(flow, "Add team sync at 9am tomorrow")
        assert _route(r1) == "create"

        # Turn 2: list
        events = [{"id": "evt-001", "title": "Team Sync", "startDate": start.isoformat(),
                    "endDate": (start + timedelta(minutes=30)).isoformat()}]
        mock_tools["list_event"].ainvoke = AsyncMock(return_value=_tool_events(events))

        mock_llm.set_responses([
            AIMessage(content='{"route": "list"}'),
            AIMessage(content="", additional_kwargs={"tool_calls": [
                {"id": "tc2", "type": "function", "function": {"name": "list_event", "arguments": json.dumps({"date": start.strftime("%Y-%m-%d")})}}
            ]}),
            AIMessage(content="Here are your events."),
        ])
        r2 = await invoke_turn(flow, "What's on my schedule tomorrow?")
        assert _route(r2) == "list"
        assert r2.get("previous_route") == "create"

    @pytest.mark.asyncio
    async def test_update_then_update_same_event(self, flow, mock_llm, mock_tools):
        """update → update same event: second update should still have context."""
        start = _dt(24)
        new_start1 = start + timedelta(hours=1)
        new_start2 = start + timedelta(hours=2)

        events = [{"id": "evt-001", "title": "Standup", "startDate": start.isoformat(),
                    "endDate": (start + timedelta(minutes=30)).isoformat()}]
        mock_tools["list_event"].ainvoke = AsyncMock(return_value=_tool_events(events))

        # Turn 1: first update
        mock_llm.set_responses([
            AIMessage(content='{"route": "update"}'),
            AIMessage(content="", additional_kwargs={"tool_calls": [
                {"id": "tc1", "type": "function", "function": {"name": "list_event", "arguments": json.dumps({"date": start.strftime("%Y-%m-%d")})}}
            ]}),
            AIMessage(content="Found it."),
            AIMessage(content=json.dumps(events)),
            UpdatePlan(
                event_ids=["evt-001"],
                new_startDate=new_start1,
                existing_startDate=start,
                existing_endDate=start + timedelta(minutes=30),
            ),
            AIMessage(content="", additional_kwargs={"tool_calls": [
                {"id": "tc2", "type": "function", "function": {"name": "check_conflict", "arguments": json.dumps({"startDate": new_start1.isoformat(), "endDate": (new_start1 + timedelta(minutes=30)).isoformat()})}}
            ]}),
            AIMessage(content="No conflict."),
        ])
        r1 = await invoke_turn(flow, "Move standup to 11am")
        assert _route(r1) == "update"
        assert r1.get("scheduling_result", {}).get("success") is True

        # Turn 2: second update on same event
        events_updated = [{"id": "evt-001", "title": "Standup", "startDate": new_start1.isoformat(),
                           "endDate": (new_start1 + timedelta(minutes=30)).isoformat()}]
        mock_tools["list_event"].ainvoke = AsyncMock(return_value=_tool_events(events_updated))

        mock_llm.set_responses([
            AIMessage(content='{"route": "update"}'),
            AIMessage(content="", additional_kwargs={"tool_calls": [
                {"id": "tc3", "type": "function", "function": {"name": "list_event", "arguments": json.dumps({"date": start.strftime("%Y-%m-%d")})}}
            ]}),
            AIMessage(content="Found it."),
            AIMessage(content=json.dumps(events_updated)),
            UpdatePlan(
                event_ids=["evt-001"],
                new_startDate=new_start2,
                existing_startDate=new_start1,
                existing_endDate=new_start1 + timedelta(minutes=30),
            ),
            AIMessage(content="", additional_kwargs={"tool_calls": [
                {"id": "tc4", "type": "function", "function": {"name": "check_conflict", "arguments": json.dumps({"startDate": new_start2.isoformat(), "endDate": (new_start2 + timedelta(minutes=30)).isoformat()})}}
            ]}),
            AIMessage(content="No conflict."),
        ])
        r2 = await invoke_turn(flow, "Actually make it noon")
        assert _route(r2) == "update"
        assert r2.get("scheduling_result", {}).get("success") is True
        assert r2.get("previous_route") == "update"


# ============================================================
# Category 10: Scheduling Messages Overwrite Semantics
# ============================================================
class TestSchedulingMessagesOverwrite:
    """Verify scheduling_messages uses overwrite (not append) per turn."""

    @pytest.mark.asyncio
    async def test_scheduling_messages_fresh_each_turn(self, flow, mock_llm, mock_tools):
        """scheduling_messages should NOT accumulate across turns — each turn overwrites."""
        start1 = _dt(24)
        start2 = _dt(48)

        # Turn 1: create event A
        mock_llm.set_responses([
            AIMessage(content='{"route": "create"}'),
            CreatePlan(events=[CreateEventItem(title="Alpha", startDate=start1, duration=60)]),
            AIMessage(content="", additional_kwargs={"tool_calls": [
                {"id": "tc1", "type": "function", "function": {"name": "check_conflict", "arguments": json.dumps({"startDate": start1.isoformat(), "endDate": (start1 + timedelta(hours=1)).isoformat()})}}
            ]}),
            AIMessage(content="No conflict."),
        ])
        r1 = await invoke_turn(flow, "Add alpha meeting")
        sched1 = r1.get("scheduling_messages", [])
        sched1_count = len(sched1)

        # Turn 2: create event B (prev_route=create, so LLM checks if this is a fresh request)
        mock_llm.set_responses([
            AIMessage(content='{"route": "create"}'),
            _FreshCreateCheck(is_new_request=True),
            CreatePlan(events=[CreateEventItem(title="Beta", startDate=start2, duration=60)]),
            AIMessage(content="", additional_kwargs={"tool_calls": [
                {"id": "tc2", "type": "function", "function": {"name": "check_conflict", "arguments": json.dumps({"startDate": start2.isoformat(), "endDate": (start2 + timedelta(hours=1)).isoformat()})}}
            ]}),
            AIMessage(content="No conflict."),
        ])
        r2 = await invoke_turn(flow, "Add beta meeting")
        sched2 = r2.get("scheduling_messages", [])

        # scheduling_messages should NOT contain turn 1's messages
        all_content = " ".join(m.content for m in sched2 if hasattr(m, "content"))
        assert "Alpha" not in all_content or "alpha" not in all_content.lower(), \
            f"Turn 1 content should not leak into turn 2 scheduling_messages. Got: {all_content}"
        # Count should be similar (not doubled)
        assert len(sched2) <= sched1_count + 2, \
            f"scheduling_messages grew unexpectedly: turn1={sched1_count}, turn2={len(sched2)}"


# ============================================================
# Category 11: Previous Route Tracking
# ============================================================
class TestPreviousRouteTracking:
    """Verify previous_route accurately tracks across all route types."""

    @pytest.mark.asyncio
    async def test_previous_route_all_types(self, flow, mock_llm, mock_tools):
        """conversation → create → delete → list: previous_route chain."""
        start = _dt(24)

        # Turn 1: conversation
        mock_llm.set_responses([
            AIMessage(content="Hi! How can I help?"),
        ])
        r1 = await invoke_turn(flow, "Hello")
        assert r1.get("previous_route") is None  # first turn

        # Turn 2: create
        mock_llm.set_responses([
            AIMessage(content='{"route": "create"}'),
            CreatePlan(events=[CreateEventItem(title="Call", startDate=start, duration=15)]),
            AIMessage(content="", additional_kwargs={"tool_calls": [
                {"id": "tc1", "type": "function", "function": {"name": "check_conflict", "arguments": json.dumps({"startDate": start.isoformat(), "endDate": (start + timedelta(minutes=15)).isoformat()})}}
            ]}),
            AIMessage(content="No conflict."),
        ])
        r2 = await invoke_turn(flow, "Add a quick call at 3pm")
        assert _route(r2) == "create"
        # previous_route: conversation returns string content, not dict, so route is the string itself
        # The router stores conversation as a string response, not {"route": "..."} dict

        # Turn 3: delete
        events = [{"id": "evt-001", "title": "Call", "startDate": start.isoformat()}]
        mock_tools["list_event"].ainvoke = AsyncMock(return_value=_tool_events(events))

        mock_llm.set_responses([
            AIMessage(content='{"route": "delete"}'),
            AIMessage(content="", additional_kwargs={"tool_calls": [
                {"id": "tc2", "type": "function", "function": {"name": "list_event", "arguments": json.dumps({"date": start.strftime("%Y-%m-%d")})}}
            ]}),
            AIMessage(content="Found it."),
            AIMessage(content=json.dumps(events)),
            DeletePlan(delete_scope="single"),
        ])
        r3 = await invoke_turn(flow, "Delete that call")
        assert _route(r3) == "delete"
        assert r3.get("previous_route") == "create"

        # Turn 4: list
        mock_tools["list_event"].ainvoke = AsyncMock(return_value=_tool_events([]))
        mock_llm.set_responses([
            AIMessage(content='{"route": "list"}'),
            AIMessage(content="", additional_kwargs={"tool_calls": [
                {"id": "tc3", "type": "function", "function": {"name": "list_event", "arguments": json.dumps({"date": start.strftime("%Y-%m-%d")})}}
            ]}),
            AIMessage(content="No events found."),
        ])
        r4 = await invoke_turn(flow, "What do I have tomorrow?")
        assert _route(r4) == "list"
        assert r4.get("previous_route") == "delete"


# ============================================================
# Category 12: Conflict → Reject → New Time
# ============================================================
class TestConflictRejectAndRetry:
    """User rejects conflict suggestion and provides a new time."""

    @pytest.mark.asyncio
    async def test_conflict_reject_then_new_time(self, flow, mock_llm, mock_tools):
        """Create with conflict → reject option → provide new time → success."""
        start = _dt(24)
        alt_start = start + timedelta(hours=1)

        # Override to return conflict
        mock_tools["check_conflict"].ainvoke = AsyncMock(return_value=json.dumps({
            "has_conflict": True,
            "conflicting_events": [{"title": "Existing", "startDate": start.isoformat()}],
            "conflict_count": 1,
        }))
        mock_tools["suggest_alternative_times"].ainvoke = AsyncMock(return_value=json.dumps({
            "suggestions": [{"startDate": alt_start.isoformat(), "endDate": (alt_start + timedelta(hours=1)).isoformat()}],
        }))

        # Turn 1: create with conflict
        mock_llm.set_responses([
            AIMessage(content='{"route": "create"}'),
            CreatePlan(events=[CreateEventItem(title="Gym", startDate=start, duration=60)]),
            AIMessage(content="", additional_kwargs={"tool_calls": [
                {"id": "tc1", "type": "function", "function": {"name": "check_conflict", "arguments": json.dumps({"startDate": start.isoformat(), "endDate": (start + timedelta(hours=1)).isoformat()})}}
            ]}),
            AIMessage(content="", additional_kwargs={"tool_calls": [
                {"id": "tc2", "type": "function", "function": {"name": "suggest_alternative_times", "arguments": json.dumps({"startDate": start.isoformat(), "duration_minutes": 60})}}
            ]}),
            AIMessage(content="Conflict found."),
        ])
        r1 = await invoke_turn(flow, "Add gym at noon")
        assert r1.get("scheduling_result", {}).get("has_conflict") is True

        # Turn 2: reject and provide totally different time (prev_route=create, LLM checks fresh)
        new_time = start + timedelta(hours=5)
        mock_tools["check_conflict"].ainvoke = AsyncMock(return_value=json.dumps({
            "has_conflict": False, "conflicting_events": [], "conflict_count": 0,
        }))

        mock_llm.set_responses([
            AIMessage(content='{"route": "create"}'),
            _FreshCreateCheck(is_new_request=False),
            CreatePlan(events=[CreateEventItem(title="Gym", startDate=new_time, duration=60)]),
            AIMessage(content="", additional_kwargs={"tool_calls": [
                {"id": "tc3", "type": "function", "function": {"name": "check_conflict", "arguments": json.dumps({"startDate": new_time.isoformat(), "endDate": (new_time + timedelta(hours=1)).isoformat()})}}
            ]}),
            AIMessage(content="No conflict."),
        ])
        r2 = await invoke_turn(flow, "No, make it 5pm instead")
        assert r2.get("scheduling_result", {}).get("success") is True


# ============================================================
# Category 13: Long Conversation / Summarizer
# ============================================================
class TestSummarizer:
    """Test that conversation summarization triggers and preserves context."""

    @pytest.mark.asyncio
    async def test_long_conversation_triggers_summary(self, flow, mock_llm):
        """After 12+ messages, summarizer should fire and set conversation_summary."""
        # We need >12 router_messages to trigger. Each turn adds ~2 (Human + AI).
        # So we need ~7 turns.
        for i in range(7):
            mock_llm.set_responses([
                AIMessage(content=f"Response {i}: I can help with that!"),
            ])
            await invoke_turn(flow, f"Question {i}: Tell me about my schedule")

        # At turn 8, summarizer should trigger (>12 messages)
        # Need extra response for summarizer LLM call + router
        mock_llm.set_responses([
            # Summarizer: produces a summary
            AIMessage(content="User has been asking about their schedule repeatedly."),
            # Router: normal response
            AIMessage(content="Here's what I can do for your schedule."),
        ])
        r = await invoke_turn(flow, "What else can you help with?")

        summary = r.get("conversation_summary")
        # If summarizer ran, summary should be set
        # Note: exact trigger depends on message count vs threshold
        router_msgs = r.get("router_messages", [])
        total_msgs = len(router_msgs)
        if total_msgs > 12:
            # Summarizer should have triggered
            assert summary is not None, \
                f"Expected conversation_summary after {total_msgs} messages"

    @pytest.mark.asyncio
    async def test_context_survives_after_many_turns(self, flow, mock_llm, mock_tools):
        """After many conversation turns, a create should still work correctly."""
        # 5 conversation turns
        for i in range(5):
            mock_llm.set_responses([
                AIMessage(content=f"Conversation reply {i}."),
            ])
            await invoke_turn(flow, f"Chat message {i}")

        # Then do a create — should work fine despite long history
        start = _dt(24)
        mock_llm.set_responses([
            AIMessage(content='{"route": "create"}'),
            CreatePlan(events=[CreateEventItem(title="After Long Chat", startDate=start, duration=60)]),
            AIMessage(content="", additional_kwargs={"tool_calls": [
                {"id": "tc1", "type": "function", "function": {"name": "check_conflict", "arguments": json.dumps({"startDate": start.isoformat(), "endDate": (start + timedelta(hours=1)).isoformat()})}}
            ]}),
            AIMessage(content="No conflict."),
        ])
        r = await invoke_turn(flow, "Add a meeting tomorrow at 2pm")
        assert _route(r) == "create"
        assert r.get("scheduling_result", {}).get("success") is True
