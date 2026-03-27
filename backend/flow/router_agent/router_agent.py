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

    # Build message list locally — do not mutate state
    existing = [m for m in state.get("router_messages", []) if not isinstance(m, SystemMessage)]
    messages = [SystemMessage(content=prompt_text)] + existing

    response = await model.ainvoke(messages)

    # Parse the JSON response
    try:
        route_data = json.loads(response.content)
    except json.JSONDecodeError:
        route_data = response.content

    return {"route": route_data}

def route_action(state: FlowState):
    if isinstance(state['route'], dict) and "route" in state['route']:
        route = state["route"]["route"]
        if route in ("create", "update", "delete", "list"):
            return "scheduling_agent"
        if route == "leisure_search":
            return "leisure_search_agent"
    return "router_message_handler"
        
def router_message_handler(state: FlowState):
    """Handle conversation responses from the router."""
    route = state.get('route')
    if isinstance(route, str):
        content = route
    else:
        content = str(route) if route else "How can I help you with your calendar?"
    return {"router_messages": [AIMessage(content=content)], "is_success": True}