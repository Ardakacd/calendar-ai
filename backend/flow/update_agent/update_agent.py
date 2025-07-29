from langchain_core.messages import SystemMessage, AIMessage
from langchain_core.prompts import PromptTemplate
from ..state import FlowState
from .update_data_range_agent_prompt import UPDATE_DATE_RANGE_AGENT_PROMPT
from ..llm import model
from tenacity import retry, stop_after_attempt, wait_random_exponential, retry_if_exception_type
from openai import OpenAIError, RateLimitError
import json
from typing import List
from adapter.event_adapter import EventAdapter
from database import get_async_db_context_manager
from models import Event
from .update_filter_event_agent_prompt import UPDATE_FILTER_EVENT_AGENT_PROMPT
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

retryable_exceptions = (OpenAIError, RateLimitError)


@retry(
    wait=wait_random_exponential(min=1, max=10),
    stop=stop_after_attempt(3),
    retry=retry_if_exception_type(retryable_exceptions),
)
async def update_date_range_agent(state: FlowState):
    
    template = PromptTemplate.from_template(UPDATE_DATE_RANGE_AGENT_PROMPT)
    prompt_text = template.format(
            current_datetime=state['current_datetime'],
            weekday=state['weekday'],
            days_in_month=state['days_in_month']
        )
    
    if state["update_messages"] and isinstance(state["update_messages"][0], SystemMessage):
        state["update_messages"][0] = SystemMessage(content=prompt_text)
    else:
        state["update_messages"].insert(0, SystemMessage(content=prompt_text))
    
    try:
        response = [await model.ainvoke(state["update_messages"])]
        route_data = json.loads(response[0].content)
        state['update_date_range_data'] = route_data
    except Exception as e:
        state['update_date_range_data'] = {"message": "Bir hata olustu. Lutfen daha sonra tekrar deneyiniz."}
    
    return state

def update_action(state: FlowState):
    if "function" in state['update_date_range_data'] and "arguments" in state['update_date_range_data']:
        return "get_events_for_update"
    else:
        return "update_message_handler"
        
def update_message_handler(_: FlowState):
        return {"update_messages": [AIMessage(content="Bir hata olustu. Lutfen daha sonra tekrar deneyiniz.")]}

async def get_events_for_update(state: FlowState) -> List[Event]:
    """
    Get events by date range for updating.
    """
    try:
        async with get_async_db_context_manager() as db:
            adapter = EventAdapter(db)
            event_args = state['update_date_range_data']['arguments'].get('event_arguments', {})

            start_date = event_args.get('startDate')
            end_date = event_args.get('endDate')
            
            state['update_date_range_filtered_events'] = await adapter.get_events_by_date_range(state['user_id'], start_date, end_date)
            return state
    except Exception as e:
        state['update_date_range_filtered_events'] = []
        return state
        
    
@retry(
    wait=wait_random_exponential(min=1, max=10),
    stop=stop_after_attempt(2),
    retry=retry_if_exception_type(retryable_exceptions),
)
async def update_filter_event_agent(state: FlowState):
    if state['update_date_range_filtered_events']:
        template = PromptTemplate.from_template(UPDATE_FILTER_EVENT_AGENT_PROMPT)
        prompt_text = template.format(
                user_events=state['update_date_range_filtered_events']
            )
        if state["update_messages"] and isinstance(state["update_messages"][0], SystemMessage):
            state["update_messages"][0] = SystemMessage(content=prompt_text)
        else:
            state["update_messages"].insert(0, SystemMessage(content=prompt_text))
        response = [await model.ainvoke(state["update_messages"])]
        try:
            update_event_data = json.loads(response[0].content)
            
            if isinstance(update_event_data, list):
                events = []
                for event_dict in update_event_data:
                    try:
                        start_date = datetime.fromisoformat(event_dict.get('startDate')) 
                        end_date = datetime.fromisoformat(event_dict.get('endDate'))
                        
                        event = Event(
                            id=event_dict.get('id'),
                            title=event_dict.get('title'),
                            startDate=start_date,
                            endDate=end_date,
                            duration=event_dict.get('duration'),
                            location=event_dict.get('location'),
                            user_id=state['user_id']
                        )
                        events.append(event)
                    except Exception as e:
                        continue
                
                state['update_final_filtered_events'] = events
                state['update_arguments'] = state['update_date_range_data']['arguments'].get('update_arguments', {})
                
                if len(events) == 0:
                    state['update_messages'].append(AIMessage(content="Güncellenecek herhangi bir etkinlik bulunamadı"))
                else:
                    update_args = state['update_arguments']
                    if 'startDate' in update_args: # important: no need to add duration
                        try:
                            async with get_async_db_context_manager() as db:
                                adapter = EventAdapter(db)
                                start_date = datetime.fromisoformat(update_args['startDate'])
                                duration = update_args.get('duration', 0)
                                end_date = start_date + timedelta(minutes=duration)
                                
                                # Get event IDs to exclude from conflict check
                                event_ids_to_exclude = [event.id for event in events]
                                
                                conflict_event = await adapter.check_event_conflict(
                                    state['user_id'], 
                                    start_date, 
                                    end_date,
                                    exclude_event_id=event_ids_to_exclude[0] if len(event_ids_to_exclude) == 1 else None
                                )
                                state['update_conflict_event'] = conflict_event
                        except Exception as e:
                            state['update_messages'].append(AIMessage(content="Bir hata oluştu. Lütfen daha sonra tekrar deneyiniz."))
                            return state
                    
                    state['update_messages'].append(AIMessage(content="Güncellenmesini istediğiniz etkinlikleri aşağıda görebilirsiniz. Lütfen güncellemek istediğiniz etkinliği seçiniz."))
                    state['is_success'] = True
            else:
                state['update_messages'].append(AIMessage(content="Bir hata olustu. Lutfen daha sonra tekrar deneyiniz."))
        except Exception as e:
            state['update_messages'].append(AIMessage(content="Bir hata olustu. Lutfen daha sonra tekrar deneyiniz."))
    else:
        state['update_messages'].append(AIMessage(content="Güncellenecek herhangi bir etkinlik bulunamadı"))
    
    return state 