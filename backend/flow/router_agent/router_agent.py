import logging
from langchain_core.messages import SystemMessage, AIMessage
from langchain_core.prompts import PromptTemplate
from ..state import FlowState
from .prompt import ROUTER_AGENT_PROMPT
from ..llm import model
from tenacity import retry, stop_after_attempt, wait_random_exponential, retry_if_exception_type
from openai import OpenAIError, RateLimitError
from ..trim_utils import trim_messages
import json

retryable_exceptions = (OpenAIError, RateLimitError)
logger = logging.getLogger(__name__)

# Phrases that indicate the LLM hallucinated executing a calendar action instead of routing
_HALLUCINATION_MARKERS = {
    "checking for conflicts",
    "i've updated", "i have updated", "i'll update",
    "i've created", "i have created", "i'll create",
    "i've deleted", "i have deleted", "i'll delete",
    "i've scheduled", "i have scheduled",
    "i've moved", "i have moved",
}


def _infer_route_from_input(input_text: str) -> str | None:
    """Infer calendar operation from user message keywords as a hallucination fallback."""
    t = input_text.lower()
    if any(kw in t for kw in ("move", "reschedule", "update", "change", "shift", "push", "postpone", "rename", "edit")):
        return "update"
    if any(kw in t for kw in ("cancel", "delete", "remove")):
        return "delete"
    if any(kw in t for kw in ("add", "create", "book", "schedule", "set up")):
        return "create"
    if any(kw in t for kw in ("list", "show", "what do i have", "what's on", "what events")):
        return "list"
    return None


@retry(
    wait=wait_random_exponential(min=1, max=10),
    stop=stop_after_attempt(3),
    retry=retry_if_exception_type(retryable_exceptions),
)
async def router_agent(state: FlowState):
    template = PromptTemplate.from_template(ROUTER_AGENT_PROMPT)
    prompt_text = template.format()

    # Build message list locally — do not mutate state
    # Token-aware trim: keep last ~4000 tokens of conversation history
    existing = trim_messages(
        state.get("router_messages", []),
        max_tokens=4000,
        start_on="human",
        include_system=False,
    )

    # Inject conversation summary if available (from summarization node)
    summary = state.get("conversation_summary", "")
    if summary:
        prompt_text = prompt_text + f"\n\n## Previous conversation context\n{summary}"

    messages = [SystemMessage(content=prompt_text)] + existing

    response = await model.ainvoke(messages)

    # Parse the JSON response
    try:
        route_data = json.loads(response.content)
    except json.JSONDecodeError:
        # LLM returned a plain string instead of JSON.
        # Check if it's a hallucinated action confirmation (e.g. "Updating lunch with Sarah...")
        response_lower = response.content.lower()
        is_hallucinated = any(marker in response_lower for marker in _HALLUCINATION_MARKERS)

        if is_hallucinated:
            inferred = _infer_route_from_input(state.get("input_text", ""))
            if inferred:
                logger.warning(
                    f"Router hallucination detected — inferred route={inferred!r} "
                    f"from input={state.get('input_text')!r}"
                )
                route_data = {"route": inferred}
            else:
                # Can't infer — treat as conversation so user gets a response
                route_data = response.content
        else:
            route_data = response.content

    # Capture the OLD route as previous_route BEFORE writing the new one.
    # Downstream nodes (scheduling_agent) use this to detect topic changes across turns.
    old_route = state.get('route', {})
    old_route_name = old_route.get('route') if isinstance(old_route, dict) else None

    return {"route": route_data, "previous_route": old_route_name}

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
    return {
        "router_messages": [AIMessage(content=content)],
        "is_success": True,
        # Clear any stale scheduling state from prior turns
        "scheduling_operation": None,
        "scheduling_event_data": None,
        "scheduling_result": None,
        "conflict_check_request": None,
        "conflict_check_result": None,
    }