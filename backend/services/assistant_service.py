import logging
from fastapi import HTTPException, Depends
from services.event_service import get_event_service, EventService
from utils.jwt import get_user_id_from_token
from langchain_core.messages import HumanMessage
from flow.builder import FlowBuilder
from langchain_core.runnables import RunnableConfig

logger = logging.getLogger(__name__)


class AssistantService:

    def __init__(self, event_service: EventService):
        self.event_service = event_service

    async def process(self, token: str, text: str, current_datetime: str, weekday: str, days_in_month: int):
        try:
            user_id = get_user_id_from_token(token)
            flow = await FlowBuilder().create_flow()
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

            # Scheduling operations (create, update, delete, list) use scheduling_result
            if route in ("create", "update", "delete", "list"):
                scheduling_result = response.get("scheduling_result") or {}
                message = scheduling_result.get("message", "Operation completed.")
                # Only send events to the frontend for LIST so the ListComponent renders.
                # CREATE/UPDATE also return event dicts but those should show as text confirmation.
                raw_events = scheduling_result.get("events") if route == "list" else None
                events = None
                if raw_events:
                    events = [
                        {**e, "id": e.get("id") or e.get("event_id")}
                        for e in raw_events
                    ]
                return {
                    "message": message,
                    "success": scheduling_result.get("success", True),
                    "has_conflict": scheduling_result.get("has_conflict", False),
                    "suggestions": scheduling_result.get("suggestions", []),
                    "events": events,
                }

            # Conversation response
            message = (
                response["router_messages"][-1].content
                if response.get("router_messages")
                else "How can I help you with your calendar?"
            )
            return {"message": message}

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error in process: {e}")
            raise


def get_assistant_service(
        event_service: EventService = Depends(get_event_service),
) -> AssistantService:
    return AssistantService(event_service)
