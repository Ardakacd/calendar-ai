
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
    previous_route: Optional[str]  # route classification from the previous turn
    conversation_summary: Optional[str]  # rolling summary of older messages
    # Conflict Resolution
    conflict_check_request: Optional[dict]
    conflict_check_result: Optional[dict]
    conflict_resolution_messages: list[BaseMessage]
    # Scheduling Agent — plain list (overwrite), per-operation working memory
    scheduling_messages: list[BaseMessage]
    scheduling_operation: Optional[str]  # 'create' | 'update' | 'delete' | 'list'
    scheduling_event_data: Optional[dict]
    scheduling_result: Optional[dict]
