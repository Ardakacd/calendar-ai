from fastapi import Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse


async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """
    Handle Pydantic validation errors and return user-friendly Turkish messages
    """
    if exc.errors():
        error = exc.errors()[0]
        field = error.get('loc', ['unknown'])[-1]  
        error_type = error.get('type', '')
        
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
