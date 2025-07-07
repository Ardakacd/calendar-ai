from pydantic import BaseModel, EmailStr, Field, computed_field
from typing import Optional, List
from datetime import datetime as dt

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
    endDate: Optional[dt] = None  # End date (nullable)
    duration: Optional[int] = None  # Duration in minutes for input
    location: Optional[str] = None

    @computed_field
    @property
    def computed_duration(self) -> Optional[int]:
        """Calculate duration in minutes from startDate and endDate"""
        if self.startDate and self.endDate:
            delta = self.endDate - self.startDate
            return int(delta.total_seconds() / 60)
        return None

    class Config:
        json_encoders = {
            dt: lambda v: v.isoformat()
        }

class EventCreate(BaseModel):
    title: str
    startDate: dt
    duration: Optional[int] = None  # Duration in minutes for input
    endDate: Optional[dt] = None  # End date (nullable) - can be provided directly
    location: Optional[str] = None
    user_id: int  # References internal user.id

    class Config:
        json_encoders = {
            dt: lambda v: v.isoformat()
        }

class EventUpdate(BaseModel):
    title: Optional[str] = None
    startDate: Optional[dt] = None
    duration: Optional[int] = None  # Duration in minutes for input
    endDate: Optional[dt] = None  # End date (nullable) - can be provided directly
    location: Optional[str] = None

    class Config:
        json_encoders = {
            dt: lambda v: v.isoformat()
        }

class Event(EventBase):
    id: str  # This is the event_id (UUID) for API exposure
    user_id: int  # References internal user.id
    created_at: str

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

class TranscribeResponse(BaseModel):
    message: str
    action: str  # "create", "delete", "update", "query", "none"
    requires_confirmation: bool = False
    confirmation_data: Optional[dict] = None  # Contains the fields for confirmation modal
    event_id: Optional[str] = None

# Confirmation Models for the frontend
class EventConfirmationData(BaseModel):
    title: str
    startDate: str  # ISO format string
    duration: Optional[int] = None  # Duration in minutes
    location: Optional[str] = None
    event_id: Optional[str] = None  # For update/delete operations

class ConfirmationRequest(BaseModel):
    action: str  # "create", "update", "delete"
    event_data: EventConfirmationData 