"""
Create Event Tool for LangChain agents.

This tool allows LLM agents to create calendar events with proper validation
and database persistence.
"""

import logging
from typing import Optional
from datetime import datetime
from langchain_core.tools import StructuredTool
from pydantic import BaseModel, Field
from adapter.event_adapter import EventAdapter
from database import get_async_db_context_manager
from exceptions import RecurringConflictError
from models import EventCreate

logger = logging.getLogger(__name__)


class CreateEventInput(BaseModel):
    """Input schema for the create_event tool."""

    title: str = Field(..., description="The title of the event")
    startDate: datetime = Field(..., description="When the event starts (ISO 8601 format: YYYY-MM-DDTHH:MM:SS±HH:MM)")
    endDate: Optional[datetime] = Field(
        None,
        description="When the event ends. If not provided, defaults to startDate"
    )
    location: Optional[str] = Field(
        None,
        description="Location of the event. If not provided, defaults to null"
    )
    description: Optional[str] = Field(
        None,
        description="Additional notes or description for the event."
    )
    category: Optional[str] = Field(
        None,
        description="Event category. Must be one of: 'work', 'personal', 'health', 'social'. Auto-infer from context if not stated — e.g. 'doctor appointment' → 'health', 'team meeting' → 'work', 'birthday party' → 'social', 'workout' → 'health'."
    )
    recurrence_type: Optional[str] = Field(
        None,
        description="Recurrence frequency: 'daily', 'weekly', 'monthly', or 'yearly'. Only set when the user explicitly asks for a recurring event."
    )
    recurrence_count: Optional[int] = Field(
        None,
        description="Number of occurrences to create when recurrence_type is set. Required if recurrence_type is provided. Maximum 365."
    )
    recurrence_interval: Optional[int] = Field(
        None,
        description="Repeat every N periods. Default 1. Set to 2 for bi-weekly, 3 for every 3 months, etc."
    )
    recurrence_byweekday: Optional[str] = Field(
        None,
        description="Comma-separated weekday codes to constrain recurrence: MO,TU,WE,TH,FR,SA,SU. E.g. 'MO,WE,FR' for Mon/Wed/Fri; 'MO,TU,WE,TH,FR' for every weekday."
    )
    recurrence_bysetpos: Optional[int] = Field(
        None,
        description="Position within the period for monthly recurrence. 1=first, 2=second, -1=last. E.g. freq=monthly, byweekday=MO, bysetpos=1 means 'first Monday of each month'."
    )

    class Config:
        json_schema_extra = {
            "example": {
                "title": "Weekly team standup",
                "startDate": "2025-03-20T09:00:00-05:00",
                "endDate": "2025-03-20T09:30:00-05:00",
                "location": "Zoom",
                "recurrence_type": "weekly",
                "recurrence_count": 12
            }
        }


async def create_event_impl(
    title: str,
    startDate: datetime,
    endDate: Optional[datetime] = None,
    location: Optional[str] = None,
    description: Optional[str] = None,
    category: Optional[str] = None,
    recurrence_type: Optional[str] = None,
    recurrence_count: Optional[int] = None,
    recurrence_interval: Optional[int] = None,
    recurrence_byweekday: Optional[str] = None,
    recurrence_bysetpos: Optional[int] = None,
    user_id: Optional[int] = None
) -> dict:
    """
    Create a calendar event (single or recurring).

    Returns:
        Dictionary with event details. For recurring events, includes a `recurrence_id`
        and `occurrences_created` count.
    """
    if user_id is None:
        raise ValueError("user_id is required but was not provided")

    if endDate is None:
        endDate = startDate

    duration_minutes = None
    if endDate != startDate:
        delta = endDate - startDate
        duration_minutes = int(delta.total_seconds() / 60)

    event_data = EventCreate(
        title=title,
        category=category,
        description=description,
        startDate=startDate,
        duration=duration_minutes,
        location=location,
    )

    try:
        async with get_async_db_context_manager() as db:
            adapter = EventAdapter(db)

            if recurrence_type and recurrence_count and recurrence_count >= 1:
                logger.info(f"Creating {recurrence_count} {recurrence_type} recurring events '{title}' for user {user_id}")
                events = await adapter.create_recurring_events(
                    user_id, event_data, recurrence_type, recurrence_count,
                    interval=recurrence_interval or 1,
                    byweekday=recurrence_byweekday,
                    bysetpos=recurrence_bysetpos,
                )
                first = events[0]
                return {
                    "event_id": first.id,
                    "title": first.title,
                    "startDate": first.startDate.isoformat(),
                    "endDate": first.endDate.isoformat(),
                    "location": first.location,
                    "user_id": first.user_id,
                    "recurrence_id": first.recurrence_id,
                    "recurrence_type": recurrence_type,
                    "occurrences_created": len(events),
                    "success": True,
                }

            logger.info(f"Creating event '{title}' for user {user_id}")
            created_event = await adapter.create_event(user_id, event_data)
            logger.info(f"Successfully created event {created_event.id} for user {user_id}")

            return {
                "event_id": created_event.id,
                "title": created_event.title,
                "startDate": created_event.startDate.isoformat(),
                "endDate": created_event.endDate.isoformat(),
                "location": created_event.location,
                "user_id": created_event.user_id,
                "success": True,
            }
    except RecurringConflictError as e:
        return {
            "success": False,
            "has_recurring_conflict": True,
            "conflicts": e.conflicts,
        }
    except Exception as e:
        logger.error(f"Error creating event: {e}", exc_info=True)
        raise Exception(f"Failed to create event: {str(e)}")


def create_event_tool_factory(user_id: int) -> StructuredTool:
    """
    Factory function to create a create_event tool bound to a specific user_id.
    
    Args:
        user_id: The user ID to inject into the tool
    
    Returns:
        A StructuredTool instance configured for the user
    """
    async def create_event_with_user_id(
        title: str,
        startDate: datetime,
        endDate: Optional[datetime] = None,
        location: Optional[str] = None,
        description: Optional[str] = None,
        category: Optional[str] = None,
        recurrence_type: Optional[str] = None,
        recurrence_count: Optional[int] = None,
        recurrence_interval: Optional[int] = None,
        recurrence_byweekday: Optional[str] = None,
        recurrence_bysetpos: Optional[int] = None,
    ) -> dict:
        """Create event with user_id injected."""
        return await create_event_impl(
            title=title,
            startDate=startDate,
            endDate=endDate,
            location=location,
            description=description,
            category=category,
            recurrence_type=recurrence_type,
            recurrence_count=recurrence_count,
            recurrence_interval=recurrence_interval,
            recurrence_byweekday=recurrence_byweekday,
            recurrence_bysetpos=recurrence_bysetpos,
            user_id=user_id,
        )

    return StructuredTool.from_function(
        func=create_event_with_user_id,
        name="create_event",
        description="""Create a new calendar event (single or recurring).

        Use this tool when the user wants to schedule or create a new event.
        The event_id will be automatically generated as a UUID.
        If endDate is not provided, it will default to startDate.
        If location is not provided, it will be null.

        For recurring events, set recurrence_type ('daily', 'weekly', 'monthly', 'yearly')
        and recurrence_count (number of occurrences, e.g. 4 for monthly means 4 months).
        All occurrences share a recurrence_id so they can be managed as a series.
        """,
        args_schema=CreateEventInput,
    )


# Note: Use create_event_tool_factory(user_id) to create a tool instance bound to a user_id.
# The factory pattern ensures user_id is properly injected and not exposed to the LLM.
