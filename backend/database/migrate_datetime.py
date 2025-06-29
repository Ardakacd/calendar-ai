import logging
from sqlalchemy import text, inspect
from database.config import engine, get_db_session
from sqlalchemy.exc import SQLAlchemyError

logger = logging.getLogger(__name__)

def migrate_datetime_column():
    """
    Migrate the datetime column from string to datetime with timezone support.
    This handles the case where the LLM returns ISO format datetime strings.
    """
    try:
        with engine.connect() as conn:
            # Check if the events table exists
            inspector = inspect(engine)
            if 'events' not in inspector.get_table_names():
                logger.info("Events table doesn't exist, skipping migration")
                return
            
            # Check current column type
            columns = inspector.get_columns('events')
            datetime_column = next((col for col in columns if col['name'] == 'datetime'), None)
            
            if not datetime_column:
                logger.error("datetime column not found in events table")
                return
            
            # Check if migration is needed
            if 'DateTime' in str(datetime_column['type']):
                logger.info("datetime column is already DateTime type, migration not needed")
                return
            
            logger.info("Starting datetime column migration...")
            
            # Begin transaction
            trans = conn.begin()
            
            try:
                # Create a temporary column with the new type
                conn.execute(text("""
                    ALTER TABLE events 
                    ADD COLUMN datetime_new TIMESTAMP WITH TIME ZONE
                """))
                
                # Convert existing string data to datetime
                conn.execute(text("""
                    UPDATE events 
                    SET datetime_new = datetime::timestamp with time zone
                    WHERE datetime IS NOT NULL
                """))
                
                # Drop the old column
                conn.execute(text("ALTER TABLE events DROP COLUMN datetime"))
                
                # Rename the new column to datetime
                conn.execute(text("ALTER TABLE events RENAME COLUMN datetime_new TO datetime"))
                
                # Make the column NOT NULL
                conn.execute(text("ALTER TABLE events ALTER COLUMN datetime SET NOT NULL"))
                
                # Commit the transaction
                trans.commit()
                
                logger.info("Datetime column migration completed successfully")
                
            except Exception as e:
                trans.rollback()
                logger.error(f"Migration failed, rolling back: {e}")
                raise
                
    except SQLAlchemyError as e:
        logger.error(f"Database error during migration: {e}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error during migration: {e}")
        raise

if __name__ == "__main__":
    migrate_datetime_column() 