from langchain_core.messages import SystemMessage, AIMessage
from langchain_core.prompts import PromptTemplate
from ..state import FlowState
from .prompt import ROUTER_AGENT_PROMPT
from ..llm import model
from tenacity import retry, stop_after_attempt, wait_random_exponential, retry_if_exception_type
from openai import OpenAIError, RateLimitError
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

    if state["router_messages"] and isinstance(state["router_messages"][0], SystemMessage):
        state["router_messages"][0] = SystemMessage(content=prompt_text)
    else:
        state["router_messages"].insert(0, SystemMessage(content=prompt_text))
    
    response = [await model.ainvoke(state["router_messages"])]
    
    # Parse the JSON response
    try:
        route_data = json.loads(response[0].content)
        state['route'] = route_data
    except json.JSONDecodeError:
        state['route'] = response[0].content
    
    return state

def route_action(state: FlowState):
    # create, delete, update, list agents removed from graph - route all to message handler
    # New architecture will use Scheduling Agent with tools instead
    if isinstance(state['route'], dict) and "route" in state['route']:
        route = state["route"]["route"]
        if route in ("create", "update", "delete", "list"):
            # Placeholder: route to message handler until Scheduling Agent is wired
            return "router_message_handler"
    return "router_message_handler"
        
def router_message_handler(state: FlowState):
    """Handle cases where router returns a message or when agents are not wired (create/update/delete/list)"""
    state['is_success'] = True
    route = state.get('route')
    if isinstance(route, dict) and route.get('route') in ('create', 'update', 'delete', 'list'):
        content = "Calendar operations are being migrated. This feature will be available soon."
    elif isinstance(route, str):
        content = route
    else:
        content = str(route) if route else "How can I help you with your calendar?"
    return {"router_messages": [AIMessage(content=content)]}