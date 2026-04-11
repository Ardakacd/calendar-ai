"""
Scheduling Agent — Agentic Implementation

Handles CREATE, UPDATE, DELETE, and LIST calendar operations.
Replaces the four separate agents (create_agent, update_agent, delete_agent, list_agent)
with a single LLM-driven agent that uses tools.

Flow per operation:
  CREATE  → structured extraction → conflict_resolution_agent → scheduling_finalize (execute)
  UPDATE  → list_event (agentic) → keyword filter → conflict_resolution_agent → scheduling_finalize (execute)
  DELETE  → list_event (agentic) → keyword filter → delete_event (if unambiguous) or ask user
  LIST    → list_event (agentic) → keyword filter → return results
"""

import logging
import json
from typing import Optional, List
from datetime import datetime, timedelta
from langchain_core.messages import SystemMessage, AIMessage, HumanMessage, ToolMessage
from langchain_core.prompts import PromptTemplate
from pydantic import BaseModel, Field
from tenacity import retry, stop_after_attempt, wait_random_exponential, retry_if_exception_type
from openai import OpenAIError, RateLimitError

from ..state import FlowState
from ..llm import model
from ..mcp.calendar_tools_mcp import get_calendar_tools
from .prompt import SCHEDULING_AGENT_SYSTEM_PROMPT, SCHEDULING_FILTER_PROMPT

logger = logging.getLogger(__name__)

retryable_exceptions = (OpenAIError, RateLimitError)


# ---------------------------------------------------------------------------
# Pydantic schemas for structured extraction
# ---------------------------------------------------------------------------

class CreateEventItem(BaseModel):
    title: str = Field(description="Event title in English")
    startDate: datetime = Field(description="Event start time (ISO 8601 with timezone)")
    duration: Optional[int] = Field(None, description="Duration in minutes; calculated from endDate if not stated")
    endDate: Optional[datetime] = Field(None, description="Event end time if explicitly provided by the user")
    location: Optional[str] = Field(None, description="Event location if mentioned")
    description: Optional[str] = Field(None, description="Additional notes or description if mentioned")
    category: Optional[str] = Field(None, description="Event category. Must be one of: 'work', 'personal', 'health', 'social'. Auto-infer from context — e.g. 'doctor appointment' → 'health', 'team meeting' → 'work', 'birthday party' → 'social', 'workout' → 'health', 'lunch with friend' → 'social'.")
    recurrence_type: Optional[str] = Field(None, description="Recurrence frequency: 'daily', 'weekly', 'monthly', or 'yearly'. Only set when the user explicitly asks for a recurring event.")
    recurrence_count: Optional[int] = Field(None, description="Number of occurrences. Required when recurrence_type is set. e.g. 'every week for 10 weeks' → recurrence_count=10")
    recurrence_interval: Optional[int] = Field(None, description="Repeat every N periods. Default 1. Use 2 for bi-weekly ('every other week'), 3 for every 3 months, etc.")
    recurrence_byweekday: Optional[str] = Field(None, description="Comma-separated weekday codes. 'MO,TU,WE,TH,FR' for every weekday; 'MO,WE,FR' for Mon/Wed/Fri; 'MO' for weekly on Mondays only.")
    recurrence_bysetpos: Optional[int] = Field(None, description="Positional selector within the period. 1=first, 2=second, -1=last. Combined with byweekday: freq=monthly, byweekday=MO, bysetpos=1 → first Monday of each month.")


class CreatePlan(BaseModel):
    events: List[CreateEventItem] = Field(description="All events to create (one or more)")
    clarification_needed: Optional[str] = Field(
        None, description="Set this if start time or title is missing or ambiguous — ask the user"
    )


class DeletePlan(BaseModel):
    delete_scope: str = Field(
        description="'single' = one specific occurrence, 'all' = entire series, 'future' = this and all future occurrences. Use 'single' for non-recurring events."
    )
    recurrence_id: Optional[str] = Field(
        None,
        description="The recurrence_id of the series. NEVER invent, shorten, or paraphrase — copy the full UUID exactly as it appears in the recurrence_id field of the list results. Required when delete_scope is 'all' or 'future'."
    )
    series_from_date: Optional[str] = Field(
        None,
        description="ISO 8601 datetime string. For 'future' scope: the startDate of the earliest occurrence to delete. All occurrences on or after this date will be removed. REQUIRED when delete_scope is 'future' — omitting it deletes the entire series instead."
    )
    clarification_needed: Optional[str] = Field(
        None,
        description="Set this if the scope is ambiguous for a recurring event and you need to ask the user whether they mean just this occurrence or the whole series."
    )


class UpdatePlan(BaseModel):
    event_ids: List[str] = Field(description="UUIDs of the event(s) to update, taken from list results. NEVER invent or guess a UUID — copy exactly from the event_id field in the list results.")
    new_title: Optional[str] = Field(None, description="New title if the user wants to change it")
    new_startDate: Optional[datetime] = Field(None, description="New start time if the user wants to change it")
    new_duration: Optional[int] = Field(None, description="New duration in minutes if the user wants to change it")
    new_location: Optional[str] = Field(None, description="New location if the user wants to change it")
    new_description: Optional[str] = Field(None, description="New notes/description if the user wants to change it")
    new_category: Optional[str] = Field(None, description="New category if the user wants to change it: 'work', 'personal', 'health', or 'social'")
    existing_startDate: Optional[datetime] = Field(
        None, description="Current start time of the target event(s), from list results. REQUIRED when the user is changing the time — omitting this silently skips the time shift."
    )
    existing_endDate: Optional[datetime] = Field(
        None, description="Current end time of the target event(s), from list results"
    )
    update_scope: Optional[str] = Field(
        None,
        description="For recurring events only. 'single' = only this occurrence, 'all' = every occurrence in the series, 'future' = this and all future occurrences. Leave None for non-recurring events."
    )
    recurrence_id: Optional[str] = Field(
        None,
        description="The recurrence_id of the series. NEVER invent, shorten, or paraphrase — copy the full UUID exactly as it appears in the recurrence_id field of the list results. Required when update_scope is 'all' or 'future'."
    )
    series_from_date: Optional[datetime] = Field(
        None,
        description="For 'future' scope: the startDate of the occurrence the user is referring to. All occurrences on or after this date will be updated. REQUIRED when update_scope is 'future' — omitting this updates ALL occurrences instead."
    )
    clarification_needed: Optional[str] = Field(
        None, description="Set this if multiple events match ambiguously or information is unclear"
    )


# ---------------------------------------------------------------------------
# Main scheduling agent node
# ---------------------------------------------------------------------------

@retry(
    wait=wait_random_exponential(min=1, max=10),
    stop=stop_after_attempt(3),
    retry=retry_if_exception_type(retryable_exceptions),
)
async def scheduling_agent(state: FlowState):
    operation = state['route']['route']
    user_id = state['user_id']

    system_prompt = PromptTemplate.from_template(SCHEDULING_AGENT_SYSTEM_PROMPT).format(
        current_datetime=state['current_datetime'],
        weekday=state['weekday'],
        days_in_month=state['days_in_month'],
    )

    # Extract user's local timezone from current_datetime so stored UTC dates
    # are converted to local time before the LLM sees them (fixes "+00:00" mismatch)
    user_tz = _extract_tz(state.get('current_datetime', ''))

    if operation == 'create':
        result = await _handle_create(state, system_prompt)
    else:
        async with get_calendar_tools(user_id, user_tz) as mcp_tools:
            tools_map = {t.name: t for t in mcp_tools}
            if operation == 'update':
                result = await _handle_update(state, system_prompt, tools_map)
            elif operation == 'delete':
                result = await _handle_delete(state, system_prompt, tools_map)
            elif operation == 'list':
                result = await _handle_list(state, system_prompt, tools_map)
            else:
                result = None

        if result is None:
            msg = "I couldn't determine what calendar operation to perform. Please try again."
            result = {
                "scheduling_messages": [AIMessage(content=msg)],
                "scheduling_result": {"message": msg, "success": False},
            }

    # Always stamp the current operation so scheduling_finalize routes correctly
    # even when a handler returns early (no-match, clarification, ambiguous)
    result.setdefault("scheduling_operation", operation)

    # Mirror the last scheduling message to router_messages so the router has
    # full conversation context on the next turn (multi-turn flows)
    sched_msgs = result.get("scheduling_messages", [])
    if sched_msgs and hasattr(sched_msgs[-1], "content"):
        result["router_messages"] = [AIMessage(content=sched_msgs[-1].content)]

    return result


# ---------------------------------------------------------------------------
# CREATE
# ---------------------------------------------------------------------------

def _extract_tz(current_datetime_str: str):
    """Return a timezone object parsed from the current_datetime ISO string, or UTC as fallback."""
    from datetime import timezone, timedelta
    try:
        dt = datetime.fromisoformat(current_datetime_str)
        if dt.tzinfo is not None:
            return dt.tzinfo
    except Exception:
        pass
    return timezone.utc


def _conversation_history(state: FlowState) -> list:
    """Return previous scheduling_messages from state, excluding SystemMessages."""
    return [m for m in state.get('scheduling_messages', []) if not isinstance(m, SystemMessage)]


async def _handle_create(state: FlowState, system_prompt: str) -> dict:
    """
    Structured extraction of one or more events from the user's message.
    Includes conversation history so the LLM can resolve references like "book option 2".
    No DB calls — conflict check happens next via conflict_resolution_agent.
    """
    # scheduling_messages: previous scheduling turns (what event was being created, conflicts seen)
    # router_messages: full cross-agent conversation context (conflict replies, prior turns)
    # Combine both so the LLM can resolve references like "it" or "option 2"
    sched_history = _conversation_history(state)
    router_history = [m for m in state.get('router_messages', []) if not isinstance(m, SystemMessage)]

    # Deduplicate: keep router_history entries not already covered by sched_history content
    sched_contents = {m.content for m in sched_history if hasattr(m, 'content')}
    extra_router = [m for m in router_history if m.content not in sched_contents]

    history = sched_history + extra_router

    plan: CreatePlan = await model.with_structured_output(CreatePlan).ainvoke(
        [SystemMessage(content=system_prompt)]
        + history
        + [HumanMessage(content=state['input_text'])]
    )

    if plan.clarification_needed:
        return {
            "scheduling_messages": [AIMessage(content=plan.clarification_needed)],
            "scheduling_result": {
                "message": plan.clarification_needed,
                "needs_clarification": True,
                "success": False,
            },
            "conflict_check_request": None,
            "conflict_check_result": None,
            "scheduling_event_data": None,
        }

    # Guard: recurrence_type without recurrence_count — ask before silently creating 1 event
    for item in plan.events:
        if item.recurrence_type and not item.recurrence_count:
            msg = f"How many times would you like to repeat \"{item.title}\"? (e.g. \"10 times\", \"every week for 3 months\")"
            return {
                "scheduling_messages": [AIMessage(content=msg)],
                "scheduling_result": {
                    "message": msg,
                    "needs_clarification": True,
                    "success": False,
                },
                "conflict_check_request": None,
                "conflict_check_result": None,
                "scheduling_event_data": None,
            }

    # Resolve endDate and duration for each event
    events_data = []
    for item in plan.events:
        start = item.startDate
        if item.endDate and not item.duration:
            duration = int((item.endDate - start).total_seconds() / 60)
            end = item.endDate
        elif item.duration:
            duration = item.duration
            end = start + timedelta(minutes=duration)
        else:
            duration = 60  # default 1 hour
            end = start + timedelta(minutes=60)

        events_data.append({
            "title": item.title,
            "startDate": start.isoformat(),
            "endDate": end.isoformat(),
            "duration_minutes": duration,
            "location": item.location,
            "description": item.description,
            "category": item.category,
            "recurrence_type": item.recurrence_type,
            "recurrence_count": item.recurrence_count,
            "recurrence_interval": item.recurrence_interval,
            "recurrence_byweekday": item.recurrence_byweekday,
            "recurrence_bysetpos": item.recurrence_bysetpos,
        })

    # Recurring series: skip the single-slot pre-check — the adapter loop checks every
    # occurrence at commit time and raises RecurringConflictError with full details.
    # Running a pre-check on slot 1 only would produce a misleading "no conflict" message
    # when a later slot actually conflicts.
    has_recurrence = any(e.get("recurrence_type") for e in events_data)
    first = events_data[0]
    conflict_check_request = None if has_recurrence else {
        "startDate": first["startDate"],
        "endDate": first["endDate"],
        "duration_minutes": first["duration_minutes"],
    }

    titles_fmt = ", ".join(f"“{e['title']}”" for e in events_data)
    if has_recurrence:
        ack = f"Got it — I’ll set up {titles_fmt} as recurring on your calendar."
    else:
        ack = f"Got it — adding {titles_fmt}. Checking the time for conflicts…"

    return {
        "scheduling_operation": "create",
        "scheduling_event_data": {"events": events_data},
        "conflict_check_request": conflict_check_request,
        "conflict_check_result": None,
        # Store the user request + AI ack so next-turn history resolves "it" / "option 2"
        "scheduling_messages": [
            HumanMessage(content=state['input_text']),
            AIMessage(content=ack),
        ],
    }


# ---------------------------------------------------------------------------
# UPDATE
# ---------------------------------------------------------------------------

async def _handle_update(state: FlowState, system_prompt: str, tools_map: dict) -> dict:
    """
    Phase 1: Use list_event to find events in the relevant date range.
    Phase 2: Keyword-filter the results, then extract the update plan.
    Conversation history is included so the LLM understands multi-turn context.
    """
    list_tool = tools_map['list_event']
    model_with_tools = model.bind_tools([list_tool])

    history = _conversation_history(state)
    messages = (
        [SystemMessage(content=system_prompt)]
        + history
        + [HumanMessage(content=state['input_text'])]
    )

    # Agentic search loop
    messages = await _run_tool_loop(messages, model_with_tools, {'list_event': list_tool}, max_iter=5)

    # Collect all events returned by list_event across all tool calls
    all_events = _extract_events_from_messages(messages)

    # Build recent conversation context so LLM can resolve pronouns like "it" or "that meeting"
    recent_msgs = [m for m in _conversation_history(state) if not isinstance(m, SystemMessage)][-4:]
    filter_context = "\n".join(
        f"{'User' if isinstance(m, HumanMessage) else 'Assistant'}: {m.content}"
        for m in recent_msgs if hasattr(m, 'content')
    )

    # Keyword-filter by title/location/duration
    filtered_events = await _filter_events(all_events, state['input_text'], intent="find the event to update", context=filter_context)

    if not filtered_events:
        msg = "I couldn’t find anything that matches. A bit more detail (title, date, or place) would help."
        return {
            "scheduling_messages": [AIMessage(content=msg)],
            "scheduling_result": {"message": msg, "success": False},
            "conflict_check_request": None,
            "conflict_check_result": None,
        }

    # Structured extraction of the update plan using filtered events as context.
    # Only include the last 2 scheduling messages (enough to resolve "it"/"option 2"
    # references) rather than full history, so older turns (e.g. a prior standup
    # update) don't bleed in and cause the LLM to pick the wrong event.
    filter_context = json.dumps(filtered_events, default=str, indent=2)
    recent_history = [m for m in _conversation_history(state) if not isinstance(m, SystemMessage)][-2:]
    plan: UpdatePlan = await model.with_structured_output(UpdatePlan).ainvoke([
        SystemMessage(content=system_prompt),
        *recent_history,
        HumanMessage(content=(
            f"User request: \"{state['input_text']}\"\n\n"
            f"Matching events found in the calendar:\n{filter_context}\n\n"
            "Extract the update plan: which event(s) to update and what fields to change."
        )),
    ])

    if plan.clarification_needed:
        return {
            "scheduling_messages": [AIMessage(content=plan.clarification_needed)],
            "scheduling_result": {
                "message": plan.clarification_needed,
                "needs_clarification": True,
                "success": False,
            },
            "conflict_check_request": None,
            "conflict_check_result": None,
        }

    if not plan.event_ids:
        msg = "I’m not sure which event you mean — which title or time should I change?"
        return {
            "scheduling_messages": [AIMessage(content=msg)],
            "scheduling_result": {"message": msg, "success": False},
            "conflict_check_request": None,
            "conflict_check_result": None,
        }

    # Guard: future-scope series update without series_from_date would silently update all occurrences
    if plan.update_scope == "future" and not plan.series_from_date:
        msg = "Which occurrence did you want to start from? Please tell me the date so I know where to begin the update."
        return {
            "scheduling_messages": [AIMessage(content=msg)],
            "scheduling_result": {"message": msg, "needs_clarification": True, "success": False},
            "conflict_check_request": None,
            "conflict_check_result": None,
        }

    # Only trigger conflict check if the start time is actually changing
    check_start = plan.new_startDate
    check_end = None
    if check_start:
        if plan.new_duration:
            check_end = check_start + timedelta(minutes=plan.new_duration)
        elif plan.existing_endDate:
            check_end = plan.existing_endDate
        else:
            check_end = check_start + timedelta(hours=1)

    duration_minutes = 60
    if check_start and check_end:
        duration_minutes = int((check_end - check_start).total_seconds() / 60)

    # Compute time_shift for series updates that change start time
    time_shift_seconds = None
    if plan.update_scope in ("all", "future") and plan.new_startDate and plan.existing_startDate:
        time_shift_seconds = int((plan.new_startDate - plan.existing_startDate).total_seconds())

    return {
        "scheduling_operation": "update",
        "conflict_check_result": None,
        "scheduling_event_data": {
            "event_ids": plan.event_ids,
            "update_args": {
                "title": plan.new_title,
                "startDate": plan.new_startDate.isoformat() if plan.new_startDate else None,
                "duration": plan.new_duration,
                "location": plan.new_location,
                "description": plan.new_description,
                "category": plan.new_category,
            },
            "series_update": plan.update_scope in ("all", "future"),
            "update_scope": plan.update_scope,
            "recurrence_id": plan.recurrence_id,
            "series_from_date": plan.series_from_date.isoformat() if plan.series_from_date else None,
            "time_shift_seconds": time_shift_seconds,
        },
        "conflict_check_request": {
            "startDate": check_start.isoformat() if check_start else None,
            "endDate": check_end.isoformat() if check_end else None,
            "duration_minutes": duration_minutes,
            "exclude_event_id": plan.event_ids[0] if plan.event_ids else None,
        },
        "scheduling_messages": [m for m in messages if not isinstance(m, SystemMessage)],
    }


# ---------------------------------------------------------------------------
# DELETE
# ---------------------------------------------------------------------------

async def _handle_delete(state: FlowState, system_prompt: str, tools_map: dict) -> dict:
    """
    Phase 1: Use list_event to find events in the relevant date range.
    Phase 2: Keyword-filter, then delete if unambiguous or ask user.
    Conversation history is included for multi-turn context.
    """
    list_tool = tools_map['list_event']
    delete_tool = tools_map['delete_event']

    _delete_all_keywords = {"both", "all", "every", "all of them", "each", "each one"}
    input_lower = state.get('input_text', '').lower()
    user_wants_all = any(kw in input_lower for kw in _delete_all_keywords)

    history_contents = " ".join(
        m.content for m in state.get('scheduling_messages', [])
        if hasattr(m, 'content')
    ).lower()
    already_asked = "multiple events match" in history_contents or "which one did you mean" in history_contents

    # If the user replied "both/all" to a previous clarification, skip re-listing entirely
    # and use the candidate_events stored from that turn so we delete exactly the right events.
    stored_candidates = state.get('scheduling_result', {}).get('candidate_events', [])
    if user_wants_all and already_asked and stored_candidates:
        return await _delete_events(stored_candidates, delete_tool)

    # --- Normal flow: list → filter → decide ---
    model_with_tools = model.bind_tools([list_tool])
    history = _conversation_history(state)
    messages = (
        [SystemMessage(content=system_prompt)]
        + history
        + [HumanMessage(content=state['input_text'])]
    )
    messages = await _run_tool_loop(messages, model_with_tools, {'list_event': list_tool}, max_iter=5)

    all_events = _extract_events_from_messages(messages)

    recent_msgs = [m for m in _conversation_history(state) if not isinstance(m, SystemMessage)][-4:]
    filter_context = "\n".join(
        f"{'User' if isinstance(m, HumanMessage) else 'Assistant'}: {m.content}"
        for m in recent_msgs if hasattr(m, 'content')
    )
    filtered_events = await _filter_events(
        all_events, state['input_text'], intent="find the event to delete", context=filter_context
    )

    if not filtered_events:
        msg = "I couldn’t find any events that match."
        return {
            "scheduling_messages": [AIMessage(content=msg)],
            "scheduling_result": {"message": msg, "success": False},
            "conflict_check_request": None,
            "conflict_check_result": None,
            "is_success": True,
        }

    # If any filtered event is recurring, ask the LLM to determine delete scope.
    has_recurring = any(e.get('recurrence_id') for e in filtered_events)
    if has_recurring:
        events_context = json.dumps(filtered_events, default=str, indent=2)
        recent_history = [m for m in _conversation_history(state) if not isinstance(m, SystemMessage)][-2:]
        delete_plan: DeletePlan = await model.with_structured_output(DeletePlan).ainvoke([
            SystemMessage(content=system_prompt),
            *recent_history,
            HumanMessage(content=(
                f"User request: \"{state['input_text']}\"\n\n"
                f"Matching events found:\n{events_context}\n\n"
                "Determine the delete scope. If the event is recurring and the user clearly wants "
                "the whole series or future occurrences deleted, set delete_scope accordingly. "
                "If it's ambiguous whether they mean just this occurrence or the whole series, "
                "set clarification_needed and ask."
            )),
        ])

        if delete_plan.clarification_needed:
            return {
                "scheduling_messages": [AIMessage(content=delete_plan.clarification_needed)],
                "scheduling_result": {
                    "message": delete_plan.clarification_needed,
                    "needs_clarification": True,
                    "candidate_events": filtered_events,
                    "success": False,
                },
                "conflict_check_request": None,
                "conflict_check_result": None,
                "is_success": True,
            }

        if delete_plan.delete_scope in ("all", "future") and delete_plan.recurrence_id:
            # Guard: future scope requires a from_date — without it we'd delete the entire series
            if delete_plan.delete_scope == "future" and not delete_plan.series_from_date:
                msg = "Which occurrence did you want to start from? Please tell me the date so I know where to cut off."
                return {
                    "scheduling_messages": [AIMessage(content=msg)],
                    "scheduling_result": {"message": msg, "needs_clarification": True, "candidate_events": filtered_events, "success": False},
                    "conflict_check_request": None,
                    "conflict_check_result": None,
                    "is_success": True,
                }
            from_date = None
            if delete_plan.delete_scope == "future" and delete_plan.series_from_date:
                try:
                    from_date = datetime.fromisoformat(delete_plan.series_from_date)
                except Exception:
                    pass
            series_title = filtered_events[0].get('title', '') if filtered_events else ''
            return await _delete_series(delete_plan.recurrence_id, state['user_id'], from_date, title=series_title)

    # Non-recurring path (or recurring single-occurrence): delete matched event(s) by ID
    if len(filtered_events) == 1:
        return await _delete_events(filtered_events, delete_tool)

    # Multiple matches — if user already said "both/all" in this same message, delete all
    if user_wants_all:
        return await _delete_events(filtered_events, delete_tool)

    # Ask the user which one
    lines = ["Multiple events match your request. Which one did you mean?\n"]
    for i, e in enumerate(filtered_events, 1):
        start = e.get('startDate', '')
        try:
            dt = datetime.fromisoformat(start)
            start_fmt = dt.strftime("%a %b %-d, %-I:%M %p")
        except Exception:
            start_fmt = start
        lines.append(f"{i}. {e.get('title')} — {start_fmt}")
    msg = "\n".join(lines)
    return {
        "scheduling_messages": [AIMessage(content=msg)],
        "scheduling_result": {
            "message": msg,
            "needs_clarification": True,
            "candidate_events": filtered_events,
            "success": False,
        },
        "conflict_check_request": None,
        "conflict_check_result": None,
        "is_success": True,
    }


async def _delete_events(events: list, delete_tool) -> dict:
    """Execute delete for one or more events and return a result dict."""
    deleted_events = []
    failed_titles = []

    for event in events:
        event_id = event.get('id') or event.get('event_id')
        try:
            result = _parse_mcp_result(await delete_tool.ainvoke({"event_id": event_id}))
            if result.get('success'):
                deleted_events.append(event)
            else:
                failed_titles.append(event.get('title', event_id))
        except Exception as e:
            logger.error(f"Error deleting event {event_id}: {e}", exc_info=True)
            failed_titles.append(event.get('title', event_id))

    if not deleted_events and not failed_titles:
        # Edge case: empty input
        msg = "No events to delete."
        return {
            "scheduling_messages": [AIMessage(content=msg)],
            "scheduling_result": {"message": msg, "success": False, "events": []},
            "conflict_check_request": None,
            "conflict_check_result": None,
            "is_success": False,
        }

    if deleted_events and not failed_titles:
        if len(deleted_events) == 1:
            msg = f"Done — removed “{deleted_events[0].get('title')}” from your calendar."
        elif len(deleted_events) == 2:
            msg = f"Done — removed “{deleted_events[0].get('title')}” and “{deleted_events[1].get('title')}”."
        else:
            msg = f"Done — removed {len(deleted_events)} events from your calendar."
    elif deleted_events:
        removed = " and ".join(f"'{e.get('title')}'" for e in deleted_events) if len(deleted_events) <= 2 else f"{len(deleted_events)} events"
        msg = f"Removed {removed}, but couldn't remove: {', '.join(failed_titles)}."
    else:
        msg = "Couldn't remove the event — it may no longer exist or you may not have permission."

    return {
        "scheduling_operation": "delete",
        "scheduling_messages": [AIMessage(content=msg)],
        "scheduling_result": {"message": msg, "success": bool(deleted_events), "events": deleted_events},
        "conflict_check_request": None,
        "conflict_check_result": None,
        "is_success": bool(deleted_events),
    }


async def _delete_series(recurrence_id: str, user_id: int, from_date=None, title: str = "") -> dict:
    """Delete an entire recurring series (or all future occurrences) directly via the adapter."""
    from database.config import get_async_db_context_manager
    from adapter.event_adapter import EventAdapter
    display = f"“{title}”" if title else "this series"
    try:
        async with get_async_db_context_manager() as db:
            adapter = EventAdapter(db)
            deleted = await adapter.delete_by_recurrence_id(recurrence_id, user_id, from_date=from_date)
        n = deleted
        if from_date:
            msg = f"Done — removed {n} upcoming occurrence{'s' if n != 1 else ''} of {display}."
        else:
            msg = f"Done — removed {display} and all {n} occurrence{'s' if n != 1 else ''} in the series."
    except Exception as e:
        logger.error(f"Error deleting series {recurrence_id}: {e}", exc_info=True)
        msg = "Something went wrong removing the series. Please try again."
        deleted = 0

    return {
        "scheduling_operation": "delete",
        "scheduling_messages": [AIMessage(content=msg)],
        "scheduling_result": {"message": msg, "success": bool(deleted)},
        "conflict_check_request": None,
        "conflict_check_result": None,
        "is_success": bool(deleted),
    }


# ---------------------------------------------------------------------------
# LIST
# ---------------------------------------------------------------------------

async def _handle_list(state: FlowState, system_prompt: str, tools_map: dict) -> dict:
    """
    Use list_event to retrieve events, then keyword-filter and present results.
    Conversation history is included for multi-turn context.
    """
    list_tool = tools_map['list_event']
    model_with_tools = model.bind_tools([list_tool])

    history = _conversation_history(state)
    messages = (
        [SystemMessage(content=system_prompt)]
        + history
        + [HumanMessage(content=state['input_text'])]
    )

    messages = await _run_tool_loop(messages, model_with_tools, {'list_event': list_tool}, max_iter=4)

    all_events = _extract_events_from_messages(messages)
    filtered_events = await _filter_events(all_events, state['input_text'], intent="list events matching the user's request")

    # If filter incorrectly returned empty but events exist, show all of them.
    # For LIST the user always wants to see events — an empty filter result is almost
    # certainly a filter error, not a genuine "no match".
    if not filtered_events and all_events:
        filtered_events = all_events

    if not filtered_events:
        msg = "Nothing on your calendar matches that."
        return {
            "scheduling_operation": "list",
            "scheduling_messages": [AIMessage(content=msg)],
            "scheduling_result": {"message": msg, "events": [], "success": True},
            "conflict_check_request": None,
            "conflict_check_result": None,
            "is_success": True,
        }

    count = len(filtered_events)
    msg = f"Here’s what I found — {count} event{'s' if count != 1 else ''}."

    return {
        "scheduling_operation": "list",
        "scheduling_messages": [AIMessage(content=msg)],
        "scheduling_result": {"message": msg, "events": filtered_events, "success": True},
        "conflict_check_request": None,
        "conflict_check_result": None,
        "is_success": True,
    }


# ---------------------------------------------------------------------------
# Scheduling finalize node
# ---------------------------------------------------------------------------

def _format_suggestion_dt(iso: str | None) -> str:
    """Format an ISO datetime string as 'Mon Mar 28, 6:30 PM'."""
    if not iso:
        return "?"
    try:
        dt = datetime.fromisoformat(iso)
        day = str(dt.day)
        hour = dt.hour % 12 or 12
        minute = dt.strftime("%M")
        ampm = "AM" if dt.hour < 12 else "PM"
        month = dt.strftime("%b")
        weekday = dt.strftime("%a")
        return f"{weekday} {month} {day}, {hour}:{minute} {ampm}"
    except Exception:
        return iso


async def scheduling_finalize(state: FlowState):
    """
    Called after conflict_resolution_agent for CREATE and UPDATE operations.
    - No conflict → execute the CRUD in the database.
    - Conflict detected → return suggestions to the user, do not execute.
    For DELETE and LIST, scheduling_agent already handled everything — this is a pass-through.
    """
    operation = state.get('scheduling_operation')

    # DELETE and LIST are fully handled by scheduling_agent
    if operation in ('delete', 'list', None):
        return {"is_success": True}

    conflict_result = state.get('conflict_check_result', {})
    event_data = state.get('scheduling_event_data', {})
    user_id = state['user_id']

    # Conflict check failed (e.g. rate limit) — do not execute, ask user to retry
    if conflict_result and conflict_result.get('check_failed'):
        msg = "I couldn’t check your calendar for conflicts just now. Try again in a moment."
        return {
            "scheduling_result": {"message": msg, "success": False},
            "scheduling_messages": [AIMessage(content=msg)],
            "is_success": False,
        }

    # No conflict check was run (e.g. title-only update or clarification path)
    if not conflict_result:
        # Still execute if we have event data (title/location-only update)
        if event_data:
            try:
                user_tz = _extract_tz(state.get('current_datetime', ''))
                async with get_calendar_tools(user_id, user_tz) as mcp_tools:
                    tools_map = {t.name: t for t in mcp_tools}
                    if operation == 'create':
                        return await _execute_create(event_data, tools_map)
                    elif operation == 'update':
                        return await _execute_update(event_data, tools_map, user_id=user_id)
            except Exception as e:
                logger.error(f"Error in scheduling_finalize ({operation}): {e}", exc_info=True)
                msg = "Something went wrong while updating your calendar. Please try again."
                return {
                    "scheduling_result": {"message": msg, "success": False},
                    "scheduling_messages": [AIMessage(content=msg)],
                    "is_success": False,
                }
        return {"is_success": True}

    if conflict_result.get('has_conflict'):
        suggestions = conflict_result.get('suggestions', [])
        conflicting = conflict_result.get('conflicting_events', [])

        conflict_titles = " and ".join(f"“{e.get('title', 'another event')}”" for e in conflicting) if conflicting else "another event"
        msg = f"That time overlaps with {conflict_titles}."
        if suggestions:
            lines = ["\n\nHere are some open slots nearby:"]
            for i, s in enumerate(suggestions, 1):
                start = _format_suggestion_dt(s.get('startDate'))
                end = _format_suggestion_dt(s.get('endDate'))
                lines.append(f"  {i}. {start} – {end}")
            lines.append("\nPick one of these, or tell me another time you’d like.")
            msg += "\n".join(lines)
        else:
            msg += " I couldn’t find open slots nearby — try another day or time?"
        return {
            "scheduling_result": {
                "message": msg,
                "has_conflict": True,
                "suggestions": suggestions,
                "success": False,
            },
            "scheduling_messages": [AIMessage(content=msg)],
            "router_messages": [AIMessage(content=msg)],
            "is_success": True,
        }

    # No conflict — execute
    try:
        user_tz = _extract_tz(state.get('current_datetime', ''))
        async with get_calendar_tools(user_id, user_tz) as mcp_tools:
            tools_map = {t.name: t for t in mcp_tools}
            if operation == 'create':
                result = await _execute_create(event_data, tools_map)
            elif operation == 'update':
                result = await _execute_update(event_data, tools_map, user_id=user_id)
            else:
                return {"is_success": True}
        # Mirror to router_messages for multi-turn context
        sched_msgs = result.get("scheduling_messages", [])
        if sched_msgs and hasattr(sched_msgs[-1], "content"):
            result["router_messages"] = [AIMessage(content=sched_msgs[-1].content)]
        return result
    except Exception as e:
        logger.error(f"Error in scheduling_finalize ({operation}): {e}", exc_info=True)
        msg = "Something went wrong while updating your calendar. Please try again."
        return {
            "scheduling_result": {"message": msg, "success": False},
            "scheduling_messages": [AIMessage(content=msg)],
            "router_messages": [AIMessage(content=msg)],
            "is_success": False,
        }


async def _execute_create(event_data: dict, tools_map: dict) -> dict:
    create_tool = tools_map['create_event']
    events_to_create = event_data.get("events", [])
    created = []
    for ev in events_to_create:
        args = {
            "title": ev['title'],
            "startDate": ev['startDate'],
        }
        if ev.get('endDate'):
            args["endDate"] = ev['endDate']
        if ev.get('location'):
            args["location"] = ev['location']
        if ev.get('description'):
            args["description"] = ev['description']
        if ev.get('category'):
            args["category"] = ev['category']
        if ev.get('recurrence_type') and ev.get('recurrence_count'):
            args["recurrence_type"] = ev['recurrence_type']
            args["recurrence_count"] = ev['recurrence_count']
        if ev.get('recurrence_interval'):
            args["recurrence_interval"] = ev['recurrence_interval']
        if ev.get('recurrence_byweekday'):
            args["recurrence_byweekday"] = ev['recurrence_byweekday']
        if ev.get('recurrence_bysetpos') is not None:
            args["recurrence_bysetpos"] = ev['recurrence_bysetpos']
        result = _parse_mcp_result(await create_tool.ainvoke(args))
        if result.get("has_recurring_conflict"):
            conflicts = result.get("conflicts", [])
            title = ev.get('title', 'the event')
            n = len(conflicts)
            lines = [
                f"Couldn’t add “{title}” — {n} proposed time{'s' if n != 1 else ''} overlap something already on your calendar:"
            ]
            for c in conflicts:
                start_fmt = _format_suggestion_dt(c.get("startDate"))
                lines.append(
                    f"  • Occurrence {c['index'] + 1} ({start_fmt}) — overlaps with “{c['conflicting_title']}”"
                )
            lines.append("\nNothing was added. Want to try different times?")
            msg = "\n".join(lines)
            return {
                "scheduling_result": {"message": msg, "has_conflict": True, "success": False},
                "scheduling_messages": [AIMessage(content=msg)],
                "is_success": False,
            }
        created.append(result)

    if len(created) == 1:
        r = created[0]
        n = r.get('occurrences_created', 0)
        title = r.get('title', '')
        start_fmt = _format_suggestion_dt(r.get('startDate', ''))
        if n:
            freq = r.get('recurrence_type', '')
            freq_label = f"{freq} " if freq else ""
            occ_label = f"{n} {freq_label}occurrence{'s' if n != 1 else ''}"
            msg = f"Done — “{title}” is on your calendar ({occ_label}), starting {start_fmt}."
        else:
            msg = f"Done — “{title}” is on your calendar for {start_fmt}."
    else:
        lines = [f"Done — added {len(created)} events:"]
        for e in created:
            start_fmt = _format_suggestion_dt(e.get('startDate', ''))
            n = e.get('occurrences_created', 0)
            if n:
                freq = e.get('recurrence_type', '')
                freq_label = f"{freq} " if freq else ""
                lines.append(f"  • “{e.get('title', '')}” — {n} {freq_label}occurrence{'s' if n != 1 else ''} from {start_fmt}")
            else:
                lines.append(f"  • “{e.get('title', '')}” — {start_fmt}")
        msg = "\n".join(lines)

    return {
        "scheduling_result": {"message": msg, "events": created, "success": True},
        "scheduling_messages": [AIMessage(content=msg)],
        "is_success": True,
    }


async def _execute_update(event_data: dict, tools_map: dict, user_id: int = 0) -> dict:
    # Series update — bypass MCP and go directly to the adapter
    if event_data.get("series_update") and event_data.get("recurrence_id"):
        return await _execute_series_update(event_data, user_id)

    update_tool = tools_map['update_event']
    event_ids = event_data.get("event_ids", [])
    update_args = event_data.get("update_args", {})

    # Strip None values so update_event only receives fields to change
    clean_args = {k: v for k, v in update_args.items() if v is not None}

    updated = []
    for event_id in event_ids:
        args = {"event_id": event_id, **clean_args}
        result = _parse_mcp_result(await update_tool.ainvoke(args))
        if result.get('success') and result.get('event'):
            updated.append(result['event'])

    if not updated:
        msg = "Couldn’t update that event — it may have been removed, or you may not have access."
        return {
            "scheduling_result": {"message": msg, "success": False},
            "scheduling_messages": [AIMessage(content=msg)],
            "is_success": False,
        }

    if len(updated) == 1:
        ev = updated[0]
        start_fmt = _format_suggestion_dt(ev.get('startDate'))
        msg = f"Done — “{ev.get('title')}” is updated" + (f", now at {start_fmt}." if start_fmt else ".")
    else:
        titles = " and ".join(f"“{e.get('title')}”" for e in updated) if len(updated) == 2 else f"{len(updated)} events"
        msg = f"Done — {titles} updated."

    return {
        "scheduling_result": {"message": msg, "events": updated, "success": True},
        "scheduling_messages": [AIMessage(content=msg)],
        "is_success": True,
    }


async def _execute_series_update(event_data: dict, user_id: int) -> dict:
    """Update an entire recurring series (or future occurrences) directly via the adapter."""
    from database.config import get_async_db_context_manager
    from adapter.event_adapter import EventAdapter
    from models import EventUpdate

    recurrence_id = event_data["recurrence_id"]
    update_args = event_data.get("update_args", {})
    update_scope = event_data.get("update_scope", "all")
    time_shift_seconds = event_data.get("time_shift_seconds")
    series_from_date_str = event_data.get("series_from_date")

    from_date = None
    if update_scope == "future" and series_from_date_str:
        try:
            from_date = datetime.fromisoformat(series_from_date_str)
        except Exception:
            pass

    time_shift = timedelta(seconds=time_shift_seconds) if time_shift_seconds else None

    event_update = EventUpdate(
        title=update_args.get("title"),
        location=update_args.get("location"),
        description=update_args.get("description"),
        category=update_args.get("category"),
        duration=update_args.get("duration"),
        # startDate handled via time_shift, not direct assignment
    )

    try:
        async with get_async_db_context_manager() as db:
            adapter = EventAdapter(db)
            updated = await adapter.update_by_recurrence_id(
                recurrence_id, user_id, event_update,
                from_date=from_date,
                time_shift=time_shift,
            )
    except Exception as e:
        logger.error(f"Error updating series {recurrence_id}: {e}", exc_info=True)
        msg = "Something went wrong updating the series. Please try again."
        return {
            "scheduling_result": {"message": msg, "success": False},
            "scheduling_messages": [AIMessage(content=msg)],
            "is_success": False,
        }

    if not updated:
        msg = "Couldn’t find that series — it may have been removed already."
        return {
            "scheduling_result": {"message": msg, "success": False},
            "scheduling_messages": [AIMessage(content=msg)],
            "is_success": False,
        }

    title = updated[0].title if updated else ""
    n = len(updated)
    if update_scope == "future":
        msg = f"Done — updated {n} upcoming occurrence{'s' if n != 1 else ''} of “{title}”."
    else:
        msg = f"Done — all {n} occurrence{'s' if n != 1 else ''} of “{title}” are updated."
    return {
        "scheduling_result": {"message": msg, "success": True},
        "scheduling_messages": [AIMessage(content=msg)],
        "is_success": True,
    }


# ---------------------------------------------------------------------------
# Conditional edge
# ---------------------------------------------------------------------------

def scheduling_route(state: FlowState) -> str:
    """
    Route after scheduling_agent completes:
    - CREATE / UPDATE with a valid conflict_check_request → conflict_resolution_agent
    - UPDATE with no date change (startDate is None) → scheduling_finalize directly
    - Everything else (DELETE, LIST, clarification) → scheduling_finalize
    """
    operation = state.get('scheduling_operation')
    conflict_req = state.get('conflict_check_request') or {}
    if operation in ('create', 'update') and conflict_req.get('startDate'):
        return "conflict_resolution_agent"
    return "scheduling_finalize"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def _run_tool_loop(
    messages: list,
    model_with_tools,
    tools_map: dict,
    max_iter: int = 5,
) -> list:
    """Run an agentic tool-calling loop until the LLM stops requesting tools."""
    for _ in range(max_iter):
        response = await model_with_tools.ainvoke(messages)
        messages.append(response)
        if not (hasattr(response, 'tool_calls') and response.tool_calls):
            break
        for tc in response.tool_calls:
            result = await _run_single_tool(tc, tools_map)
            messages.append(ToolMessage(
                content=json.dumps(result, default=str),
                tool_call_id=tc['id'],
            ))
    return messages


def _parse_mcp_result(result) -> dict:
    """MCP tools (langchain-mcp-adapters 0.1.6) return results as JSON strings."""
    if isinstance(result, str):
        try:
            return json.loads(result)
        except json.JSONDecodeError:
            return {"error": result}
    return result


async def _run_single_tool(tool_call: dict, tools_map: dict) -> dict:
    tool_name = tool_call['name']
    tool_args = dict(tool_call.get('args', {}))
    # MCP tools accept ISO string dates — no conversion needed
    tool = tools_map.get(tool_name)
    if not tool:
        return {"error": f"Unknown tool: {tool_name}"}
    return _parse_mcp_result(await tool.ainvoke(tool_args))


def _extract_events_from_messages(messages: list) -> list:
    """Pull all events returned by list_event tool calls out of the message history.
    Deduplicates by event_id so multiple tool calls for overlapping ranges don't
    produce phantom duplicates."""
    seen_ids = set()
    events = []
    for msg in messages:
        if isinstance(msg, ToolMessage):
            try:
                data = json.loads(msg.content)
                if isinstance(data, dict) and 'events' in data:
                    for event in data['events']:
                        eid = event.get('event_id') or event.get('id')
                        if eid and eid in seen_ids:
                            continue
                        if eid:
                            seen_ids.add(eid)
                        events.append(event)
            except (json.JSONDecodeError, TypeError):
                pass
    return events


def _reconcile_event_ids(filtered: list, originals: list) -> list:
    """
    Replace any hallucinated IDs in the LLM-filtered list with the real IDs from originals.
    Matches by title (case-insensitive). When multiple originals share the same title,
    picks the one whose startDate is closest to the filtered event's startDate.
    """
    # Build lookup: normalised title → list of original events
    originals_by_title: dict[str, list] = {}
    for e in originals:
        title = (e.get('title') or '').strip().lower()
        if title:
            originals_by_title.setdefault(title, []).append(e)

    # Track which originals have already been matched to avoid double-assigning
    used_ids: set = set()

    def _best_match(fe: dict, candidates: list) -> dict:
        """Pick the closest unmatched candidate by startDate, else any unmatched one."""
        fe_start_str = fe.get('startDate') or ''
        try:
            fe_dt = datetime.fromisoformat(fe_start_str)
        except Exception:
            fe_dt = None

        best = None
        best_diff = None
        for c in candidates:
            cid = c.get('event_id') or c.get('id')
            if cid in used_ids:
                continue
            if fe_dt is not None:
                try:
                    c_dt = datetime.fromisoformat(c.get('startDate', ''))
                    diff = abs((fe_dt - c_dt).total_seconds())
                    if best_diff is None or diff < best_diff:
                        best = c
                        best_diff = diff
                except Exception:
                    pass
            if best is None:
                best = c  # fallback: first unmatched candidate
        return best or candidates[0]  # last resort

    reconciled = []
    for fe in filtered:
        title_key = (fe.get('title') or '').strip().lower()
        candidates = originals_by_title.get(title_key)
        if candidates:
            match = _best_match(fe, candidates)
            used_ids.add(match.get('event_id') or match.get('id'))
            reconciled.append(match)
        else:
            reconciled.append(fe)
    return reconciled


async def _filter_events(events: list, user_message: str, intent: str = "identify", context: str = "") -> list:
    """
    Use LLM to keyword-filter a list of events based on the user's message.
    Filters by title/location/duration keywords only (not date/time).
    Accepts optional conversation context to resolve pronouns like "it" or "that meeting".
    Returns all events if no keywords match.
    """
    if not events:
        return []

    prompt = PromptTemplate.from_template(SCHEDULING_FILTER_PROMPT).format(
        user_events=json.dumps(events, default=str, indent=2),
        user_message=user_message,
        intent=intent,
        context=context,
    )

    response = await model.ainvoke([HumanMessage(content=prompt)])

    try:
        content = response.content.strip()
        # Strip markdown code fences if present (LLMs often wrap JSON in ```json ... ```)
        if content.startswith("```"):
            content = content.split("```")[1]
            if content.startswith("json"):
                content = content[4:]
            content = content.strip()
        filtered = json.loads(content)
        if isinstance(filtered, list):
            logger.debug(f"_filter_events: {len(events)} input → {len(filtered)} after filter (intent={intent!r})")
            # Reconcile IDs: LLM may hallucinate IDs — replace with originals matched by title
            return _reconcile_event_ids(filtered, events)
    except (json.JSONDecodeError, TypeError) as exc:
        logger.warning(f"_filter_events: failed to parse LLM response ({exc}); raw={response.content[:200]!r}")

    # Fallback: return all events if parsing fails
    return events
