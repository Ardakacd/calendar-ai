import logging

import uvicorn
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from controller.event_controller import router as event_router
from controller.transcribe_controller import router as transcribe_router
from controller.assistant_controller import router as assistant_router
from controller.user_controller import router as auth_router
from database import init_db

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = FastAPI(title="Calendar AI API", version="1.0.0")

logger.info("Starting Calendar AI API")

# CORS middleware for React Native app
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Change in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

logger.info("CORS middleware configured")

# Custom exception handler for validation errors
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """
    Handle Pydantic validation errors and return user-friendly Turkish messages
    """
    print(exc)
    # Get the first validation error
    if exc.errors():
        error = exc.errors()[0]
        field = error.get('loc', ['unknown'])[-1]  # Get the field name
        error_type = error.get('type', '')
        print(field)
        print(error_type)
        
        # Custom Turkish error messages based on field and error type
        if field == 'password' and error_type == 'string_too_short':
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={"detail": "Şifre en az 6 karakter olmalıdır"}
            )
        elif field == 'current_password' and error_type == 'string_too_short':
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={"detail": "Mevcut şifre en az 6 karakter olmalıdır"}
            )
        elif field == 'new_password' and error_type == 'string_too_short':
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={"detail": "Yeni şifre en az 6 karakter olmalıdır"}
            )
        elif field == 'email' and error_type == 'value_error':
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={"detail": "Geçersiz e-posta formatı"}
            )
        elif field == 'name' and error_type == 'missing':
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={"detail": "İsim alanı zorunludur"}
            )
        elif field == 'email' and error_type == 'missing':
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={"detail": "E-posta alanı zorunludur"}
            )
        elif field == 'password' and error_type == 'missing':
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={"detail": "Şifre alanı zorunludur"}
            )
    
    # Fallback for other validation errors
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={"detail": "Geçersiz veri formatı"}
    )

# Include authentication routes
app.include_router(auth_router)
logger.info("Authentication routes included")

# Include event routes
app.include_router(event_router)
logger.info("Event routes included")

# Initialize database
try:
    init_db()
    logger.info("Database initialized successfully")
except Exception as e:
    logger.error(f"Failed to initialize database: {e}", exc_info=True)
    raise

# Include transcribe routes
app.include_router(transcribe_router)
app.include_router(assistant_router)


@app.get("/")
async def root():
    logger.info("Root endpoint accessed")
    return {"message": "Calendar AI API is running!"}


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
