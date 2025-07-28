import logging
from fastapi import HTTPException, Depends
from services.event_service import get_event_service, EventService
from utils.jwt import get_user_id_from_token
from langchain_core.messages import HumanMessage
from flow.builder import FlowBuilder
from models import SuccessfulListResponse, SuccessfulDeleteResponse, SuccessfulCreateResponse, SuccessfulUpdateResponse, EventCreate
from langchain_core.runnables import RunnableConfig
logger = logging.getLogger(__name__)



class AssistantService:

    def __init__(self, event_service: EventService):
        self.event_service = event_service

    async def process(self, token: str, text: str, current_datetime: str, weekday: str, days_in_month: int):
        try:            
            user_id = get_user_id_from_token(token)
            flow = await FlowBuilder().create_flow()
            config: RunnableConfig = {'thread_id': user_id}
            
            response = await flow.ainvoke({
                "user_id": user_id, 
                "messages": [HumanMessage(content=text)], 
                "current_datetime": current_datetime, 
                "weekday": weekday, 
                "days_in_month": days_in_month
            }, config=config)
            route = response["route"].get('route') if isinstance(response["route"], dict) else None
            is_success = response["is_success"]

            if is_success:
                if route == "create":
                    create_event_data = response["create_event_data"]
                    events = [EventCreate(
                        title=event_data.get("arguments").get("title"),
                        startDate=event_data.get("arguments").get("startDate"),
                        duration=event_data.get("arguments", {}).get("duration"),
                        location=event_data.get("arguments", {}).get("location")
                    ) for event_data in create_event_data]
                    create_response = SuccessfulCreateResponse(
                        message=response["messages"][-1].content, 
                        events=events,
                        conflict_events=response["create_conflict_events"]
                    )
                    return create_response.model_dump()
                elif route == "update":
                    update_response = SuccessfulUpdateResponse(
                        message=response["messages"][-1].content, 
                        events=response["update_final_filtered_events"],
                        update_arguments=response["update_arguments"],
                        update_conflict_event=response["update_conflict_event"]
                    )
                    return update_response.model_dump()
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
