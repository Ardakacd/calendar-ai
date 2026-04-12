from typing import List, Optional, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy import select, delete, update, func, or_, and_
import logging
import uuid
from database import EventModel
from database.models.user import UserModel
from models import EventCreate, EventUpdate, Event
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
from dateutil.rrule import rrule, rrulestr, DAILY, WEEKLY, MONTHLY, YEARLY, MO, TU, WE, TH, FR, SA, SU
from exceptions import EventNotFoundError, EventPermissionError, DatabaseError, RecurringConflictError
from fastapi import HTTPException, status

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
        
        
        delta = event_model.endDate - event_model.startDate
        duration = int(delta.total_seconds() / 60)

        
        return Event(
            id=event_model.event_id,
            title=event_model.title,
            category=event_model.category,
            description=event_model.description,
            startDate=event_model.startDate,
            endDate=event_model.endDate,
            duration=duration,
            location=event_model.location,
            user_id=event_model.user_id,
            recurrence_id=event_model.recurrence_id,
            recurrence_type=event_model.recurrence_type,
            rrule_string=event_model.rrule_string,
        )
    
    def _convert_to_db_model(
        self,
        user_id: int,
        event_data: EventCreate,
        recurrence_id: Optional[str] = None,
        recurrence_type: Optional[str] = None,
        rrule_string: Optional[str] = None,
    ) -> EventModel:
        """Convert EventCreate Pydantic model to EventModel."""

        end_date = None
        if event_data.duration and event_data.duration > 0:
            end_date = event_data.startDate + timedelta(minutes=event_data.duration)
        else:
            end_date = event_data.startDate

        return EventModel(
            title=event_data.title,
            category=event_data.category,
            description=event_data.description,
            startDate=event_data.startDate,
            endDate=end_date,
            location=event_data.location,
            user_id=user_id,
            recurrence_id=recurrence_id,
            recurrence_type=recurrence_type,
            rrule_string=rrule_string,
        )

    _FREQ_MAP = {"daily": DAILY, "weekly": WEEKLY, "monthly": MONTHLY, "yearly": YEARLY}
    _WEEKDAY_MAP = {"MO": MO, "TU": TU, "WE": WE, "TH": TH, "FR": FR, "SA": SA, "SU": SU}

    def _build_rrule(
        self,
        start: datetime,
        recurrence_type: str,
        count: int,
        interval: int = 1,
        byweekday: Optional[str] = None,
        bysetpos: Optional[int] = None,
    ) -> tuple[List[datetime], str]:
        """
        Build an rrule from recurrence parameters.
        Returns (list_of_datetimes, rrule_string).
        """
        freq = self._FREQ_MAP.get(recurrence_type.lower() if recurrence_type else "")
        if freq is None:
            valid = ", ".join(self._FREQ_MAP.keys())
            raise ValueError(f"Unknown recurrence_type '{recurrence_type}'. Must be one of: {valid}")

        kwargs: dict = {
            "freq": freq,
            "count": count,
            "dtstart": start,
            "interval": interval,
        }
        if byweekday:
            tokens = [d.strip().upper() for d in byweekday.split(",")]
            invalid = [t for t in tokens if t not in self._WEEKDAY_MAP]
            if invalid:
                raise ValueError(f"Unknown weekday token(s): {', '.join(invalid)}. Must be MO,TU,WE,TH,FR,SA,SU")
            days = [self._WEEKDAY_MAP[t] for t in tokens]
            kwargs["byweekday"] = days
        if bysetpos is not None:
            kwargs["bysetpos"] = bysetpos

        rule = rrule(**kwargs)
        dates = list(rule)
        # Strip DTSTART line — we store it separately as the event's startDate
        rule_str = "\n".join(
            line for line in str(rule).splitlines() if not line.startswith("DTSTART")
        )
        return dates, rule_str
    
    def _ensure_datetime(self, value: Optional[datetime | str]) -> Optional[datetime]:
        if isinstance(value, str):
            return datetime.fromisoformat(value)
        return value
    
    async def create_event(self, user_id: int, event_data: EventCreate) -> Event:
        """
        Create a new event.
        
        Args:
            event_data: Event data to create
            
        Returns:
            Created event
            
        Raises:
            DatabaseError: If there's a database error
        """
        try:
            db_event = self._convert_to_db_model(user_id, event_data)
            self.db.add(db_event)
            await self.db.commit()
            
            logger.info(f"Created event: {db_event.event_id}")
            return self._convert_to_model(db_event)
            
        except SQLAlchemyError as e:
            logger.error(f"Database error creating event: {e}")
            await self.db.rollback()
            raise DatabaseError(f"Failed to create event: {e}")
        except Exception as e:
            logger.error(f"Unexpected error creating event: {e}")
            await self.db.rollback()
            raise DatabaseError(f"Unexpected error creating event: {e}")
        
    async def create_events(self, user_id: int, event_data: List[EventCreate]) -> List[Event]:
        """
        Create multiple events.
        
        Args:
            event_data: List of event data to create
        
        Returns:
            List of created events
            
        Raises:
            DatabaseError: If there's a database error
        """
        try:
            db_events = [self._convert_to_db_model(user_id, event) for event in event_data]
            self.db.add_all(db_events)
            await self.db.commit()
            
            return [self._convert_to_model(db_event) for db_event in db_events] 
        
        except SQLAlchemyError as e:
            logger.error(f"Database error creating events: {e}")
            await self.db.rollback()
            raise DatabaseError(f"Failed to create events: {e}")
        except Exception as e:
            logger.error(f"Unexpected error creating events: {e}")

    async def create_recurring_events(
        self,
        user_id: int,
        event_data: EventCreate,
        recurrence_type: str,
        count: int,
        interval: int = 1,
        byweekday: Optional[str] = None,
        bysetpos: Optional[int] = None,
    ) -> List[Event]:
        """
        Create a series of recurring events sharing a recurrence_id.

        Args:
            user_id: Owner user ID
            event_data: Template event (startDate is the first occurrence)
            recurrence_type: daily / weekly / monthly / yearly
            count: Number of occurrences to create
            interval: Repeat every N periods (default 1; 2 = bi-weekly)
            byweekday: Comma-separated weekday codes e.g. "MO,WE,FR"
            bysetpos: Position within period (1=first, -1=last)

        Returns:
            List of created Event instances
        """
        try:
            shared_recurrence_id = str(uuid.uuid4())
            dates, rule_str = self._build_rrule(
                event_data.startDate, recurrence_type, count,
                interval=interval, byweekday=byweekday, bysetpos=bysetpos,
            )

            # All-or-nothing conflict check: verify every occurrence before writing.
            duration_minutes = event_data.duration or 0
            conflicts = []
            for i, occurrence_start in enumerate(dates):
                occurrence_end = occurrence_start + timedelta(minutes=duration_minutes)
                conflicting = await self.check_event_conflict(user_id, occurrence_start, occurrence_end)
                if conflicting:
                    conflicts.append({
                        "index": i,
                        "startDate": occurrence_start.isoformat(),
                        "conflicting_title": conflicting.title,
                        "conflicting_id": conflicting.id,
                    })
            if conflicts:
                raise RecurringConflictError(conflicts)

            db_events = []
            for occurrence_start in dates:
                occurrence = EventCreate(
                    title=event_data.title,
                    category=event_data.category,
                    description=event_data.description,
                    startDate=occurrence_start,
                    duration=event_data.duration,
                    location=event_data.location,
                )
                db_events.append(
                    self._convert_to_db_model(
                        user_id,
                        occurrence,
                        recurrence_id=shared_recurrence_id,
                        recurrence_type=recurrence_type,
                        rrule_string=rule_str,
                    )
                )

            self.db.add_all(db_events)
            await self.db.commit()

            logger.info(f"Created {len(db_events)} recurring events (recurrence_id={shared_recurrence_id})")
            return [self._convert_to_model(e) for e in db_events]

        except RecurringConflictError:
            raise  # propagate with full conflict details intact
        except SQLAlchemyError as e:
            logger.error(f"Database error creating recurring events: {e}")
            await self.db.rollback()
            raise DatabaseError(f"Failed to create recurring events: {e}")
        except Exception as e:
            logger.error(f"Unexpected error creating recurring events: {e}")
            await self.db.rollback()
            raise DatabaseError(f"Unexpected error creating recurring events: {e}")

    async def get_event_by_event_id(self, event_id: str) -> Event:
        """
        Get event by event_id (UUID).
        
        Args:
            event_id: Event ID (UUID) to retrieve
            
        Returns:
            Event
            
        Raises:
            EventNotFoundError: If event is not found
            DatabaseError: If there's a database error
        """
        try:
            stmt = select(EventModel).where(EventModel.event_id == event_id)
            result = await self.db.execute(stmt)
            db_event = result.scalar_one_or_none()
            
            if db_event:
                return self._convert_to_model(db_event)
            raise EventNotFoundError(f"Event with ID {event_id} not found")
            
        except EventNotFoundError:
            raise
        except SQLAlchemyError as e:
            logger.error(f"Database error retrieving event {event_id}: {e}")
            raise DatabaseError(f"Database error retrieving event {event_id}: {e}")
        except Exception as e:
            logger.error(f"Unexpected error retrieving event {event_id}: {e}")
            raise DatabaseError(f"Unexpected error retrieving event {event_id}: {e}")
         
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
    
    async def get_events_by_date_range(
        self,
        user_id: int,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> List[Event]:
        """
        Get events within an optional date range for a specific user.
        
        Args:
            user_id: User ID to filter events
            start_date: Optional start date (YYYY-MM-DD HH:MM:SS)
            end_date: Optional end date (YYYY-MM-DD HH:MM:SS)
            
        Returns:
            List of events filtered by optional date range (empty list if no events found)
            
        Raises:
            DatabaseError: If there's a database error
        """
        try:
            conditions = [EventModel.user_id == user_id]

            # Overlap condition: event overlaps [start_date, end_date] if
            # event.startDate < end_date AND event.endDate > start_date
            if start_date and end_date:
                sd = self._ensure_datetime(start_date)
                ed = self._ensure_datetime(end_date)
                conditions.append(EventModel.startDate < ed)
                conditions.append(EventModel.endDate > sd)
            elif start_date:
                conditions.append(EventModel.endDate > self._ensure_datetime(start_date))
            elif end_date:
                conditions.append(EventModel.startDate < self._ensure_datetime(end_date))

            stmt = select(EventModel).where(*conditions).order_by(EventModel.startDate.asc())
            
            result = await self.db.execute(stmt)
            db_events = result.scalars().all()
            
            return [self._convert_to_model(event) for event in db_events]

        except SQLAlchemyError as e:
            logger.error(f"Database error retrieving events by date range: {e}")
            raise DatabaseError(f"Database error retrieving events by date range: {e}")
        except Exception as e:
            logger.error(f"Unexpected error retrieving events by date range: {e}")
            raise DatabaseError(f"Unexpected error retrieving events by date range: {e}")

    
    async def update_event(self, event_id: str, user_id: int, event_data: EventUpdate) -> Event:
        """
        Update an existing event.
        
        Args:
            event_id: Event ID (UUID) to update
            user_id: User ID to verify ownership
            event_data: Updated event data
            
        Returns:
            Updated event
            
        Raises:
            EventNotFoundError: If event is not found
            EventPermissionError: If user doesn't have permission
            DatabaseError: If there's a database error
        """
        try:
            # First, get the existing event to verify ownership
            stmt = select(EventModel).where(EventModel.event_id == event_id)
            result = await self.db.execute(stmt)
            db_event = result.scalar_one_or_none()
            
            if not db_event:
                logger.warning(f"Event not found for update: {event_id}")
                raise EventNotFoundError(f"Event with ID {event_id} not found")
            
            if db_event.user_id != user_id:
                logger.warning(f"User {user_id} not authorized to update event {event_id}")
                raise EventPermissionError(f"User {user_id} not authorized to update event {event_id}")
            
            # Update fields
            update_data = {}
            logger.info(f"Processing update fields for event {event_id}")
            logger.info(f"Title: {event_data.title}, StartDate: {event_data.startDate}, Location: {event_data.location}")
            
            if event_data.title is not None:
                update_data['title'] = event_data.title
            if event_data.category is not None:
                update_data['category'] = event_data.category
            if event_data.description is not None:
                update_data['description'] = event_data.description
            if event_data.startDate is not None:
                update_data['startDate'] = event_data.startDate
            if event_data.location is not None:
                update_data['location'] = event_data.location
            
            # Handle endDate and duration logic
            logger.info(f"Update event {event_id}: duration={event_data.duration}, startDate={event_data.startDate}")
            
            if event_data.duration is not None or event_data.startDate is not None:
                start_date = event_data.startDate if event_data.startDate is not None else db_event.startDate
                duration = event_data.duration if event_data.duration is not None else 0
                update_data['endDate'] = start_date + timedelta(minutes=duration)
            
            if update_data:
                stmt = update(EventModel).where(EventModel.event_id == event_id).values(**update_data).returning(EventModel)
                result = await self.db.execute(stmt)
                db_event = result.scalar_one_or_none()
                await self.db.commit()
                logger.info(f"Updated event: {event_id}")
                if db_event:
                    return self._convert_to_model(db_event)
                else:
                    raise DatabaseError(f"Failed to retrieve updated event {event_id}")
            else:
                # No changes to make, return the original event
                return self._convert_to_model(db_event)
                
        except (EventNotFoundError, EventPermissionError, HTTPException):
            raise
        except SQLAlchemyError as e:
            logger.error(f"Database error updating event {event_id}: {e}")
            await self.db.rollback()
            raise DatabaseError(f"Database error updating event {event_id}: {e}")
        except Exception as e:
            logger.error(f"Unexpected error updating event {event_id}: {e}")
            await self.db.rollback()
            raise DatabaseError(f"Unexpected error updating event {event_id}: {e}")
    
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
            stmt = delete(EventModel).where(
                EventModel.event_id == event_id,
                EventModel.user_id == user_id
            )
            result = await self.db.execute(stmt)
            deleted_count = result.rowcount
            
            if deleted_count == 1:
                await self.db.commit()
                logger.info(f"Deleted event: {event_id}")
                return True
            else:
                await self.db.rollback()
                logger.warning(f"Event not found or not authorized for deletion: {event_id}")
                return False
            
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
        Search events by title, location, or description for a specific user.
        
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
                (
                    EventModel.title.ilike(search_term)
                    | EventModel.location.ilike(search_term)
                    | EventModel.description.ilike(search_term)
                ),
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

    async def check_event_conflict(
        self,
        user_id: int,
        start_date: datetime,
        end_date: datetime,
        exclude_event_id: Optional[str] = None
    ) -> Optional[Event]:
        """
        Check if there's an event that conflicts with the given date range.
        
        Args:
            user_id: User ID to filter events
            start_date: Start date of the time range to check
            end_date: End date of the time range to check
            exclude_event_id: Optional event ID to exclude from conflict check (useful for updates)
            
        Returns:
            Conflicting event if found, None if no conflicts
        """
        try:
            conditions = [
            EventModel.user_id == user_id,
            or_(
                and_(
                    EventModel.startDate < self._ensure_datetime(end_date),
                    EventModel.endDate > self._ensure_datetime(start_date)
                ),
                and_(
                    EventModel.startDate == self._ensure_datetime(start_date),
                    EventModel.endDate == self._ensure_datetime(end_date)
                )
            )
            ]
            # Exclude a specific event (useful when updating an event)
            if exclude_event_id:
                conditions.append(EventModel.event_id != exclude_event_id)
            
            stmt = select(EventModel).where(*conditions).limit(1)
            result = await self.db.execute(stmt)
            conflicting_event = result.scalar_one_or_none()
            
            if conflicting_event:
                logger.info(f"Found conflicting event: {conflicting_event.event_id} for time range {start_date} - {end_date}")
                return self._convert_to_model(conflicting_event)
            
            return None
            
        except SQLAlchemyError as e:
            logger.error(f"Database error checking event conflicts: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error checking event conflicts: {e}")
            return None

    async def delete_multiple_events(self, event_ids: List[str], user_id: int) -> bool:
        """
        Delete multiple events by their IDs.
        
        Args:
            event_ids: List of event IDs (UUIDs) to delete
            user_id: User ID to verify ownership
            
        Returns:
            True if ALL events were successfully deleted, False if ANY failed (none deleted)
        """
        try:
            stmt = delete(EventModel).where(
                EventModel.event_id.in_(event_ids),
                EventModel.user_id == user_id
            )
            result = await self.db.execute(stmt)
            deleted_count = result.rowcount
            
            if deleted_count == len(event_ids):
                await self.db.commit()
                logger.info(f"Successfully deleted {deleted_count} events")
                return True
            else:
                await self.db.rollback()
                logger.warning(f"Only {deleted_count} out of {len(event_ids)} events were deleted")
                return False
            
        except SQLAlchemyError as e:
            logger.error(f"Database error in bulk delete operation: {e}")
            await self.db.rollback()
            return False
        except Exception as e:
            logger.error(f"Unexpected error in bulk delete operation: {e}")
            await self.db.rollback()
            return False

    async def claim_and_get_reminder_events(
        self, window_start: datetime, window_end: datetime
    ) -> List[Tuple[Event, str, Optional[str]]]:
        """
        Atomically claim unclaimed reminder events in [window_start, window_end].

        Two-step approach safe against concurrent workers:
          1. SELECT candidate event_ids (reminder_sent=False, user has push_token).
          2. UPDATE ... WHERE event_id IN (...) AND reminder_sent=FALSE RETURNING event_id
             — only the process whose UPDATE wins gets a non-empty RETURNING set.
          3. Fetch full event + user info for claimed IDs only.

        Returns List of (Event, push_token, user_timezone) for events this process claimed.
        """
        try:
            # Step 1: find candidates
            candidate_stmt = (
                select(EventModel.event_id)
                .join(UserModel, EventModel.user_id == UserModel.id)
                .where(
                    EventModel.startDate >= window_start,
                    EventModel.startDate < window_end,
                    EventModel.reminder_sent == False,
                    UserModel.push_token.isnot(None),
                )
            )
            candidate_result = await self.db.execute(candidate_stmt)
            candidate_ids = [row[0] for row in candidate_result.all()]

            if not candidate_ids:
                return []

            # Step 2: atomic claim — only rows still unclaimed are returned
            claim_stmt = (
                update(EventModel)
                .where(
                    EventModel.event_id.in_(candidate_ids),
                    EventModel.reminder_sent == False,
                )
                .values(reminder_sent=True)
                .returning(EventModel.event_id)
            )
            claim_result = await self.db.execute(claim_stmt)
            claimed_ids = {row[0] for row in claim_result.all()}
            await self.db.commit()

            if not claimed_ids:
                return []

            # Step 3: fetch full details for claimed events
            fetch_stmt = (
                select(EventModel, UserModel.push_token, UserModel.timezone)
                .join(UserModel, EventModel.user_id == UserModel.id)
                .where(EventModel.event_id.in_(claimed_ids))
            )
            fetch_result = await self.db.execute(fetch_stmt)
            return [
                (self._convert_to_model(row[0]), row[1], row[2])
                for row in fetch_result.all()
            ]

        except SQLAlchemyError as e:
            logger.error(f"Database error claiming reminder events: {e}")
            await self.db.rollback()
            return []

    async def clear_push_tokens_for_events(self, event_ids: List[str]) -> int:
        """
        Clear push_token for users who own the given events.
        Called when Expo reports DeviceNotRegistered / InvalidCredentials so stale
        tokens are removed and the user is prompted to re-register on next app open.
        Returns the number of users whose token was cleared.
        """
        if not event_ids:
            return 0
        try:
            subq = select(EventModel.user_id).where(EventModel.event_id.in_(event_ids))
            stmt = (
                update(UserModel)
                .where(UserModel.id.in_(subq))
                .values(push_token=None)
            )
            result = await self.db.execute(stmt)
            await self.db.commit()
            cleared = result.rowcount
            logger.info(f"Cleared push tokens for {cleared} user(s) with invalid/unregistered devices")
            return cleared
        except SQLAlchemyError as e:
            logger.error(f"Database error clearing push tokens: {e}")
            await self.db.rollback()
            return 0

    async def revert_reminder_claims(self, event_ids: List[str]) -> None:
        """Reset reminder_sent=False for events whose push notification failed."""
        if not event_ids:
            return
        try:
            stmt = (
                update(EventModel)
                .where(
                    EventModel.event_id.in_(event_ids),
                    EventModel.reminder_sent == True,  # only undo what we set
                )
                .values(reminder_sent=False)
            )
            await self.db.execute(stmt)
            await self.db.commit()
        except SQLAlchemyError as e:
            logger.error(f"Database error reverting reminder claims: {e}")
            await self.db.rollback()

    async def delete_by_recurrence_id(
        self, recurrence_id: str, user_id: int, from_date: Optional[datetime] = None
    ) -> int:
        """
        Delete all events in a recurring series for a user.
        If from_date is given, only deletes occurrences starting on or after that date.
        Returns the number of deleted events.
        """
        try:
            conditions = [
                EventModel.recurrence_id == recurrence_id,
                EventModel.user_id == user_id,
            ]
            if from_date:
                conditions.append(EventModel.startDate >= from_date)
            stmt = delete(EventModel).where(*conditions)
            result = await self.db.execute(stmt)
            await self.db.commit()
            deleted = result.rowcount
            logger.info(f"Deleted {deleted} events for recurrence_id={recurrence_id} (from_date={from_date})")
            return deleted
        except SQLAlchemyError as e:
            logger.error(f"Database error deleting series {recurrence_id}: {e}")
            await self.db.rollback()
            return 0

    async def update_by_recurrence_id(
        self,
        recurrence_id: str,
        user_id: int,
        event_data: "EventUpdate",
        from_date: Optional[datetime] = None,
        time_shift: Optional[timedelta] = None,
    ) -> List[Event]:
        """
        Update all events in a recurring series for a user.
        - from_date: if set, only updates occurrences starting on or after that date.
        - time_shift: if set, shifts each event's startDate and endDate by this delta.
        - event_data: non-time fields (title, location, category, description) applied uniformly.
        Returns the list of updated events.
        """
        try:
            conditions = [
                EventModel.recurrence_id == recurrence_id,
                EventModel.user_id == user_id,
            ]
            if from_date:
                conditions.append(EventModel.startDate >= from_date)

            stmt = select(EventModel).where(*conditions).order_by(EventModel.startDate.asc())
            result = await self.db.execute(stmt)
            db_events = list(result.scalars().all())

            if not db_events:
                return []

            for ev in db_events:
                if event_data.title is not None:
                    ev.title = event_data.title
                if event_data.category is not None:
                    ev.category = event_data.category
                if event_data.description is not None:
                    ev.description = event_data.description
                if event_data.location is not None:
                    ev.location = event_data.location
                if time_shift is not None:
                    ev.startDate = ev.startDate + time_shift
                    ev.endDate = ev.endDate + time_shift
                if event_data.duration is not None and event_data.duration >= 0:
                    # Explicit duration change: recalculate endDate from (shifted) startDate
                    ev.endDate = ev.startDate + timedelta(minutes=event_data.duration)

            await self.db.commit()
            logger.info(f"Updated {len(db_events)} events for recurrence_id={recurrence_id}")
            return [self._convert_to_model(ev) for ev in db_events]

        except SQLAlchemyError as e:
            logger.error(f"Database error updating series {recurrence_id}: {e}")
            await self.db.rollback()
            return []

    async def migrate_events_to_user(self, from_user_id: int, to_user_id: int) -> int:
        """
        Reassign all events from one user to another.
        Called before deleting the SMS-created account when a user links their phone
        to an existing account — prevents cascade-delete from wiping their events.
        Returns the number of events migrated.
        """
        try:
            stmt = (
                update(EventModel)
                .where(EventModel.user_id == from_user_id)
                .values(user_id=to_user_id)
            )
            result = await self.db.execute(stmt)
            await self.db.commit()
            migrated = result.rowcount
            logger.info(f"Migrated {migrated} events from user {from_user_id} to user {to_user_id}")
            return migrated
        except SQLAlchemyError as e:
            logger.error(f"Database error migrating events: {e}")
            await self.db.rollback()
            return 0

    async def delete_all_events(self, user_id: int) -> int:
        """
        Delete all events for a user.

        Returns:
            Number of deleted events.
        """
        try:
            stmt = delete(EventModel).where(EventModel.user_id == user_id)
            result = await self.db.execute(stmt)
            await self.db.commit()
            deleted_count = result.rowcount
            logger.info(f"Deleted all {deleted_count} events for user {user_id}")
            return deleted_count
        except SQLAlchemyError as e:
            logger.error(f"Database error deleting all events for user {user_id}: {e}")
            await self.db.rollback()
            return 0
        except Exception as e:
            logger.error(f"Unexpected error deleting all events for user {user_id}: {e}")
            await self.db.rollback()
            return 0
