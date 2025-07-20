from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import SQLAlchemyError, IntegrityError
from sqlalchemy import select, delete, update
import logging
from database import UserModel
from models import UserCreate, UserUpdate, User
from fastapi import HTTPException
logger = logging.getLogger(__name__)


class UserAdapter:
    """
    User adapter for database operations.
    
    This adapter provides async interface for user CRUD operations
    with proper error handling and session management.
    """
    
    def __init__(self, session: AsyncSession):
        self.db: AsyncSession = session
    
    def _convert_to_model(self, user_model: UserModel) -> User:
        """Convert UserModel to User Pydantic model."""
        logger.debug(f"UserAdapter: Converting UserModel to User: {user_model.id}")
        return User(
            id=user_model.id,
            user_id=user_model.user_id,
            name=user_model.name,
            email=user_model.email,
            password=user_model.password
        )
    
    def _convert_to_db_model(self, user_data: UserCreate) -> UserModel:
        """Convert UserCreate Pydantic model to UserModel."""
        logger.debug(f"UserAdapter: Converting UserCreate to UserModel: {user_data.name}")
        return UserModel(
            user_id=user_data.user_id,
            name=user_data.name,
            email=user_data.email,
            password=user_data.password
        )
       
    def _handle_integrity_error(self, e: IntegrityError, operation: str) -> None:
        """
        Handle integrity errors with specific error messages.
        
        Args:
            e: IntegrityError exception
            operation: Operation being performed (create, update)
            
        Raises:
            HTTPException: With specific error message
        """
        error_msg = str(e).lower()
        
        if "email" in error_msg and "unique" in error_msg:
            raise HTTPException(status_code=400, detail="Bu e-posta adresi zaten kullanımda")
        elif "password" in error_msg and "length" in error_msg:
            raise HTTPException(status_code=400, detail="Şifre en az 6 karakter olmalıdır")
        elif "email" in error_msg and "format" in error_msg:
            raise HTTPException(status_code=400, detail="Geçersiz e-posta formatı")
        else:
            raise HTTPException(status_code=500, detail=f"Veri doğrulama hatası: {operation}")
    
    async def create_user(self, user_data: UserCreate) -> Optional[User]:
        """
        Create a new user.
        
        Args:
            user_data: User data to create
            
        Returns:
            Created user or None if failed
            
        Raises:
            ValueError: If validation fails (email exists, password too short, etc.)
        """
        logger.info(f"UserAdapter: Creating user with email: {user_data.email}")
        try:
            db_user = self._convert_to_db_model(user_data)
            logger.debug(f"UserAdapter: UserModel created: {db_user.id}")
            
            self.db.add(db_user)
            logger.debug(f"UserAdapter: User added to session")
            
            await self.db.commit()
            logger.info(f"UserAdapter: User created successfully: {db_user.id}")
            
            return self._convert_to_model(db_user)
            
        except HTTPException as e:
            logger.error(f"UserAdapter: Http error creating user {user_data.email}: {e}")
            raise
        except IntegrityError as e:
            logger.error(f"UserAdapter: Integrity error creating user {user_data.email}: {e}")
            await self.db.rollback()
            self._handle_integrity_error(e, "create")
        except SQLAlchemyError as e:
            logger.error(f"UserAdapter: Database error creating user {user_data.email}: {e}")
            await self.db.rollback()
            return None
        except Exception as e:
            logger.error(f"UserAdapter: Unexpected error creating user {user_data.email}: {e}", exc_info=True)
            await self.db.rollback()
            return None
    
    async def get_user_by_id(self, user_id: int) -> Optional[User]:
        """
        Get user by internal ID.
        
        Args:
            user_id: Internal user ID to retrieve
            
        Returns:
            User or None if not found
        """
        try:
            stmt = select(UserModel).where(UserModel.id == user_id)
            result = await self.db.execute(stmt)
            db_user = result.scalar_one_or_none()
            
            if db_user:
                return self._convert_to_model(db_user)
            return None
            
        except SQLAlchemyError as e:
            logger.error(f"Database error retrieving user {user_id}: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error retrieving user {user_id}: {e}")
            return None
       
    async def get_user_by_email(self, email: str) -> Optional[User]:
        """
        Get user by email.
        
        Args:
            email: Email to search for
            
        Returns:
            User or None if not found
        """
        logger.info(f"UserAdapter: Looking up user by email: {email}")
        try:
            stmt = select(UserModel).where(UserModel.email == email)
            result = await self.db.execute(stmt)
            db_user = result.scalar_one_or_none()
            
            if db_user:
                return self._convert_to_model(db_user)
            else:
                logger.warning(f"UserAdapter: No user found for email: {email}")
                return None
            
        except SQLAlchemyError as e:
            logger.error(f"UserAdapter: Database error retrieving user by email {email}: {e}")
            return None
        except Exception as e:
            logger.error(f"UserAdapter: Unexpected error retrieving user by email {email}: {e}", exc_info=True)
            return None
    
    async def update_user(self, user_id: int, user_data: UserUpdate) -> Optional[User]:
        """
        Update an existing user efficiently.
        
        Args:
            user_id: Internal user ID to update
            user_data: Updated user data
            
        Returns:
            Updated user or None if failed
            
        Raises:
            ValueError: If validation fails (email exists, password too short, etc.)
        """
        try:
            # Build update data
            update_data = user_data.model_dump(exclude_unset=True)
            if not update_data:
                logger.warning(f"No fields to update for user {user_id}")
                return await self.get_user_by_id(user_id)
            
            
            # Direct update operation
            stmt = update(UserModel).where(UserModel.id == user_id).values(**update_data)
            result = await self.db.execute(stmt)
            
            if result.rowcount == 0:
                logger.warning(f"User {user_id} not found for update")
                return None
            
            await self.db.commit()
            logger.info(f"Updated user: {user_id}")
            
            return await self.get_user_by_id(user_id)
            
        except HTTPException as e:
            logger.error(f"UserAdapter: Http error updating user {user_id}: {e}")
            raise
        except IntegrityError as e:
            logger.error(f"UserAdapter: Integrity error updating user {user_id}: {e}")
            await self.db.rollback()
            self._handle_integrity_error(e, "update")
        except SQLAlchemyError as e:
            logger.error(f"UserAdapter: Database error updating user {user_id}: {e}")
            await self.db.rollback()
            return None
        except Exception as e:
            logger.error(f"UserAdapter: Unexpected error updating user {user_id}: {e}", exc_info=True)
            await self.db.rollback()
            return None
    
    async def delete_user(self, user_id: int) -> bool:
        """
        Delete a user.
        
        Args:
            user_id: Internal user ID to delete
            
        Returns:
            True if deleted, False if failed or not found
        """
        try:
            stmt = delete(UserModel).where(UserModel.id == user_id)
            result = await self.db.execute(stmt)
            
            if result.rowcount == 0:
                logger.warning(f"User {user_id} not found for deletion")
                return False
            
            await self.db.commit()
            logger.info(f"Deleted user: {user_id}")
            return True
            
        except SQLAlchemyError as e:
            logger.error(f"Database error deleting user {user_id}: {e}")
            await self.db.rollback()
            return False
        except Exception as e:
            logger.error(f"Unexpected error deleting user {user_id}: {e}")
            await self.db.rollback()
            return False