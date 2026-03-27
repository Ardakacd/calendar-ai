import logging

from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from services.assistant_service import AssistantService, get_assistant_service
from models import ProcessInput
from utils.jwt import get_user_id_from_token
from flow.builder import _checkpointer

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/assistant", tags=["assistant"])
security = HTTPBearer()


@router.delete("/memory")
async def reset_memory(
    credentials: HTTPAuthorizationCredentials = Depends(security),
):
    """Clear the conversation memory for the current user."""
    try:
        user_id = get_user_id_from_token(credentials.credentials)
        thread_id = str(user_id)
        # MemorySaver stores checkpoints in .storage dict keyed by thread_id
        _checkpointer.storage.pop(thread_id, None)
        _checkpointer.writes.pop(thread_id, None)
        return {"message": "Conversation memory cleared."}
    except Exception as e:
        logger.error(f"Error resetting memory: {e}")
        raise HTTPException(status_code=500, detail="Could not reset memory")


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
        raise HTTPException(status_code=500, detail="User message could not be processed")
