from typing import List, Optional
from sqlalchemy import String, DateTime, Date, CheckConstraint, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func
from datetime import date
import uuid

from .base import Base

class UserModel(Base):
    __tablename__ = "users"

    # 🔹 Internal primary key
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    user_id: Mapped[str] = mapped_column(String(36), unique=True, nullable=False, default=lambda: str(uuid.uuid4()))

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    password: Mapped[str] = mapped_column(String(255), nullable=False)
    phone_number: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, unique=True)
    timezone: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    # Legacy columns (unused); kept so existing DBs need no migration.
    linq_chat_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    push_token: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    summary_sent_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    events: Mapped[List["EventModel"]] = relationship(
        "EventModel",
        back_populates="user",
        cascade="all, delete-orphan"
    )

    __table_args__ = (
        CheckConstraint(
            "email ~* '^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$'",
            name="check_email_format"
        ),
        CheckConstraint(
            "length(password) >= 6",
            name="check_password_length"
        ),
    )

    def __repr__(self):
        return f"<UserModel(id={self.id}, user_id='{self.user_id}', email='{self.email}')>"


