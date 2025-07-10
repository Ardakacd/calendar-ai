from langchain_core.messages import SystemMessage, AIMessage
from langchain_core.prompts import PromptTemplate
from ..state import FlowState
from .prompt import CREATE_EVENT_AGENT_PROMPT
from ..llm import model
from tenacity import retry, stop_after_attempt, wait_random_exponential, retry_if_exception_type
from openai import OpenAIError, RateLimitError
from langgraph.graph import END
import json

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
    response = [await model.ainvoke(state["messages"])]
    
    try:
        route_data = json.loads(response[0].content)
        state['create_data'] = route_data
    except json.JSONDecodeError:
        state['create_data'] = {"message": "Sorry, I couldn't understand your request. Please try again."}
    
    return state

def create_action(state: FlowState):
    print(state['create_data'])
    if "function" in state['create_data'] and "arguments" in state['create_data']:
        return END
    else:
        return "create_message_handler"
        
def create_message_handler(state: FlowState):

        """Handle cases where router returns a message instead of arguments"""
        return {"messages": [AIMessage(content=state["create_data"]["message"])]}