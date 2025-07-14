from typing import Optional
from sqlalchemy import String, Integer, Text, DateTime, CheckConstraint, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func
import uuid
from datetime import datetime

from .base import Base

# Event model using mapped approach
class EventModel(Base):
    __tablename__ = "events"

    # 🔹 Internal primary key for performance
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # 🔸 Public-facing ID for APIs
    event_id: Mapped[str] = mapped_column(String(36), unique=True, nullable=False, default=lambda: str(uuid.uuid4()))

    title: Mapped[str] = mapped_column(String(255), nullable=False)
    startDate: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    endDate: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=False)
    location: Mapped[Optional[str]] = mapped_column(String(255))
    
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    user: Mapped["UserModel"] = relationship("UserModel", back_populates="events")

    def __repr__(self):
        return f"<EventModel(id={self.id}, event_id='{self.event_id}', title='{self.title}')>"
