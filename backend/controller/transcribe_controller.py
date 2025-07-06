import logging

from fastapi import APIRouter, Depends, File, Form, UploadFile, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from models import ConfirmationRequest
from services.transcribe_service import TranscribeService, get_transcribe_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/transcribe", tags=["transcribe"])
security = HTTPBearer()


@router.post("")
async def transcribe(
        audio: UploadFile = File(...),
        current_datetime: str = Form(...),
        weekday: str = Form(...),
        days_in_month: int = Form(...),
        credentials: HTTPAuthorizationCredentials = Depends(security),
        transcribe_service: TranscribeService = Depends(get_transcribe_service)
):
    """
    Transcribe audio file and process calendar commands.
    """
    try:
        # Validate file type
        if not audio.content_type or not audio.content_type.startswith('audio/'):
            raise HTTPException(status_code=400, detail="File must be an audio file")

        # Get token from credentials
        token = credentials.credentials

        # Process the audio file directly
        logger.info(f"Processing audio file: {audio.filename}")
        result = await transcribe_service.transcribe(audio, current_datetime, weekday, days_in_month, token)

        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in transcribe endpoint: {e}")
        raise HTTPException(status_code=500, detail="Failed to process the audio")


@router.post("/confirm")
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
        raise HTTPException(status_code=500, detail="Failed to confirm action")
