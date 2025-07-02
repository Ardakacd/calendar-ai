from fastapi import Depends, HTTPException, status
from models import EventBase, EventUpdate, Event, EventCreate
from adapter.event import EventAdapter
from utils.jwt import get_user_id_from_token
from typing import List, Optional
import logging
from database.config import get_async_db
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

class EventService:
    def __init__(self, event_adapter: EventAdapter):
        self.event_adapter = event_adapter

    async def create_event(self, token: str, event_data: EventBase) -> Event:
        """
        Create a new event for the authenticated user.
        
        Args:
            token: JWT token for authentication
            event_data: Event data to create
            
        Returns:
            Created event
        """
        logger.info(f"EventService: Creating event with title: {event_data.title}")
        try:
            user_id = get_user_id_from_token(token)
            
            event = EventCreate(
                user_id=user_id,
                title=event_data.title,
                datetime=event_data.datetime,
                duration=event_data.duration,
                location=event_data.location,
            )

            result = await self.event_adapter.create_event(event)
            if not result:
                logger.error(f"EventService: Failed to create event: {event_data.title}")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Failed to create event"
                )
            
            logger.info(f"EventService: Event created successfully: {result.id}")
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
        Get a specific event by ID for the authenticated user.
        
        Args:
            token: JWT token for authentication
            event_id: Event ID to retrieve
            
        Returns:
            Event details
        """
        logger.info(f"EventService: Getting event: {event_id}")
        try:
            user_id = get_user_id_from_token(token)
            
            result = await self.event_adapter.get_event_by_event_id(event_id)
            if not result:
                logger.warning(f"EventService: Event not found: {event_id}")
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Event not found"
                )
            
            # Verify the event belongs to the user
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

    async def get_user_events(self, token: str, limit: Optional[int] = None, offset: Optional[int] = None) -> List[Event]:
        """
        Get all events for the authenticated user.
        
        Args:
            token: JWT token for authentication
            limit: Maximum number of events to return
            offset: Number of events to skip
            
        Returns:
            List of user's events
        """
        logger.info(f"EventService: Getting events for user with pagination: limit={limit}, offset={offset}")
        try:
            user_id = get_user_id_from_token(token)
            
            result = await self.event_adapter.get_events_by_user_id(user_id, limit=limit, offset=offset)
            
            logger.info(f"EventService: Retrieved {len(result)} events for user {user_id}")
            return result
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"EventService: Unexpected error getting user events: {str(e)}", exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Internal server error"
            )

    async def get_events_by_date_range(self, token: str, start_date: str, end_date: str) -> List[Event]:
        """
        Get events within a date range for the authenticated user.
        
        Args:
            token: JWT token for authentication
            start_date: Start date (YYYY-MM-DD HH:MM:SS)
            end_date: End date (YYYY-MM-DD HH:MM:SS)
            
        Returns:
            List of events in date range
        """
        logger.info(f"EventService: Getting events by date range: {start_date} to {end_date}")
        try:
            user_id = get_user_id_from_token(token)
            
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

    async def update_event(self, token: str, event_id: str, event_data: EventUpdate) -> dict:
        """
        Update an existing event for the authenticated user.
        
        Args:
            token: JWT token for authentication
            event_id: Event ID to update
            event_data: Updated event data
            
        Returns:
            Success message
        """
        logger.info(f"EventService: Updating event: {event_id}")
        try:
            user_id = get_user_id_from_token(token)
            
            result = await self.event_adapter.update_event(event_id, user_id, event_data)
            if not result:
                logger.warning(f"EventService: Event not found or not authorized for update: {event_id}")
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Event not found or not authorized"
                )
            
            logger.info(f"EventService: Event updated successfully: {event_id}")
            print('look at here')
            print(result)
            return result
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"EventService: Unexpected error updating event {event_id}: {str(e)}", exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Internal server error"
            )

    async def delete_event(self, token: str, event_id: str) -> dict:
        """
        Delete an event for the authenticated user.
        
        Args:
            token: JWT token for authentication
            event_id: Event ID to delete
            
        Returns:
            Success message
        """
        logger.info(f"EventService: Deleting event: {event_id}")
        try:
            user_id = get_user_id_from_token(token)
            
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
            token: JWT token for authentication
            query: Search query
            
        Returns:
            List of matching events
        """
        logger.info(f"EventService: Searching events with query: {query}")
        try:
            user_id = get_user_id_from_token(token)
            
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

    async def get_events_count(self, token: str) -> dict:
        """
        Get total number of events for the authenticated user.
        
        Args:
            token: JWT token for authentication
            
        Returns:
            Event count
        """
        logger.info("EventService: Getting events count")
        try:
            user_id = get_user_id_from_token(token)
            
            count = await self.event_adapter.get_events_count(user_id)
            
            logger.info(f"EventService: User {user_id} has {count} events")
            return {"count": count}
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"EventService: Unexpected error getting events count: {str(e)}", exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Internal server error"
            )
        
def get_event_service(
    db: AsyncSession = Depends(get_async_db),
) -> EventService:
    event_adapter = EventAdapter(db)
    return EventService(event_adapter)
