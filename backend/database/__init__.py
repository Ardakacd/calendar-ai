"""
Database package for Calendar AI application.

This package provides:
- Database models (EventModel, UserModel)
- Database configuration and connection pooling
- Database initialization and health checks
- Production-ready database utilities
"""

from .models.event import EventModel
from .models.user import UserModel
from .config import (
    get_db,
    get_db_session,
    get_async_db,
    init_db,
    get_pool_status,
    health_check,
    get_async_db_context_manager
)

__all__ = [
    "EventModel",
    "UserModel",
    "get_db",
    "get_db_session",
    "get_async_db",
    "init_db",
    "get_pool_status",
    "health_check",
    "get_async_db_context_manager"
]

# This file makes the database directory a Python package 