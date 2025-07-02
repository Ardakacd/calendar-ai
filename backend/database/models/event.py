from typing import Optional
from sqlalchemy import String, Integer, Text, DateTime, CheckConstraint, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func
import uuid

from .base import Base

# Event model using mapped approach
class EventModel(Base):
    __tablename__ = "events"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    datetime: Mapped[DateTime] = mapped_column(DateTime(timezone=True), nullable=False)  # Format: YYYY-MM-DDTHH:MM:SS±HH:MM
    duration: Mapped[Optional[int]] = mapped_column(Integer)  # Duration in minutes
    location: Mapped[Optional[str]] = mapped_column(String(255))
    
    # Foreign key to user
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False)
    
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    # Many-to-one relationship with user (using string reference)
    user: Mapped["UserModel"] = relationship("UserModel", back_populates="events")

    def __repr__(self):
        return f"<EventModel(id='{self.id}', title='{self.title}', user_id='{self.user_id}')>" 