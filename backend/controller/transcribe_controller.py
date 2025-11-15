import logging

from fastapi import APIRouter, Depends, File, UploadFile, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from models import TranscribeMessage
from services.transcribe_service import TranscribeService, get_transcribe_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/transcribe", tags=["transcribe"])
security = HTTPBearer()


@router.post("")
async def transcribe(
        audio: UploadFile = File(...),
        credentials: HTTPAuthorizationCredentials = Depends(security),
        transcribe_service: TranscribeService = Depends(get_transcribe_service)
) -> TranscribeMessage:
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
        result = await transcribe_service.transcribe(token, audio)

        return TranscribeMessage(message=result)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in transcribe endpoint: {e}")
        raise HTTPException(status_code=500, detail="Audio could not be processed")
