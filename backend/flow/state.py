
from typing import TypedDict, Annotated
from langchain_core.messages import BaseMessage
from langgraph.graph import add_messages


class FlowState(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]
    input_text: str
    current_datetime: str
    weekday: str
    days_in_month: int
    user_id: int
    route: dict
    create_data: dict
    list_data: dict
    delete_data: dict