from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List
from datetime import datetime as dt

# User Models
class UserBase(BaseModel):
    name: str
    email: EmailStr

class UserCreate(UserBase):
    id: str
    password: str = Field(..., min_length=6, description="Password must be at least 6 characters long")

class UserLogin(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=6, description="Password must be at least 6 characters long")

class UserRegister(UserBase):
    password: str = Field(..., min_length=6, description="Password must be at least 6 characters long")

class UserUpdate(BaseModel):
    name: Optional[str] = None
    email: Optional[str] = EmailStr
    password: Optional[str] = Field(None, min_length=6, description="Password must be at least 6 characters long")

class User(UserBase):
    id: str
    password: Optional[str] = None
    created_at: Optional[str] = None

    class Config:
        from_attributes = True
        arbitrary_types_allowed = True

# Event Models
class EventBase(BaseModel):
    title: str
    datetime: dt  # Use proper datetime type with timezone support
    duration: Optional[int] = None  # Duration in minutes
    location: Optional[str] = None

    class Config:
        json_encoders = {
            dt: lambda v: v.isoformat()
        }

class EventCreate(EventBase):
    user_id: str  # Required user ID for the relationship

class EventUpdate(BaseModel):
    title: Optional[str] = None
    datetime: Optional[dt] = None
    duration: Optional[int] = None
    location: Optional[str] = None

    class Config:
        json_encoders = {
            dt: lambda v: v.isoformat()
        }

class Event(EventBase):
    id: str
    user_id: str
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
    token_type: str
    user_id: str
    user_name: str
    expires_in: int  # Access token expiration time in seconds

class TokenData(BaseModel):
    user_id: Optional[str] = None

class RefreshTokenRequest(BaseModel):
    refresh_token: str

# Speech Recognition Models
class TranscribeRequest(BaseModel):
    audio_data: str  # Base64 encoded audio

class TranscribeResponse(BaseModel):
    message: str
    action: str  # "add", "delete", "update", "query", "none"
    event: Optional[Event] = None
    event_id: Optional[str] = None 