import io
import logging
from config import settings
from fastapi import UploadFile, HTTPException, Depends
from openai import OpenAI
from services.event_service import get_event_service, EventService
from utils.jwt import verify_token

logger = logging.getLogger(__name__)


class TranscribeService:

    def __init__(self, event_service: EventService):
        self.event_service = event_service

    async def transcribe(self, token: str, audio_file: UploadFile) -> str:
        try:            
            verify_token(token)
            
            # Create OpenAI client and transcribe
            client = OpenAI(api_key=settings.OPENAI_API_KEY)
            logger.info("Starting audio transcription")

            # Read the uploaded file content
            content = await audio_file.read()

            # Create a BytesIO object for the OpenAI API
            audio_bytes = io.BytesIO(content)
            audio_bytes.name = audio_file.filename or "audio.wav"

            logger.info("Requesting transcription")

            transcription_text = client.audio.transcriptions.create(
                model="whisper-1",
                file=audio_bytes,
                response_format="text"
            )
            logger.info(f"Transcription completed: '{transcription_text}...'")
            return transcription_text

        except HTTPException as e:
            raise
        except Exception as e:
            logger.error(f"Error in transcribe service: {e}")
            raise Exception

def get_transcribe_service(
        event_service: EventService = Depends(get_event_service),
) -> TranscribeService:
    return TranscribeService(event_service)
