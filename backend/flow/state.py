
from typing import TypedDict, Annotated, Optional
from langchain_core.messages import BaseMessage
from langgraph.graph import add_messages


def merge_is_success(old: bool, new: bool) -> bool:
    return new


class FlowState(TypedDict):
    # Shared
    router_messages: Annotated[list[BaseMessage], add_messages]
    input_text: str
    current_datetime: str
    weekday: str
    days_in_month: int
    user_id: int
    route: dict
    is_success: Annotated[bool, merge_is_success]
    # Conflict Resolution
    conflict_check_request: Optional[dict]
    conflict_check_result: Optional[dict]
    conflict_resolution_messages: Annotated[list[BaseMessage], add_messages]
    # Scheduling Agent
    scheduling_messages: Annotated[list[BaseMessage], add_messages]
    scheduling_operation: Optional[str]  # 'create' | 'update' | 'delete' | 'list'
    scheduling_event_data: Optional[dict]
    scheduling_result: Optional[dict]
