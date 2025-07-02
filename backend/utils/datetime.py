from datetime import datetime
from typing import Optional

def validate_datetime(datetime_str: str) -> bool:
    """Validate datetime format (ISO format with timezone only)."""
    try:
        # Only support ISO format with timezone
        datetime.fromisoformat(datetime_str)
        return True
    except ValueError:
        return False

def validate_duration(duration: Optional[int]) -> bool:
    """Validate duration is positive if provided."""
    return duration is None or duration > 0

def convert_datetime_string_to_datetime(datetime_str: str) -> datetime:
    """
    Convert LLM datetime string to datetime object.
    Only supports ISO format with timezone.
    """
    try:
        # Only support ISO format with timezone
        return datetime.fromisoformat(datetime_str)
    except ValueError:
        raise ValueError(f"Invalid datetime format. Expected ISO format with timezone, got: {datetime_str}")
