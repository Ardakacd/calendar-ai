from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy import select, delete, update
import logging
from database import EventModel
from models import EventCreate, EventUpdate, Event

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
        return Event(
            id=event_model.event_id,  # Use event_id (UUID) for API exposure
            title=event_model.title,
            datetime=event_model.datetime,  # Keep as datetime object for Pydantic validation
            duration=event_model.duration,
            location=event_model.location,
            user_id=event_model.user_id,
            created_at=event_model.created_at.isoformat() if event_model.created_at else None
        )
    
    def _convert_to_db_model(self, event_data: EventCreate) -> EventModel:
        """Convert EventCreate Pydantic model to EventModel."""
        return EventModel(
            title=event_data.title,
            datetime=event_data.datetime,
            duration=event_data.duration,
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
            stmt = select(EventModel).where(EventModel.user_id == user_id).order_by(EventModel.datetime.desc())
            
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
            stmt = select(EventModel).order_by(EventModel.datetime.desc())
            
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
                EventModel.datetime >= start_date,
                EventModel.datetime <= end_date
            ).order_by(EventModel.datetime.asc())
            
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
            True if updated successfully, False if failed or not found
        """
        try:
            # Build update data
            update_data = event_data.dict(exclude_unset=True)
            if not update_data:
                logger.warning(f"No fields to update for event {event_id}")
                return True  
            
            # Direct update operation with user ownership check
            stmt = update(EventModel).where(
                EventModel.event_id == event_id,
                EventModel.user_id == user_id
            ).values(**update_data).returning(EventModel)
            
            result = await self.db.execute(stmt)
            
            await self.db.commit()
            logger.info(f"Updated event: {event_id}")

            db_event = result.scalar_one_or_none()
            
            if db_event:
                return self._convert_to_model(db_event)
            return None
            
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
            True if deleted, False if failed or not found
        """
        try:
            stmt = delete(EventModel).where(
                EventModel.event_id == event_id,
                EventModel.user_id == user_id
            )
            result = await self.db.execute(stmt)
            
            if result.rowcount == 0:
                logger.warning(f"Event {event_id} not found for deletion or user {user_id} not authorized")
                return False
            
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
        Search events by title for a specific user.
        
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
                (EventModel.title.ilike(search_term))
            ).order_by(EventModel.datetime.desc())
            
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
        Get total number of events for a user.
        
        Args:
            user_id: User ID to count events for
            
        Returns:
            Number of events
        """
        try:
            from sqlalchemy import func
            stmt = select(func.count(EventModel.id)).where(EventModel.user_id == user_id)
            result = await self.db.execute(stmt)
            return result.scalar() or 0
            
        except SQLAlchemyError as e:
            logger.error(f"Database error counting events: {e}")
            return 0
        except Exception as e:
            logger.error(f"Unexpected error counting events: {e}")
            return 0
