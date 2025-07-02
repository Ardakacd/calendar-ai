from fastapi import Depends, HTTPException, status
from models import User, RefreshTokenRequest, UserRegister, UserLogin
from adapter.user import UserAdapter
from utils.jwt import create_access_token, create_refresh_token, verify_token, verify_refresh_token
from utils.password import verify_password, get_password_hash
from config import settings
import uuid
import logging
from database.config import get_async_db
from sqlalchemy.ext.asyncio import AsyncSession

# Configure logging
logger = logging.getLogger(__name__)

class UserService:
    def __init__(self, user_adapter: UserAdapter):
        self.user_adapter = user_adapter

    async def login(self, user: UserLogin):
        logger.info(f"UserService: Login attempt for email: {user.email}")
        try:
            db_user = await self.user_adapter.get_user_by_email(user.email)
            if not db_user:
                logger.warning(f"UserService: Login failed - user not found for email: {user.email}")
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Incorrect email or password"
                )
            
            if not verify_password(user.password, db_user.password):
                logger.warning(f"UserService: Login failed - incorrect password for email: {user.email}")
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Incorrect email or password"
                )
        
                        
            access_token = create_access_token(
                data={"user_id": db_user.id}
            )
            
            refresh_token = create_refresh_token(
                data={"user_id": db_user.id}
            )
            
            return {
                "access_token": access_token,
                "refresh_token": refresh_token,
                "token_type": "bearer",
                "user_id": db_user.id,
                "user_name": db_user.name,
                "expires_in": settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60  # Convert to seconds
            }
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"UserService: Unexpected error during login for {user.email}: {str(e)}", exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Internal server error"
            )

    async def register(self, user: UserRegister):
        logger.info(f"UserService: Registration attempt for email: {user.email}, name: {user.name}")
        try: 
            hashed_password = get_password_hash(user.password)
            logger.debug(f"UserService: Password hashed successfully for email: {user.email}")

            user_id = str(uuid.uuid4())
            logger.debug(f"UserService: Generated user ID: {user_id}")
            
            user_data = User(
                id=user_id,
                name=user.name,
                email=user.email,
                password=hashed_password
            )
            
            logger.debug(f"UserService: User object created: {user_data}")
            await self.user_adapter.create_user(user_data)
            logger.info(f"UserService: User created successfully in database: {user_id}")
            
            access_token = create_access_token(
                data={"user_id": user_id}
            )
            
            refresh_token = create_refresh_token(
                data={"user_id": user_id}
            )
            
            logger.info(f"UserService: Registration successful for user: {user_id}")
            
            return {
                "access_token": access_token,
                "refresh_token": refresh_token,
                "token_type": "bearer",
                "user_id": user_id,
                "user_name": user.name,
                "expires_in": settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60  # Convert to seconds
            }
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"UserService: Unexpected error during registration for {user.email}: {str(e)}", exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Internal server error"
            )

    async def refresh_token(self, refresh_request: RefreshTokenRequest):
        try:
            # Verify the refresh token
            print(refresh_request.refresh_token)
            token_data = verify_refresh_token(refresh_request.refresh_token)
            user_id = token_data.user_id
            
            # Check if user still exists
            user = await self.user_adapter.get_user_by_id(user_id)
            if not user:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="User not found"
                )
            print(user_id)
            
            # Create new access token
            access_token = create_access_token(
                data={"user_id": user_id}
            )
            print('geldi')
            
            # Create new refresh token (optional - you can reuse the old one)
            new_refresh_token = create_refresh_token(
                data={"user_id": user_id}
            )
            print(access_token)
            print(new_refresh_token)
            print(user_id)
            print(user.name)
            print(settings.ACCESS_TOKEN_EXPIRE_MINUTES)
            
            return {
                "access_token": access_token,
                "refresh_token": new_refresh_token,
                "token_type": "bearer",
                "user_id": user_id,
                "user_name": user.name,
                "expires_in": settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60  # Convert to seconds
            }
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Internal server error"
            )

    async def logout(self, token: str):
        try:
            verify_token(token)
            return {"message": "User logged out successfully"}
        except HTTPException:
            raise
        except Exception:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Internal server error"
            )

    async def get_user(self, token: str):
        try:
            token_data = verify_token(token)
            user_id = token_data.user_id
            
            user = await self.user_adapter.get_user_by_id(user_id)
            if not user:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="User not found"
                )
            
            return {
                "id": user.id,
                "name": user.name,
                "email": user.email
            }
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Internal server error"
            )

    async def update_user(self, token: str, user: User):
        try:
            token_data = verify_token(token)
            user_id = token_data.user_id
            
            
            existing_user = await self.user_adapter.get_user_by_id(user_id)
            if not existing_user:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="User not found"
                )
            
            
            hashed_password = get_password_hash(user.password) if user.password else existing_user.password
            
            
            user_data = User(
                id=user_id,
                name=existing_user.name,
                email=existing_user.email,
                password=hashed_password
            )
            
            await self.user_adapter.update_user(user_id, user_data)
            
            return {"message": "User updated successfully"}
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Internal server error"
            )

    async def delete_user(self, token: str):
        try:
            
            token_data = verify_token(token)
            user_id = token_data.user_id
            
            existing_user = await self.user_adapter.get_user_by_id(user_id)
            if not existing_user:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="User not found"
                )
            
            await self.user_adapter.delete_user(user_id)
            
            return {"message": "User deleted successfully"}
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Internal server error"
            ) 
        
def get_user_service(
    db: AsyncSession = Depends(get_async_db),
) -> UserService:
    user_adapter = UserAdapter(db)
    return UserService(user_adapter)


