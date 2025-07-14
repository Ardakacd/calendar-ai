"""
Custom exceptions for the calendar application.
"""

from .event_exceptions import (
    EventNotFoundError,
    EventPermissionError,
    EventConflictError,
    DatabaseError,
    ValidationError
)

__all__ = [
    "EventNotFoundError",
    "EventPermissionError", 
    "EventConflictError",
    "DatabaseError",
    "ValidationError"
] 