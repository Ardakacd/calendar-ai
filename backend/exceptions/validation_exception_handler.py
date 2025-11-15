from fastapi import Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse


async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """
    Handle Pydantic validation errors and return user-friendly English messages
    """
    if exc.errors():
        error = exc.errors()[0]
        field = error.get('loc', ['unknown'])[-1]  
        error_type = error.get('type', '')
        
        if field == 'password' and error_type == 'string_too_short':
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={"detail": "Password must be at least 6 characters"}
            )
        elif field == 'current_password' and error_type == 'string_too_short':
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={"detail": "Current password must be at least 6 characters"}
            )
        elif field == 'new_password' and error_type == 'string_too_short':
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={"detail": "New password must be at least 6 characters"}
            )
        elif field == 'email' and error_type == 'value_error':
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={"detail": "Invalid email format"}
            )
        elif field == 'name' and error_type == 'missing':
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={"detail": "Name field is required"}
            )
        elif field == 'email' and error_type == 'missing':
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={"detail": "Email field is required"}
            )
        elif field == 'password' and error_type == 'missing':
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={"detail": "Password field is required"}
            )
    
    # Fallback for other validation errors
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={"detail": "Invalid data format"}
    )
