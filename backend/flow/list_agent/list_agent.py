from langchain_core.messages import SystemMessage, AIMessage
from langchain_core.prompts import PromptTemplate
from ..state import FlowState
from .prompt import LIST_EVENT_AGENT_PROMPT
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
async def list_agent(state: FlowState):
    
    template = PromptTemplate.from_template(LIST_EVENT_AGENT_PROMPT)
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
        state['list_data'] = route_data
    except json.JSONDecodeError:
        state['list_data'] = {"message": "Sorry, I couldn't understand your request. Please try again."}
    
    return state

def list_action(state: FlowState):
    print(state['list_data'])
    if "function" in state['list_data'] and "arguments" in state['list_data']:
        return END
    else:
        return "list_message_handler"
        
def list_message_handler(_: FlowState):
        """Handle cases where router returns a message instead of arguments"""
        return {"messages": [AIMessage(content="An error occurred while listing events. Please try again.")]}