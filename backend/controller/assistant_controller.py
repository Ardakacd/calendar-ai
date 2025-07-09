import logging

from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from services.assistant_service import AssistantService, get_assistant_service
from models import ProcessInput
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/assistant", tags=["assistant"])
security = HTTPBearer()

@router.post("")
async def process(
        input: ProcessInput,
        credentials: HTTPAuthorizationCredentials = Depends(security),
        assistant_service: AssistantService = Depends(get_assistant_service)
):
    """
    Process users text message and return a response.
    """
    try:
        if len(input.text) == 0:
            raise HTTPException(status_code=400, detail="Text cannot be empty")

        token = credentials.credentials
        
        result = await assistant_service.process(token, input.text, input.current_datetime, input.weekday, input.days_in_month)

        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in process endpoint: {e}")
        raise HTTPException(status_code=500, detail="Failed to process the user message")


'''@router.post("/confirm")
async def confirm_action(
        confirmation_request: ConfirmationRequest,
        credentials: HTTPAuthorizationCredentials = Depends(security),
        transcribe_service: TranscribeService = Depends(get_transcribe_service)
):
    """
    Confirm and execute a calendar action (create, update, delete event).
    """
    try:
        # Get token from credentials
        token = credentials.credentials

        # Execute the confirmed action
        logger.info(f"Confirming action: {confirmation_request.action}")
        result = await transcribe_service.confirm_action(
            confirmation_request.action,
            confirmation_request.event_data,
            token
        )

        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in confirm action endpoint: {e}")
        raise HTTPException(status_code=500, detail="Failed to confirm action")'''
