import logging

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from models import UserLogin, Token, RefreshTokenRequest, UserRegister
from services.user_service import UserService, get_user_service

# Configure logging
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["authentication"])
security = HTTPBearer()


@router.post("/login", response_model=Token)
async def login(user_credentials: UserLogin, user_service: UserService = Depends(get_user_service)):
    """
    Login user with email and password.
    
    Returns access token and refresh token.
    """
    logger.info(f"Login attempt for email: {user_credentials.email}")
    try:
        user = UserLogin(
            email=user_credentials.email,
            password=user_credentials.password
        )

        logger.debug(f"UserLogin object created: {user}")
        result = await user_service.login(user)
        logger.info(f"Login successful for email: {user_credentials.email}")
        return Token(**result)

    except HTTPException as e:
        logger.error(f"HTTP error during login for {user_credentials.email}: {e.detail}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error during login for {user_credentials.email}: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


@router.post("/register", response_model=Token)
async def register(user_data: UserRegister, user_service: UserService = Depends(get_user_service)):
    """
    Register a new user.
    
    Returns access token and refresh token.
    """
    logger.info(f"Registration attempt for email: {user_data.email}, name: {user_data.name}")
    logger.debug(f"UserRegister data received: {user_data}")

    try:
        result = await user_service.register(user_data)
        logger.info(f"Registration successful for email: {user_data.email}")
        return Token(**result)

    except HTTPException as e:
        logger.error(f"HTTP error during registration for {user_data.email}: {e.detail}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error during registration for {user_data.email}: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


@router.post("/refresh", response_model=Token)
async def refresh_token(refresh_request: RefreshTokenRequest, user_service: UserService = Depends(get_user_service)):
    """
    Refresh access token using refresh token.
    
    Returns new access token and refresh token.
    """
    logger.info("Token refresh attempt")
    try:
        result = await user_service.refresh_token(refresh_request)
        print(result)
        logger.info("Token refresh successful")
        return Token(**result)

    except HTTPException as e:
        logger.error(f"HTTP error during token refresh: {e.detail}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error during token refresh: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


@router.post("/logout")
async def logout(credentials: HTTPAuthorizationCredentials = Depends(security),
                 user_service: UserService = Depends(get_user_service)):
    """
    Logout user by invalidating the token.
    """
    logger.info("Logout attempt")
    try:
        token = credentials.credentials
        result = await user_service.logout(token)
        logger.info("Logout successful")
        return result

    except HTTPException as e:
        logger.error(f"HTTP error during logout: {e.detail}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error during logout: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


@router.get("/me")
async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security),
                           user_service: UserService = Depends(get_user_service)):
    """
    Get current user information.
    """
    logger.info("Get current user attempt")
    try:
        token = credentials.credentials
        result = await user_service.get_user(token)
        logger.info("Get current user successful")
        return result

    except HTTPException as e:
        logger.error(f"HTTP error during get current user: {e.detail}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error during get current user: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )
