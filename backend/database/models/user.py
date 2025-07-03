from typing import List
from sqlalchemy import String, DateTime, CheckConstraint, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func 
import uuid

from .base import Base

class UserModel(Base):
    __tablename__ = "users"

    # 🔹 Internal primary key
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # 🔸 Public-facing ID for APIs
    user_id: Mapped[str] = mapped_column(String(36), unique=True, nullable=False, default=lambda: str(uuid.uuid4()))

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    password: Mapped[str] = mapped_column(String(255), nullable=False)
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


