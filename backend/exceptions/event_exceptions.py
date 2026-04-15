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


class RecurringConflictError(EventConflictError):
    """
    Raised when one or more occurrences of a recurring series conflict with
    existing events. All-or-nothing: the series is NOT created.

    conflicts: list of dicts, one per conflicting occurrence:
      {
        "index":              int,   # 0-based occurrence index
        "startDate":          str,   # ISO 8601
        "conflicting_title":  str,
        "conflicting_id":     str,
      }
    """
    def __init__(self, conflicts: list):
        self.conflicts = conflicts
        super().__init__(f"{len(conflicts)} occurrence(s) conflict with existing events")


class DatabaseError(Exception):
    """Raised when there's a database-related error"""
    pass


class ValidationError(Exception):
    """Raised when input data is invalid"""
    pass 