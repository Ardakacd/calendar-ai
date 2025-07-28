from langchain_core.messages import SystemMessage, AIMessage
from langchain_core.prompts import PromptTemplate
from ..state import FlowState
from .prompt import CREATE_EVENT_AGENT_PROMPT
from ..llm import model
from tenacity import retry, stop_after_attempt, wait_random_exponential, retry_if_exception_type
from openai import OpenAIError, RateLimitError
from langgraph.graph import END
import json
from typing import Optional
from adapter.event_adapter import EventAdapter
from database import get_async_db_context_manager
from models import Event
import traceback
from datetime import timedelta, datetime, timezone
from zoneinfo import ZoneInfo

retryable_exceptions = (OpenAIError, RateLimitError)


@retry(
    wait=wait_random_exponential(min=1, max=10),
    stop=stop_after_attempt(3),
    retry=retry_if_exception_type(retryable_exceptions),
)
async def create_agent(state: FlowState):
    
    template = PromptTemplate.from_template(CREATE_EVENT_AGENT_PROMPT)
    prompt_text = template.format(
            current_datetime=state['current_datetime'],
            weekday=state['weekday'],
            days_in_month=state['days_in_month']
        )
    
    if state["messages"] and isinstance(state["messages"][0], SystemMessage):
        state["messages"][0] = SystemMessage(content=prompt_text)
    else:
        state["messages"].insert(0, SystemMessage(content=prompt_text))
    try:
        response = [await model.ainvoke(state["messages"])]
        create_event_data = json.loads(response[0].content)
        state['create_event_data'] = create_event_data
    except Exception as e:
        state['create_event_data'] = {"message": "Bir hata olustu. Lutfen daha sonra tekrar deneyiniz."}
    
    return state

def create_action(state: FlowState):
    if "function" in state['create_event_data'] and "arguments" in state['create_event_data']:
        return "check_event_conflict"
    else:
        return "create_message_handler"
        
def create_message_handler(state: FlowState):
    message = state['create_event_data'].get('message', 'Bir hata olustu. Lutfen daha sonra tekrar deneyiniz.')
    return {"messages": [AIMessage(content=message)]}

async def check_event_conflict(state: FlowState) -> Optional[Event]:
    """
    Check for event conflicts before creating the event.
    """
    try:
        async with get_async_db_context_manager() as db:
            adapter = EventAdapter(db)
            start_date = datetime.fromisoformat(state['create_event_data']['arguments']['startDate'])
            duration = state['create_event_data']['arguments'].get('duration', 0)
            end_date = start_date + timedelta(minutes=duration)
            conflict_event = await adapter.check_event_conflict(state['user_id'], start_date, end_date)
            state['create_conflict_event'] = conflict_event
            state['is_success'] = True    
            state['messages'].append(AIMessage(content="Asagidaki etkinligi olusturmak istediginize emin misiniz?"))
            return state
    except Exception as e:
        state['messages'].append(AIMessage(content="Bir hata olustu. Lutfen daha sonra tekrar deneyiniz."))
        return state
