"""
Custom exceptions for the calendar application.
"""

from .event_exceptions import (
    EventNotFoundError,
    EventPermissionError,
    EventConflictError,
    RecurringConflictError,
    DatabaseError,
    ValidationError
)

__all__ = [
    "EventNotFoundError",
    "EventPermissionError",
    "EventConflictError",
    "RecurringConflictError",
    "DatabaseError",
    "ValidationError"
] 