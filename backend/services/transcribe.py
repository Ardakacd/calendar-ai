from openai import OpenAI
from langchain_openai import ChatOpenAI
from config import settings
from langchain_core.prompts import PromptTemplate
from utils.constants import AGENT_PROMPT
from utils.jwt import get_user_id_from_token
from tenacity import retry, stop_after_attempt, wait_random_exponential, retry_if_exception_type
from openai import OpenAIError, RateLimitError
import logging
from adapter.event import EventAdapter
from models import EventCreate, EventUpdate
from fastapi import UploadFile, HTTPException
from database import get_async_db
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
            
            # Invoke LLM to get function call information
            # Get user events for context
            async for db in get_async_db():
                event_adapter = EventAdapter(db)
                user_events = await event_adapter.get_events_by_user_id(user_id)
                logger.info(f"Retrieved {len(user_events)} events for user {user_id}")
                logger.info(f"Invoking LLM for user: {user_id} with {len(user_events)} events")
                result = await invoke_llm(llm, user_events, transcription_text, current_datetime, weekday, days_in_month)

                if type(result) != dict:
                    raise ValueError("Invalid response from LLM")

                if result['function'] == 'create_event':
                    # Add user_id to arguments
                    event_args = result['arguments'].copy()
                    event_args['user_id'] = user_id
                    event_args['datetime'] = convert_datetime_string_to_datetime(event_args['datetime'])
                    await event_adapter.create_event(EventCreate(**event_args))
                elif result['function'] == 'remove_event':
                    event_id = result['arguments']['event_id']
                    await event_adapter.delete_event(event_id, user_id)
                elif result['function'] == 'update_event':
                    event_id = result['arguments']['event_id']
                    # Remove event_id from arguments for EventUpdate
                    update_args = result['arguments'].copy()
                    del update_args['event_id']
                    update_args['datetime'] = convert_datetime_string_to_datetime(update_args['datetime'])
                    await event_adapter.update_event(event_id, user_id, EventUpdate(**update_args))
                
            
            return result['message']
        except HTTPException as e:
            raise           
        except Exception as e:
            logger.error(f"Error in transcribe service: {e}")
            raise Exception
        

def get_transcribe_service() -> TranscribeService:
    return TranscribeService()

        
        