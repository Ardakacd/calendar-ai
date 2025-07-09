import logging
from fastapi import HTTPException, Depends
from services.event_service import get_event_service, EventService
from utils.jwt import get_user_id_from_token
from langchain_core.messages import HumanMessage
from flow.builder import FlowBuilder
logger = logging.getLogger(__name__)



class AssistantService:

    def __init__(self, event_service: EventService):
        self.event_service = event_service

    async def process(self, token: str, text: str, current_datetime: str, weekday: str, days_in_month: int) -> str:
        try:            
            user_id = get_user_id_from_token(token)
            flow = FlowBuilder().create_flow()
            response = await flow.ainvoke({
                "user_id": user_id, 
                "messages": [HumanMessage(content=text)], 
                "current_datetime": current_datetime, 
                "weekday": weekday, 
                "days_in_month": days_in_month
            })
            return response["messages"][-1].content
        except HTTPException as e:
            raise
        except Exception as e:
            logger.error(f"Error in process: {e}")
            raise Exception


def get_assistant_service(
        event_service: EventService = Depends(get_event_service),
) -> AssistantService:
    return AssistantService(event_service)
