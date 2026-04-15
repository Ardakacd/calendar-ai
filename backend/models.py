from typing import Optional, List
from datetime import datetime as dt
from pydantic import BaseModel, EmailStr, Field, field_validator


# User Models
class UserBase(BaseModel):
    name: str
    email: EmailStr
    phone_number: Optional[str] = None
    timezone: Optional[str] = None

class UserCreate(UserBase):
    user_id: str
    password: str = Field(..., min_length=6, description="Password must be at least 6 characters long")

class UserRegister(UserBase):
    password: str = Field(..., min_length=6, description="Password must be at least 6 characters long")

class UserUpdate(BaseModel):
    name: Optional[str] = None
    email: Optional[EmailStr] = None
    password: Optional[str] = Field(None, min_length=6, description="Password must be at least 6 characters long")
    phone_number: Optional[str] = None
    timezone: Optional[str] = None
    push_token: Optional[str] = None

class User(UserBase):
    id: int  # Internal DB ID
    user_id: str  # Public-facing UUID for API
    password: Optional[str] = None
    phone_number: Optional[str] = None
    timezone: Optional[str] = None
    push_token: Optional[str] = None
    created_at: Optional[str] = None

    class Config:
        from_attributes = True
        arbitrary_types_allowed = True

# Event Models
class EventBase(BaseModel):
    title: str
    category: Optional[str] = None  # work / personal / health / social
    description: Optional[str] = Field(None, max_length=5000)
    startDate: dt  # Use proper datetime type with timezone support
    endDate: dt  # End date
    duration: Optional[int] = None  # Duration in minutes for input
    location: Optional[str] = None

    class Config:
        json_encoders = {
            dt: lambda v: v.isoformat()
        }

class RecurrenceCreate(BaseModel):
    type: str  # daily / weekly / monthly / yearly
    count: int = Field(..., ge=1, le=365, description="How many occurrences to create")
    interval: int = Field(default=1, ge=1, description="Repeat every N periods (2 = bi-weekly, 3 = every 3 months)")
    byweekday: Optional[str] = Field(default=None, description="Comma-separated weekday codes: MO,TU,WE,TH,FR,SA,SU")
    bysetpos: Optional[int] = Field(default=None, description="Position within period: 1=first, -1=last (e.g. first Monday of month)")

class EventCreate(BaseModel):
    title: str
    category: Optional[str] = None
    description: Optional[str] = Field(None, max_length=5000)
    startDate: dt
    duration: Optional[int] = None  # Duration in minutes for input
    location: Optional[str] = None
    recurrence: Optional[RecurrenceCreate] = None

    class Config:
        json_encoders = {
            dt: lambda v: v.isoformat()
        }

class EventUpdate(BaseModel):
    title: Optional[str] = None
    category: Optional[str] = None
    description: Optional[str] = Field(None, max_length=5000)
    startDate: Optional[dt] = None
    duration: Optional[int] = None  # Duration in minutes for input
    location: Optional[str] = None

    class Config:
        json_encoders = {
            dt: lambda v: v.isoformat()
        }


class SeriesUpdateRequest(BaseModel):
    scope: str = Field(..., description="'all' to update every occurrence, 'future' to update from from_date onward")
    from_date: Optional[dt] = Field(None, description="Required when scope='future': earliest occurrence to update (inclusive)")
    title: Optional[str] = None
    category: Optional[str] = None
    description: Optional[str] = Field(None, max_length=5000)
    location: Optional[str] = None
    duration: Optional[int] = Field(None, description="New duration in minutes")
    time_shift_minutes: Optional[int] = Field(None, description="Shift every occurrence's start/end time by N minutes (negative = earlier)")

    class Config:
        json_encoders = {dt: lambda v: v.isoformat()}


class SeriesUpdateResponse(BaseModel):
    updated_count: int
    recurrence_id: str
    scope: str
    message: str


class SeriesDeleteResponse(BaseModel):
    deleted_count: int
    recurrence_id: str
    scope: str
    message: str

class Event(EventBase):
    id: str  # This is the event_id (UUID) for API exposure
    user_id: int  # References internal user.id
    recurrence_id: Optional[str] = None
    recurrence_type: Optional[str] = None
    rrule_string: Optional[str] = None

    class Config:
        from_attributes = True
        arbitrary_types_allowed = True
        json_encoders = {
            dt: lambda v: v.isoformat()
        }

# User with Events (for detailed user views)
class UserWithEvents(User):
    events: List[Event] = []

# Authentication Models
class UserLogin(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=6, description="Password must be at least 6 characters long")

class PasswordChangeRequest(BaseModel):
    current_password: str = Field(..., min_length=6, description="Current password")
    new_password: str = Field(..., min_length=6, description="New password must be at least 6 characters long")

class Token(BaseModel):
    access_token: str
    refresh_token: str
    user_name: str
    

class TokenData(BaseModel):
    user_id: Optional[int] = None

class RefreshTokenRequest(BaseModel):
    refresh_token: str

# Speech Recognition Models
class TranscribeRequest(BaseModel):
    audio_data: str  # Base64 encoded audio


class TranscribeMessage(BaseModel):
    message: str

class ProcessInput(BaseModel):
    text: str
    current_datetime: str
    weekday: str
    days_in_month: int

class SuccessfulListResponse(BaseModel):
    type: str = "list"
    message: str
    events: List[Event]

class SuccessfulDeleteResponse(BaseModel):
    type: str = "delete"
    message: str
    events: List[Event]

class SuccessfulCreateResponse(BaseModel):
    type: str = "create"
    message: str
    events: List[EventCreate]
    conflict_events: Optional[List[Event]] = None

class SuccessfulUpdateResponse(BaseModel):
    type: str = "update"
    message: str
    events: List[Event]
    update_arguments: dict
    update_conflict_event: Optional[Event] = None
