import os
import logging
from sqlalchemy import create_engine, inspect
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.sql import func
from sqlalchemy_utils import create_database, database_exists
from sqlalchemy.exc import SQLAlchemyError
from .models.event import Base
from config import settings

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# Create SQLAlchemy engine with production-ready pooling
engine = create_engine(
    settings.DATABASE_URL,
    # Connection pooling configuration
    pool_size=settings.DB_POOL_SIZE,
    max_overflow=settings.DB_MAX_OVERFLOW,
    pool_timeout=settings.DB_POOL_TIMEOUT,
    pool_recycle=settings.DB_POOL_RECYCLE,
    pool_pre_ping=settings.DB_POOL_PRE_PING,
    echo=settings.SQL_ECHO,
    # Production SSL settings
    connect_args={
        "sslmode": settings.DB_SSL_MODE,
        "connect_timeout": settings.DB_CONNECT_TIMEOUT
    } if settings.DB_SSL_MODE else {}
)

# Create async engine for async operations
async_engine = create_async_engine(
    settings.DATABASE_URL.replace('postgresql://', 'postgresql+asyncpg://'),
    # Connection pooling configuration
    pool_size=settings.DB_POOL_SIZE,
    max_overflow=settings.DB_MAX_OVERFLOW,
    pool_timeout=settings.DB_POOL_TIMEOUT,
    pool_recycle=settings.DB_POOL_RECYCLE,
    pool_pre_ping=settings.DB_POOL_PRE_PING,
    echo=settings.SQL_ECHO,
    # Production SSL settings
    connect_args={
        "sslmode": settings.DB_SSL_MODE,
        "connect_timeout": settings.DB_CONNECT_TIMEOUT
    } if settings.DB_SSL_MODE else {}
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
AsyncSessionLocal = async_sessionmaker(async_engine, class_=AsyncSession, expire_on_commit=False)

def create_database_if_not_exists():
    """Create database if it doesn't exist using sqlalchemy_utils"""
    try:
        if not database_exists(settings.DATABASE_URL):
            create_database(settings.DATABASE_URL)
            logger.info(f"Created database: {settings.DATABASE_URL.split('@')[-1]}")
        else:
            logger.info("Database already exists")
    except Exception as e:
        logger.error(f"Database creation error: {e}")
        raise

def get_db():
    """Get database session with automatic cleanup and error handling"""
    db = SessionLocal()
    try:
        yield db
    except SQLAlchemyError as e:
        logger.error(f"Database error: {e}")
        db.rollback()
        raise
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        db.rollback()
        raise
    finally:
        db.close()

async def get_async_db():
    """Get async database session with automatic cleanup and error handling"""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except SQLAlchemyError as e:
            logger.error(f"Async database error: {e}")
            await session.rollback()
            raise
        except Exception as e:
            logger.error(f"Unexpected async database error: {e}")
            await session.rollback()
            raise

async def get_async_session():
    """Get a single async database session without dependency injection"""
    try:
        return AsyncSessionLocal()
    except Exception as e:
        logger.error(f"Failed to create async database session: {e}")
        raise

def init_db():
    """Initialize database with tables and production logging"""
    try:
        # First create database if it doesn't exist
        create_database_if_not_exists()
        
        # Check if tables exist
        inspector = inspect(engine)
        existing_tables = inspector.get_table_names()
        
        if 'events' not in existing_tables:
            logger.info("Creating tables...")
            Base.metadata.create_all(bind=engine)
            logger.info("Tables created successfully")
        else:
            logger.info("Tables already exist, skipping creation")
        
        # Log pool status
        pool_status = get_pool_status()
        logger.info(f"Database initialized successfully. Pool status: {pool_status}")
        
    except Exception as e:
        logger.error(f"Database initialization failed: {e}")
        raise

def get_db_session():
    """Get a database session with error handling"""
    try:
        return SessionLocal()
    except Exception as e:
        logger.error(f"Failed to create database session: {e}")
        raise

def get_pool_status():
    """Get connection pool status for monitoring"""
    try:
        return {
            "pool_size": engine.pool.size(),
            "checked_in": engine.pool.checkedin(),
            "checked_out": engine.pool.checkedout(),
            "overflow": engine.pool.overflow()
        }
    except Exception as e:
        logger.error(f"Failed to get pool status: {e}")
        return {"error": str(e)}

def health_check():
    """Database health check for monitoring"""
    try:
        with engine.connect() as conn:
            conn.execute(func.select(1))
        return {"status": "healthy", "pool": get_pool_status()}
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {"status": "unhealthy", "error": str(e)} 