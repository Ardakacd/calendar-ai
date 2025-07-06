from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy import select, delete, update, func
import logging
from database import EventModel
from models import EventCreate, EventUpdate, Event
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class EventAdapter:
    """
    Event adapter for database operations.
    
    This adapter provides async interface for event CRUD operations
    with proper error handling and session management.
    """
    
    def __init__(self, session: AsyncSession):
        self.db: AsyncSession = session
    
    def _convert_to_model(self, event_model: EventModel) -> Event:
        """Convert EventModel to Event Pydantic model."""
        # Calculate duration from startDate and endDate
        duration = None
        if event_model.startDate and event_model.endDate:
            delta = event_model.endDate - event_model.startDate
            duration = int(delta.total_seconds() / 60)
        
        return Event(
            id=event_model.event_id,  # Use event_id (UUID) for API exposure
            title=event_model.title,
            startDate=event_model.startDate,
            endDate=event_model.endDate,
            duration=duration,  # Set the computed duration
            location=event_model.location,
            user_id=event_model.user_id,
            created_at=event_model.created_at.isoformat() if event_model.created_at else ""
        )
    
    def _convert_to_db_model(self, event_data: EventCreate) -> EventModel:
        """Convert EventCreate Pydantic model to EventModel."""
        # Calculate endDate from startDate + duration if duration is provided
        end_date = None
        if event_data.duration and event_data.duration > 0:
            end_date = event_data.startDate + timedelta(minutes=event_data.duration)
        elif event_data.endDate:
            end_date = event_data.endDate
            
        return EventModel(
            title=event_data.title,
            startDate=event_data.startDate,
            endDate=end_date,
            location=event_data.location,
            user_id=event_data.user_id
        )
    
    async def create_event(self, event_data: EventCreate) -> Optional[Event]:
        """
        Create a new event.
        
        Args:
            event_data: Event data to create
            
        Returns:
            Created event or None if failed
        """
        try:
            db_event = self._convert_to_db_model(event_data)
            self.db.add(db_event)
            await self.db.commit()
            
            logger.info(f"Created event: {db_event.event_id}")
            return self._convert_to_model(db_event)
            
        except SQLAlchemyError as e:
            logger.error(f"Database error creating event: {e}")
            await self.db.rollback()
            return None
        except Exception as e:
            logger.error(f"Unexpected error creating event: {e}")
            await self.db.rollback()
            return None
    
    async def get_event_by_event_id(self, event_id: str) -> Optional[Event]:
        """
        Get event by event_id (UUID).
        
        Args:
            event_id: Event ID (UUID) to retrieve
            
        Returns:
            Event or None if not found
        """
        try:
            stmt = select(EventModel).where(EventModel.event_id == event_id)
            result = await self.db.execute(stmt)
            db_event = result.scalar_one_or_none()
            
            if db_event:
                return self._convert_to_model(db_event)
            return None
            
        except SQLAlchemyError as e:
            logger.error(f"Database error retrieving event {event_id}: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error retrieving event {event_id}: {e}")
            return None
         
    async def get_events_by_user_id(self, user_id: int, limit: Optional[int] = None, offset: Optional[int] = None) -> List[Event]:
        """
        Get all events for a specific user with optional pagination.
        
        Args:
            user_id: User ID to filter events
            limit: Maximum number of events to return
            offset: Number of events to skip
            
        Returns:
            List of events
        """
        try:
            stmt = select(EventModel).where(EventModel.user_id == user_id).order_by(EventModel.startDate.desc())
            
            if offset:
                stmt = stmt.offset(offset)
            if limit:
                stmt = stmt.limit(limit)
            
            result = await self.db.execute(stmt)
            db_events = result.scalars().all()
            
            return [self._convert_to_model(event) for event in db_events]
            
        except SQLAlchemyError as e:
            logger.error(f"Database error retrieving events for user {user_id}: {e}")
            return []
        except Exception as e:
            logger.error(f"Unexpected error retrieving events for user {user_id}: {e}")
            return []
    
    async def get_all_events(self, limit: Optional[int] = None, offset: Optional[int] = None) -> List[Event]:
        """
        Get all events with optional pagination.
        
        Args:
            limit: Maximum number of events to return
            offset: Number of events to skip
            
        Returns:
            List of events
        """
        try:
            stmt = select(EventModel).order_by(EventModel.startDate.desc())
            
            if offset:
                stmt = stmt.offset(offset)
            if limit:
                stmt = stmt.limit(limit)
            
            result = await self.db.execute(stmt)
            db_events = result.scalars().all()
            
            return [self._convert_to_model(event) for event in db_events]
            
        except SQLAlchemyError as e:
            logger.error(f"Database error retrieving events: {e}")
            return []
        except Exception as e:
            logger.error(f"Unexpected error retrieving events: {e}")
            return []
    
    async def get_events_by_date_range(self, user_id: int, start_date: str, end_date: str) -> List[Event]:
        """
        Get events within a date range for a specific user.
        
        Args:
            user_id: User ID to filter events
            start_date: Start date (YYYY-MM-DD HH:MM:SS)
            end_date: End date (YYYY-MM-DD HH:MM:SS)
            
        Returns:
            List of events in date range
        """
        try:
            stmt = select(EventModel).where(
                EventModel.user_id == user_id,
                EventModel.startDate >= start_date,
                EventModel.startDate <= end_date
            ).order_by(EventModel.startDate.asc())
            
            result = await self.db.execute(stmt)
            db_events = result.scalars().all()
            
            return [self._convert_to_model(event) for event in db_events]
            
        except SQLAlchemyError as e:
            logger.error(f"Database error retrieving events by date range: {e}")
            return []
        except Exception as e:
            logger.error(f"Unexpected error retrieving events by date range: {e}")
            return []
    
    async def update_event(self, event_id: str, user_id: int, event_data: EventUpdate) -> Optional[Event]:
        """
        Update an existing event.
        
        Args:
            event_id: Event ID (UUID) to update
            user_id: User ID to verify ownership
            event_data: Updated event data
            
        Returns:
            Updated event or None if failed
        """
        try:
            # First, get the existing event to verify ownership
            stmt = select(EventModel).where(EventModel.event_id == event_id)
            result = await self.db.execute(stmt)
            db_event = result.scalar_one_or_none()
            
            if not db_event:
                logger.warning(f"Event not found for update: {event_id}")
                return None
            
            if db_event.user_id != user_id:
                logger.warning(f"User {user_id} not authorized to update event {event_id}")
                return None
            
            # Update fields
            update_data = {}
            logger.info(f"Processing update fields for event {event_id}")
            logger.info(f"Title: {event_data.title}, StartDate: {event_data.startDate}, Location: {event_data.location}")
            
            if event_data.title is not None:
                update_data['title'] = event_data.title
            if event_data.startDate is not None:
                update_data['startDate'] = event_data.startDate
            if event_data.location is not None:
                update_data['location'] = event_data.location
            
            # Handle endDate and duration logic
            logger.info(f"Update event {event_id}: duration={event_data.duration}, startDate={event_data.startDate}, endDate={event_data.endDate}")
            
            if event_data.duration is not None:
                if event_data.duration > 0:
                    # If duration is provided and > 0, calculate endDate from startDate + duration
                    # Use the new startDate if provided, otherwise use the existing one
                    start_date = event_data.startDate if event_data.startDate is not None else db_event.startDate
                    logger.info(f"Calculating endDate: start_date={start_date}, duration={event_data.duration}")
                    update_data['endDate'] = start_date + timedelta(minutes=event_data.duration)
                    logger.info(f"Calculated endDate: {update_data['endDate']}")
                elif event_data.duration == 0:
                    # If duration is explicitly set to 0, clear endDate
                    update_data['endDate'] = None
            elif event_data.endDate is not None:
                # If endDate is provided directly, use it
                update_data['endDate'] = event_data.endDate
            
            if update_data:
                stmt = update(EventModel).where(EventModel.event_id == event_id).values(**update_data)
                await self.db.execute(stmt)
                await self.db.commit()
                
                # Get updated event
                result = await self.db.execute(select(EventModel).where(EventModel.event_id == event_id))
                updated_event = result.scalar_one_or_none()
                
                if updated_event:
                    logger.info(f"Updated event: {event_id}")
                    return self._convert_to_model(updated_event)
            
            return self._convert_to_model(db_event)
            
        except SQLAlchemyError as e:
            logger.error(f"Database error updating event {event_id}: {e}")
            await self.db.rollback()
            return None
        except Exception as e:
            logger.error(f"Unexpected error updating event {event_id}: {e}")
            await self.db.rollback()
            return None
    
    async def delete_event(self, event_id: str, user_id: int) -> bool:
        """
        Delete an event.
        
        Args:
            event_id: Event ID (UUID) to delete
            user_id: User ID to verify ownership
            
        Returns:
            True if deleted, False otherwise
        """
        try:
            # First, verify ownership
            stmt = select(EventModel).where(EventModel.event_id == event_id)
            result = await self.db.execute(stmt)
            db_event = result.scalar_one_or_none()
            
            if not db_event:
                logger.warning(f"Event not found for deletion: {event_id}")
                return False
            
            if db_event.user_id != user_id:
                logger.warning(f"User {user_id} not authorized to delete event {event_id}")
                return False
            
            # Delete the event
            stmt = delete(EventModel).where(EventModel.event_id == event_id)
            await self.db.execute(stmt)
            await self.db.commit()
            
            logger.info(f"Deleted event: {event_id}")
            return True
            
        except SQLAlchemyError as e:
            logger.error(f"Database error deleting event {event_id}: {e}")
            await self.db.rollback()
            return False
        except Exception as e:
            logger.error(f"Unexpected error deleting event {event_id}: {e}")
            await self.db.rollback()
            return False
    
    async def search_events(self, user_id: int, query: str) -> List[Event]:
        """
        Search events by title or location for a specific user.
        
        Args:
            user_id: User ID to filter events
            query: Search query
            
        Returns:
            List of matching events
        """
        try:
            search_term = f"%{query}%"
            stmt = select(EventModel).where(
                EventModel.user_id == user_id,
                (EventModel.title.ilike(search_term) | EventModel.location.ilike(search_term))
            ).order_by(EventModel.startDate.desc())
            
            result = await self.db.execute(stmt)
            db_events = result.scalars().all()
            
            return [self._convert_to_model(event) for event in db_events]
            
        except SQLAlchemyError as e:
            logger.error(f"Database error searching events: {e}")
            return []
        except Exception as e:
            logger.error(f"Unexpected error searching events: {e}")
            return []
    
    async def get_events_count(self, user_id: int) -> int:
        """
        Get the count of events for a specific user.
        
        Args:
            user_id: User ID to filter events
            
        Returns:
            Number of events
        """
        try:
            stmt = select(func.count(EventModel.id)).where(EventModel.user_id == user_id)
            result = await self.db.execute(stmt)
            count = result.scalar()
            
            return count or 0
            
        except SQLAlchemyError as e:
            logger.error(f"Database error counting events: {e}")
            return 0
        except Exception as e:
            logger.error(f"Unexpected error counting events: {e}")
            return 0
