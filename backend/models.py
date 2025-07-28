from typing import Optional, List
from datetime import datetime as dt
from pydantic import BaseModel, EmailStr, Field, field_validator


# User Models
class UserBase(BaseModel):
    name: str
    email: EmailStr

class UserCreate(UserBase):
    user_id: str
    password: str = Field(..., min_length=6, description="Password must be at least 6 characters long")

class UserRegister(UserBase):
    password: str = Field(..., min_length=6, description="Password must be at least 6 characters long")

class UserUpdate(BaseModel):
    name: Optional[str] = None
    email: Optional[EmailStr] = None
    password: Optional[str] = Field(None, min_length=6, description="Password must be at least 6 characters long")

class User(UserBase):
    id: int  # Internal DB ID
    user_id: str  # Public-facing UUID for API
    password: Optional[str] = None
    created_at: Optional[str] = None

    class Config:
        from_attributes = True
        arbitrary_types_allowed = True

# Event Models
class EventBase(BaseModel):
    title: str
    startDate: dt  # Use proper datetime type with timezone support
    endDate: dt  # End date
    duration: Optional[int] = None  # Duration in minutes for input
    location: Optional[str] = None

    class Config:
        json_encoders = {
            dt: lambda v: v.isoformat()
        }

class EventCreate(BaseModel):
    title: str
    startDate: dt
    duration: Optional[int] = None  # Duration in minutes for input
    location: Optional[str] = None

    class Config:
        json_encoders = {
            dt: lambda v: v.isoformat()
        }

class EventUpdate(BaseModel):
    title: Optional[str] = None
    startDate: Optional[dt] = None
    duration: Optional[int] = None  # Duration in minutes for input
    location: Optional[str] = None

    class Config:
        json_encoders = {
            dt: lambda v: v.isoformat()
        }

class Event(EventBase):
    id: str  # This is the event_id (UUID) for API exposure
    user_id: int  # References internal user.id

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
    event: EventCreate
    conflict_event: Optional[Event] = None

class SuccessfulUpdateResponse(BaseModel):
    type: str = "update"
    message: str
    events: List[Event]
    update_arguments: dict
    update_conflict_event: Optional[Event] = None
