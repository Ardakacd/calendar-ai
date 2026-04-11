import logging
import uvicorn
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from controller.event_controller import router as event_router
from controller.transcribe_controller import router as transcribe_router
from controller.assistant_controller import router as assistant_router
from controller.user_controller import router as auth_router
from controller.linq_controller import router as linq_router
from database import init_db
from exceptions.validation_exception_handler import validation_exception_handler
from services.morning_summary_service import send_morning_summaries
from services.reminder_service import send_event_reminders

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

scheduler = AsyncIOScheduler()


@asynccontextmanager
async def lifespan(app: FastAPI):
    scheduler.add_job(send_morning_summaries, "cron", minute=0)
    scheduler.add_job(send_event_reminders, "interval", minutes=5)
    scheduler.start()
    logger.info("APScheduler started — morning summary + reminder jobs registered")
    yield
    scheduler.shutdown(wait=False)
    logger.info("APScheduler shut down")


app = FastAPI(title="Calendar AI API", version="1.0.0", lifespan=lifespan)

logger.info("Starting Calendar AI API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

logger.info("CORS middleware configured")

app.add_exception_handler(RequestValidationError, validation_exception_handler)


app.include_router(auth_router)
logger.info("Authentication routes included")


app.include_router(event_router)
logger.info("Event routes included")


try:
    init_db()
    logger.info("Database initialized successfully")
except Exception as e:
    logger.error(f"Failed to initialize database: {e}", exc_info=True)
    raise

app.include_router(transcribe_router)
app.include_router(assistant_router)
app.include_router(linq_router)
logger.info("Linq iMessage routes included")


@app.get("/")
async def root():
    logger.info("Root endpoint accessed")
    return {"message": "Calendar AI API is running!"}


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
