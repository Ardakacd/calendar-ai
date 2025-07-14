import logging
from fastapi import HTTPException, Depends
from services.event_service import get_event_service, EventService
from utils.jwt import get_user_id_from_token
from langchain_core.messages import HumanMessage
from flow.builder import FlowBuilder
from models import SuccessfulListResponse, SuccessfulDeleteResponse, SuccessfulCreateResponse, EventCreate
logger = logging.getLogger(__name__)



class AssistantService:

    def __init__(self, event_service: EventService):
        self.event_service = event_service

    async def process(self, token: str, text: str, current_datetime: str, weekday: str, days_in_month: int):
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
            route = response["route"]["route"]
            is_success = response["is_success"]

            if is_success:
                if route == "create":
                    arguments = response["create_event_data"]["arguments"]
                    event = EventCreate(
                        title=arguments.get("title"),
                        startDate=arguments.get("startDate"),
                        duration=arguments.get("duration"),
                        location=arguments.get("location")
                    )
                    create_response = SuccessfulCreateResponse(
                        message=response["messages"][-1].content, 
                        event=event
                    )
                    return create_response.model_dump()
                elif route == "update":
                    return response["messages"][-1].content
                elif route == "delete":
                    delete_response = SuccessfulDeleteResponse(
                        message=response["messages"][-1].content, 
                        events=response["delete_final_filtered_events"]
                    )
                    return delete_response.model_dump()
                elif route == "list":
                    list_response = SuccessfulListResponse(
                        message=response["messages"][-1].content, 
                        events=response["list_final_filtered_events"]
                    )
                    return list_response.model_dump()
            else:
                return {"message": response["messages"][-1].content}
        except HTTPException as e:
            raise
        except Exception as e:
            logger.error(f"Error in process: {e}")
            raise


def get_assistant_service(
        event_service: EventService = Depends(get_event_service),
) -> AssistantService:
    return AssistantService(event_service)
