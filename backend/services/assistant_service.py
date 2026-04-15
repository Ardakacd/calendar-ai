import logging
from fastapi import HTTPException, Depends
from services.event_service import get_event_service, EventService
from utils.jwt import get_user_id_from_token
from langchain_core.messages import HumanMessage
from flow.builder import FlowBuilder
from langchain_core.runnables import RunnableConfig

logger = logging.getLogger(__name__)

# Module-level compiled-graph cache — avoids rebuilding on every request.
_compiled_flow = None


class AssistantService:

    def __init__(self, event_service: EventService):
        self.event_service = event_service

    async def process(self, token: str, text: str, current_datetime: str, weekday: str, days_in_month: int):
        user_id = get_user_id_from_token(token)
        return await self.process_for_user(user_id, text, current_datetime, weekday, days_in_month)

    async def process_for_user(self, user_id: int, text: str, current_datetime: str, weekday: str, days_in_month: int):
        try:
            global _compiled_flow
            if _compiled_flow is None:
                _compiled_flow = await FlowBuilder().create_flow()
            flow = _compiled_flow
            config: RunnableConfig = {'configurable': {'thread_id': str(user_id)}}

            response = await flow.ainvoke({
                "user_id": user_id,
                "router_messages": [HumanMessage(content=text)],
                "input_text": text,
                "current_datetime": current_datetime,
                "weekday": weekday,
                "days_in_month": days_in_month,
            }, config=config)

            route = response["route"].get('route') if isinstance(response["route"], dict) else None

            if route in ("create", "update", "delete", "list"):
                scheduling_result = response.get("scheduling_result") or {}
                message = scheduling_result.get("message") or "Operation completed."
                needs_clarification = scheduling_result.get("needs_clarification", False)

                if route == "list":
                    raw_events = scheduling_result.get("events")
                elif route == "delete" and needs_clarification:
                    raw_events = scheduling_result.get("candidate_events")
                elif route in ("create", "update"):
                    raw_events = scheduling_result.get("events")
                else:
                    raw_events = None

                events = None
                if raw_events:
                    events = [
                        {**e, "id": e.get("id") or e.get("event_id")}
                        for e in raw_events
                    ]
                return {
                    "type": route,
                    "message": message,
                    "success": scheduling_result.get("success", True),
                    "has_conflict": scheduling_result.get("has_conflict", False),
                    "needs_clarification": needs_clarification,
                    "suggestions": scheduling_result.get("suggestions", []),
                    "events": events,
                }

            last_msg = response.get("router_messages", [])
            if last_msg:
                content = last_msg[-1].content
                # content can be a list when the message has tool calls
                if isinstance(content, list):
                    text_parts = [p.get("text", "") for p in content if isinstance(p, dict) and p.get("type") == "text"]
                    message = " ".join(text_parts).strip()
                else:
                    message = str(content).strip()
            else:
                message = ""

            logger.debug(f"Router fallback message: {repr(message)}")
            return {"message": message or "How can I help you with your calendar?"}

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error in process_for_user: {e}")
            raise


def get_assistant_service(
        event_service: EventService = Depends(get_event_service),
) -> AssistantService:
    return AssistantService(event_service)
