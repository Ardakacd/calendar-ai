import io
import json
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
            '''

            # Set up LLM
            llm = ChatOpenAI(model='gpt-3.5-turbo', temperature=0.2, api_key=settings.OPENAI_API_KEY)

            user_events = await self.event_service.get_user_events(token)
            logger.info(f"Retrieved {len(user_events)} events for user {user_id}")
            logger.info(f"Invoking LLM for user: {user_id} with {len(user_events)} events")
            result = await invoke_llm(llm, user_events, transcription_text, current_datetime, weekday, days_in_month)

            if type(result) != dict or 'function' not in result or 'arguments' not in result:
                raise ValueError("Invalid response from LLM")

            # Instead of executing functions directly, return the data for confirmation
            if result['function'] == 'create_event':
                event_args = result['arguments'].copy()
                confirmation_data = EventConfirmationData(
                    title=event_args.get('title'),
                    startDate=event_args.get('datetime'),
                    duration=event_args.get('duration'),
                    location=event_args.get('location')
                )

                return TranscribeResponse(
                    message=result.get('message', 'Please confirm the event details below.'),
                    action='create',
                    requires_confirmation=True,
                    confirmation_data=confirmation_data.model_dump()
                )

            elif result['function'] == 'remove_event':
                event_id = result['arguments']['event_id']

                # Get the event details for confirmation
                event = await self.event_service.get_event(token, event_id)

                confirmation_data = EventConfirmationData(
                    title=event.title,
                    startDate=event.startDate.isoformat(),
                    duration=event.duration,
                    location=event.location,
                    event_id=event_id
                )

                return TranscribeResponse(
                    message=result.get('message', 'Please confirm that you want to delete this event.'),
                    action='delete',
                    requires_confirmation=True,
                    confirmation_data=confirmation_data.model_dump()
                )

            elif result['function'] == 'update_event':
                update_args = result['arguments'].copy()
                event_id = update_args['event_id']

                # Get the current event details
                current_event = await self.event_service.get_event(token, event_id)
                # Merge current data with updates
                confirmation_data = EventConfirmationData(
                    title=update_args.get('title', current_event.title),
                    startDate=update_args.get('datetime', current_event.startDate.isoformat()),
                    duration=update_args.get('duration', current_event.duration),
                    location=update_args.get('location', current_event.location),
                    event_id=event_id
                )

                return TranscribeResponse(
                    message=result.get('message', 'Please confirm the updated event details below.'),
                    action='update',
                    requires_confirmation=True,
                    confirmation_data=confirmation_data.model_dump()
                )
            else:
                # For queries or other actions that don't require confirmation
                return TranscribeResponse(
                    message=result.get('message', 'No action required.'),
                    action='none',
                    requires_confirmation=False
                )

        except HTTPException as e:
            raise
        except Exception as e:
            logger.error(f"Error in transcribe service: {e}")
            raise Exception

    async def confirm_action(self, action: str, event_data: EventConfirmationData, token: str):
        """Execute the confirmed action"""
        try:
            if action == 'create':
                event_args = {
                    'title': event_data.title,
                    'startDate': convert_datetime_string_to_datetime(event_data.startDate),
                    'duration': event_data.duration,
                    'location': event_data.location
                }
                await self.event_service.create_event(token, EventCreate(**event_args))
                return {"message": f"Event '{event_data.title}' created successfully."}

            elif action == 'delete':
                await self.event_service.delete_event(token, event_data.event_id)
                return {"message": f"Event '{event_data.title}' deleted successfully."}

            elif action == 'update':
                event_id = event_data.event_id
                update_data = event_data.model_dump(exclude={"event_id"})

                await self.event_service.update_event(token, event_id, EventUpdate(**update_data))
                return {"message": f"Event '{event_data.title}' updated successfully."}'''
        except HTTPException as e:
            raise
        except Exception as e:
            logger.error(f"Error in confirm_action: {e}")
            raise Exception


def get_transcribe_service(
        event_service: EventService = Depends(get_event_service),
) -> TranscribeService:
    return TranscribeService(event_service)
