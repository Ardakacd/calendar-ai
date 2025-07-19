from langchain_core.messages import SystemMessage, AIMessage
from langchain_core.prompts import PromptTemplate
from ..state import FlowState
from .prompt import ROUTER_AGENT_PROMPT
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
async def router_agent(state: FlowState):
    template = PromptTemplate.from_template(ROUTER_AGENT_PROMPT)
    prompt_text = template.format()

    if state["messages"] and isinstance(state["messages"][0], SystemMessage):
        state["messages"][0] = SystemMessage(content=prompt_text)
    else:
        state["messages"].insert(0, SystemMessage(content=prompt_text))
    response = [await model.ainvoke(state["messages"])]
    
    # Parse the JSON response
    try:
        route_data = json.loads(response[0].content)
        state['route'] = route_data
    except json.JSONDecodeError:
        state['route'] = {"message": "Bir hata olustu. Lutfen daha sonra tekrar deneyiniz."}
    
    return state

def route_action(state: FlowState):
    if "route" in state['route']:
        route = state["route"]["route"]

        match route:
            case "create":
                return "create_agent"
            case "update":
                return "update_date_range_agent"
            case "delete":
                return "delete_date_range_agent"
            case "list":
                return "list_date_range_agent"
            case _:
                return 'router_message_handler'
    return 'router_message_handler'
        
def router_message_handler(state: FlowState):
    """Handle cases where router returns a message instead of a route"""
    message  = state["route"]["message"] if 'message' in state["route"] else 'Bir hata oluştu'
    return {"messages": [AIMessage(content=message)]}