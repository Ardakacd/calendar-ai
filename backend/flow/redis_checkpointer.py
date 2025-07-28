from langgraph.checkpoint.redis.aio import AsyncRedisSaver
from config import settings
import os
from dotenv import load_dotenv
load_dotenv(dotenv_path=f'.env.{settings.ENV}')

# dont forget ttl

async def get_checkpointer():
    checkpointer = None
    REDIS_URL = settings.redis_url  
    async with AsyncRedisSaver.from_conn_string(REDIS_URL) as _checkpointer:
        await _checkpointer.asetup()
        checkpointer = _checkpointer
    

    return checkpointer

