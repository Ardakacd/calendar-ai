
from typing import TypedDict, Annotated, List, Optional
from langchain_core.messages import BaseMessage
from langgraph.graph import add_messages
from models import Event

def merge_is_success(old: bool, new: bool) -> bool:
    return new


class FlowState(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]
    input_text: str
    current_datetime: str
    weekday: str
    days_in_month: int
    user_id: int
    route: dict
    create_event_data: dict
    create_conflict_event: Optional[Event]
    list_date_range_data: dict
    list_date_range_filtered_events: List[Event]
    list_final_filtered_events: List[Event]
    delete_date_range_data: dict
    delete_date_range_filtered_events: List[Event]
    delete_final_filtered_events: List[Event]
    update_date_range_data: dict
    update_date_range_filtered_events: List[Event]
    update_final_filtered_events: List[Event]
    update_arguments: dict
    update_conflict_event: Optional[Event]
    is_success: Annotated[bool, merge_is_success]
