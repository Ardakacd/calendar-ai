import logging
from typing import List, Optional, Dict, Any
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status, Query
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from models import EventCreate, EventUpdate, Event
from services.event_service import EventService, get_event_service

# Configure logging
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/events", tags=["events"])
security = HTTPBearer()


@router.post("", response_model=Event)
async def create_event(
        event_data: EventCreate,
        credentials: HTTPAuthorizationCredentials = Depends(security),
        event_service: EventService = Depends(get_event_service)
):
    """
    Create a new event for the authenticated user.
    
    Returns the created event details.
    """
    logger.info(f"Creating event with title: {event_data.title}")
    try:
        token = credentials.credentials
        
        result = await event_service.create_event(token, event_data)
        
        logger.info(f"Event created successfully: {result.id}")
        return result

    except HTTPException as e:
        logger.error(f"HTTP error during event creation: {e.detail}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error during event creation: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Bir hata oluştu. Lütfen daha sonra tekrar deneyiniz."
        )


@router.get("/{event_id}", response_model=Event)
async def get_event(
        event_id: str,
        credentials: HTTPAuthorizationCredentials = Depends(security),
        event_service: EventService = Depends(get_event_service)
):
    """
    Get a specific event by ID for the authenticated user.
    
    Returns the event details.
    """
    logger.info(f"Getting event: {event_id}")
    try:
        token = credentials.credentials
        result = await event_service.get_event(token, event_id)
        logger.info(f"Event retrieved successfully: {event_id}")
        return result

    except HTTPException as e:
        logger.error(f"HTTP error during event retrieval: {e.detail}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error during event retrieval: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Bir hata oluştu. Lütfen daha sonra tekrar deneyiniz."
        )


@router.get("", response_model=List[Event])
async def get_user_events(
        limit: Optional[int] = Query(None, ge=1, le=100, description="Maximum number of events to return"),
        offset: Optional[int] = Query(None, ge=0, description="Number of events to skip"),
        credentials: HTTPAuthorizationCredentials = Depends(security),
        event_service: EventService = Depends(get_event_service)
):
    """
    Get all events for the authenticated user with optional pagination.
    
    Returns a list of user's events.
    """
    logger.info(f"Getting user events with pagination: limit={limit}, offset={offset}")
    try:
        token = credentials.credentials
        result = await event_service.get_user_events(token, limit=limit, offset=offset)
        logger.info(f"Retrieved {len(result)} events for user")
        return result

    except HTTPException as e:
        logger.error(f"HTTP error during events retrieval: {e.detail}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error during events retrieval: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Bir hata oluştu. Lütfen daha sonra tekrar deneyiniz."
        )


@router.get("/range/", response_model=List[Event])
async def get_events_by_date_range(
        start_date: datetime = Query(..., description="Start date (YYYY-MM-DD HH:MM:SS)"),
        end_date: datetime = Query(..., description="End date (YYYY-MM-DD HH:MM:SS)"),
        credentials: HTTPAuthorizationCredentials = Depends(security),
        event_service: EventService = Depends(get_event_service)
):
    """
    Get events within a date range for the authenticated user.
    
    Returns a list of events in the specified date range.
    """
    logger.info(f"Getting events by date range: {start_date} to {end_date}")
    try:
        token = credentials.credentials
        result = await event_service.get_events_by_date_range(token, start_date, end_date)
        logger.info(f"Retrieved {len(result)} events in date range")
        return result

    except HTTPException as e:
        logger.error(f"HTTP error during date range events retrieval: {e.detail}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error during date range events retrieval: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Bir hata oluştu. Lütfen daha sonra tekrar deneyiniz."
        )


@router.patch("/{event_id}")
async def update_event(
        event_id: str,
        event_data: EventUpdate,
        credentials: HTTPAuthorizationCredentials = Depends(security),
        event_service: EventService = Depends(get_event_service)
):
    """
    Update an existing event for the authenticated user.
    
    Returns a success message.
    """
    logger.info(f"Updating event: {event_id}")
    try:
        token = credentials.credentials
        result = await event_service.update_event(token, event_id, event_data)
        logger.info(f"Event updated successfully: {event_id}")
        return result

    except HTTPException as e:
        logger.error(f"HTTP error during event update: {e.detail}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error during event update: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Bir hata oluştu. Lütfen daha sonra tekrar deneyiniz."
        )


@router.delete("/{event_id}", response_model=Dict[str, str])
async def delete_event(
        event_id: str,
        credentials: HTTPAuthorizationCredentials = Depends(security),
        event_service: EventService = Depends(get_event_service)
):
    """
    Delete an event for the authenticated user.
    
    Returns a success message.
    """
    logger.info(f"Deleting event: {event_id}")
    try:
        token = credentials.credentials
        result = await event_service.delete_event(token, event_id)
        logger.info(f"Event deleted successfully: {event_id}")
        return result

    except HTTPException as e:
        logger.error(f"HTTP error during event deletion: {e.detail}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error during event deletion: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Bir hata oluştu. Lütfen daha sonra tekrar deneyiniz."
        )


@router.delete("/bulk/", response_model=Dict[str, str])
async def delete_multiple_events(
        event_ids: List[str] = Query(..., description="List of event IDs to delete"),
        credentials: HTTPAuthorizationCredentials = Depends(security),
        event_service: EventService = Depends(get_event_service)
):
    """
    Delete multiple events for the authenticated user.
    
    Returns a success message if all events were deleted, or an error if any failed.
    """
    logger.info(f"Deleting multiple events: {len(event_ids)} events")
    try:
        token = credentials.credentials
        result = await event_service.delete_multiple_events(token, event_ids)
        logger.info(f"Bulk delete completed successfully")
        return result

    except HTTPException as e:
        logger.error(f"HTTP error during bulk event deletion: {e.detail}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error during bulk event deletion: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Bir hata oluştu. Lütfen daha sonra tekrar deneyiniz."
        )


@router.get("/search/", response_model=List[Event])
async def search_events(
        query: str = Query(..., min_length=1, description="Search query for title"),
        credentials: HTTPAuthorizationCredentials = Depends(security),
        event_service: EventService = Depends(get_event_service)
):
    """
    Search events by title for the authenticated user.
    
    Returns a list of matching events.
    """
    logger.info(f"Searching events with query: {query}")
    try:
        token = credentials.credentials
        result = await event_service.search_events(token, query)
        logger.info(f"Found {len(result)} events matching query '{query}'")
        return result

    except HTTPException as e:
        logger.error(f"HTTP error during event search: {e.detail}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error during event search: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Bir hata oluştu. Lütfen daha sonra tekrar deneyiniz."
        )


@router.get("/count/")
async def get_events_count(
        credentials: HTTPAuthorizationCredentials = Depends(security),
        event_service: EventService = Depends(get_event_service)
):
    """
    Get total number of events for the authenticated user.
    
    Returns the event count.
    """
    logger.info("Getting events count")
    try:
        token = credentials.credentials
        result = await event_service.get_events_count(token)
        logger.info(f"Events count retrieved: {result['count']}")
        return result

    except HTTPException as e:
        logger.error(f"HTTP error during events count retrieval: {e.detail}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error during events count retrieval: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Bir hata oluştu. Lütfen daha sonra tekrar deneyiniz."
        )
