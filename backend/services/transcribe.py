from openai import OpenAI
from langchain_openai import ChatOpenAI
from config import settings
from langchain_core.prompts import PromptTemplate
from utils.constants import AGENT_PROMPT
from utils.jwt import get_user_id_from_token
from tenacity import retry, stop_after_attempt, wait_random_exponential, retry_if_exception_type
from openai import OpenAIError, RateLimitError
import logging
from services.event import get_event_service, EventService
from models import EventBase, EventUpdate, TranscribeResponse, EventConfirmationData
from fastapi import UploadFile, HTTPException, Depends
import io
import json
from utils.datetime import convert_datetime_string_to_datetime

logger = logging.getLogger(__name__)
retryable_exceptions = (OpenAIError, RateLimitError)



@retry(
    wait=wait_random_exponential(min=1, max=10),
    stop=stop_after_attempt(5),
    retry=retry_if_exception_type(retryable_exceptions),
)
async def invoke_llm(llm, user_events, transcription_text, current_datetime, weekday, days_in_month):

    prompt = PromptTemplate.from_template(AGENT_PROMPT)
    formatted_prompt = prompt.invoke({'user_events': user_events, 
                                      'transcription_text': transcription_text, 
                                      'current_datetime': current_datetime, 
                                      'weekday': weekday, 
                                      'days_in_month': days_in_month})
    # Get response from LLM
    result = await llm.ainvoke(formatted_prompt)
    
    print(f"LLM Response: {result.content}")
    
    # Try to parse JSON from response
    try:
        
        result = json.loads(result.content)
        return result
            
    except json.JSONDecodeError as e:
        print(f"JSON parsing error: {e}")
        return {
            "function": "none",
            "arguments": {},
            "message": "An error occurred."
        }

class TranscribeService:

    def __init__(self, event_service: EventService):
        self.event_service = event_service

    async def transcribe(self, audio_file: UploadFile, current_datetime: str, weekday: str, days_in_month: int, token: str):
        try:
            print(f"Current datetime: {current_datetime}, Weekday: {weekday}, Days in month: {days_in_month}")
            # Verify token and extract user_id using existing function
            logger.info("Verifying JWT token for transcribe request")
            user_id = get_user_id_from_token(token)
            logger.info(f"Token verified successfully for user: {user_id}")
            
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
                    datetime=event_args.get('datetime'),
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
                    datetime=event.datetime.isoformat(),
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
                    datetime=update_args.get('datetime', current_event.datetime.isoformat()),
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
                    'datetime': convert_datetime_string_to_datetime(event_data.datetime),
                    'duration': event_data.duration,
                    'location': event_data.location
                }
                await self.event_service.create_event(token, EventBase(**event_args))
                return {"message": f"Event '{event_data.title}' created successfully."}
                
            elif action == 'delete':
                await self.event_service.delete_event(token, event_data.event_id)
                return {"message": f"Event '{event_data.title}' deleted successfully."}
                
            elif action == 'update':
                event_id = event_data.event_id
                update_data = event_data.model_dump(exclude={"event_id"})

                await self.event_service.update_event(token, event_id, EventUpdate(**update_data))
                return {"message": f"Event '{event_data.title}' updated successfully."}
        except HTTPException as e:
            raise
        except Exception as e:
            logger.error(f"Error in confirm_action: {e}")
            raise Exception

def get_transcribe_service(
    event_service: EventService = Depends(get_event_service),
) -> TranscribeService:
    return TranscribeService(event_service)

        
        