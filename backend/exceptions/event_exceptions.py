"""
Event-related custom exceptions.
"""


class EventNotFoundError(Exception):
    """Raised when an event is not found"""
    pass


class EventPermissionError(Exception):
    """Raised when user doesn't have permission to access/modify an event"""
    pass


class EventConflictError(Exception):
    """Raised when there's a scheduling conflict"""
    pass


class DatabaseError(Exception):
    """Raised when there's a database-related error"""
    pass


class ValidationError(Exception):
    """Raised when input data is invalid"""
    pass 