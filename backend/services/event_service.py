import logging
from typing import List, Optional, Dict, Any

from adapter.event_adapter import EventAdapter
from database.config import get_async_db
from fastapi import Depends, HTTPException, status
from models import EventUpdate, Event, EventCreate
from sqlalchemy.ext.asyncio import AsyncSession
from utils.jwt import get_user_id_from_token

logger = logging.getLogger(__name__)


class EventService:
    def __init__(self, event_adapter: EventAdapter):
        self.event_adapter = event_adapter

    async def create_event(self, token: str, event_data: EventCreate) -> Event:
        """
        Create a new event for the authenticated user.
        
        Args:
            token: JWT token for user authentication
            event_data: Event data to create
            
        Returns:
            Created event
            
        Raises:
            HTTPException: If user not authenticated or creation fails
        """
        try:
            # Extract user_id from token
            user_id = get_user_id_from_token(token)

            logger.info(f"EventService: Creating event for user {user_id}")
            result = await self.event_adapter.create_event(user_id, event_data)

            if not result:
                logger.error(f"EventService: Failed to create event for user {user_id}")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Failed to create event"
                )

            logger.info(f"EventService: Event created successfully for user {user_id}")
            return result

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"EventService: Unexpected error creating event: {str(e)}", exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Internal server error"
            )

    async def get_event(self, token: str, event_id: str) -> Event:
        """
        Get a specific event by ID.
        
        Args:
            token: JWT token for user authentication
            event_id: Event ID to retrieve
            
        Returns:
            Event data
            
        Raises:
            HTTPException: If user not authenticated, event not found, or not authorized
        """
        try:
            # Extract user_id from token
            user_id = get_user_id_from_token(token)

            logger.info(f"EventService: Getting event: {event_id}")

            # Get event by event_id
            result = await self.event_adapter.get_event_by_event_id(event_id)

            if not result:
                logger.warning(f"EventService: Event not found: {event_id}")
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Event not found"
                )

            # Check if user owns the event
            if result.user_id != user_id:
                logger.warning(f"EventService: User {user_id} not authorized to access event {event_id}")
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Not authorized to access this event"
                )

            logger.info(f"EventService: Event retrieved successfully: {event_id}")
            return result

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"EventService: Unexpected error getting event {event_id}: {str(e)}", exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Internal server error"
            )

    async def get_user_events(self, token: str, limit: Optional[int] = None, offset: Optional[int] = None) -> List[
        Event]:
        """
        Get all events for the authenticated user.
        
        Args:
            token: JWT token for user authentication
            limit: Maximum number of events to return
            offset: Number of events to skip
            
        Returns:
            List of events
            
        Raises:
            HTTPException: If user not authenticated
        """
        try:
            # Extract user_id from token
            user_id = get_user_id_from_token(token)
           
            logger.info(f"EventService: Getting events for user {user_id}")

            result = await self.event_adapter.get_events_by_user_id(user_id, limit=limit, offset=offset)

            logger.info(f"EventService: Retrieved {len(result)} events for user {user_id}")
            return result

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"EventService: Unexpected error getting events: {str(e)}", exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Internal server error"
            )

    async def get_events_by_date_range(self, token: str, start_date: str, end_date: str) -> List[Event]:
        """
        Get events within a date range for the authenticated user.
        
        Args:
            token: JWT token for user authentication
            start_date: Start date (YYYY-MM-DD HH:MM:SS)
            end_date: End date (YYYY-MM-DD HH:MM:SS)
            
        Returns:
            List of events in date range
            
        Raises:
            HTTPException: If user not authenticated
        """
        try:
            # Extract user_id from token
            user_id = get_user_id_from_token(token)
           
            logger.info(f"EventService: Getting events in date range for user {user_id}")

            result = await self.event_adapter.get_events_by_date_range(user_id, start_date, end_date)

            logger.info(f"EventService: Retrieved {len(result)} events in date range for user {user_id}")
            return result

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"EventService: Unexpected error getting events by date range: {str(e)}", exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Internal server error"
            )

    async def update_event(self, token: str, event_id: str, event_data: EventUpdate) -> Dict[str, Any]:
        """
        Update an existing event.
        
        Args:
            token: JWT token for user authentication
            event_id: Event ID to update
            event_data: Updated event data
            
        Returns:
            Success message
            
        Raises:
            HTTPException: If user not authenticated, event not found, or not authorized
        """
        try:
            # Extract user_id from token
            user_id = get_user_id_from_token(token)

            logger.info(f"EventService: Updating event: {event_id}")

            result = await self.event_adapter.update_event(event_id, user_id, event_data)

            if not result:
                logger.warning(f"EventService: Event not found or not authorized for update: {event_id}")
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Event not found or not authorized"
                )

            logger.info(f"EventService: Event updated successfully: {event_id}")
            return result

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"EventService: Unexpected error updating event {event_id}: {str(e)}", exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Internal server error"
            )

    async def delete_event(self, token: str, event_id: str) -> Dict[str, Any]:
        """
        Delete an event.
        
        Args:
            token: JWT token for user authentication
            event_id: Event ID to delete
            
        Returns:
            Success message
            
        Raises:
            HTTPException: If user not authenticated, event not found, or not authorized
        """
        try:
            # Extract user_id from token
            user_id = get_user_id_from_token(token)

            logger.info(f"EventService: Deleting event: {event_id}")

            result = await self.event_adapter.delete_event(event_id, user_id)

            if not result:
                logger.warning(f"EventService: Event not found or not authorized for deletion: {event_id}")
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Event not found or not authorized"
                )

            logger.info(f"EventService: Event deleted successfully: {event_id}")
            return {"message": "Event deleted successfully"}

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"EventService: Unexpected error deleting event {event_id}: {str(e)}", exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Internal server error"
            )

    async def search_events(self, token: str, query: str) -> List[Event]:
        """
        Search events by title for the authenticated user.
        
        Args:
            token: JWT token for user authentication
            query: Search query
            
        Returns:
            List of matching events
            
        Raises:
            HTTPException: If user not authenticated
        """
        try:
            # Extract user_id from token
            user_id = get_user_id_from_token(token)

            logger.info(f"EventService: Searching events for user {user_id}")

            result = await self.event_adapter.search_events(user_id, query)

            logger.info(f"EventService: Found {len(result)} events matching query '{query}' for user {user_id}")
            return result

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"EventService: Unexpected error searching events: {str(e)}", exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Internal server error"
            )

    async def get_events_count(self, token: str) -> Dict[str, Any]:
        """
        Get total number of events for the authenticated user.
        
        Args:
            token: JWT token for user authentication
            
        Returns:
            Event count
            
        Raises:
            HTTPException: If user not authenticated
        """
        try:
            # Extract user_id from token
            user_id = get_user_id_from_token(token)

            logger.info(f"EventService: Getting event count for user {user_id}")

            count = await self.event_adapter.get_events_count(user_id)

            logger.info(f"EventService: User {user_id} has {count} events")
            return {"count": count}

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"EventService: Unexpected error getting event count: {str(e)}", exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Internal server error"
            )


def get_event_service(
        db: AsyncSession = Depends(get_async_db),
) -> EventService:
    event_adapter = EventAdapter(db)
    return EventService(event_adapter)
