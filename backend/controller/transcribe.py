from fastapi import APIRouter, Depends, File, Form, UploadFile, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from services.transcribe import TranscribeService, get_transcribe_service
import logging

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
    
 