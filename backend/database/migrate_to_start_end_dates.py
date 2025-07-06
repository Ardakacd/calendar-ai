import logging
from sqlalchemy import text, inspect
from database.config import engine, get_db_session
from sqlalchemy.exc import SQLAlchemyError
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

def migrate_to_start_end_dates():
    """
    Migrate the events table to use startDate and endDate columns instead of datetime and duration.
    - startDate: NOT NULL, replaces datetime
    - endDate: NULLABLE, calculated from startDate + duration if duration exists
    - Remove datetime and duration columns
    """
    try:
        with engine.connect() as conn:
            # Check if the events table exists
            inspector = inspect(engine)
            if 'events' not in inspector.get_table_names():
                logger.info("Events table doesn't exist, skipping migration")
                return
            
            # Check current columns
            columns = inspector.get_columns('events')
            column_names = [col['name'] for col in columns]
            
            logger.info(f"Current columns: {column_names}")
            
            # Check if migration is already done
            if 'startDate' in column_names and 'endDate' in column_names and 'datetime' not in column_names and 'duration' not in column_names:
                logger.info("Migration already completed, startDate and endDate columns exist")
                return
            
            logger.info("Starting migration to startDate and endDate columns...")
            
            # Begin transaction
            trans = conn.begin()
            
            try:
                # Step 1: Add startDate column if it doesn't exist
                if 'startDate' not in column_names:
                    logger.info("Adding startDate column...")
                    conn.execute(text("""
                        ALTER TABLE events 
                        ADD COLUMN startDate TIMESTAMP WITH TIME ZONE
                    """))
                
                # Step 2: Add endDate column if it doesn't exist
                if 'endDate' not in column_names:
                    logger.info("Adding endDate column...")
                    conn.execute(text("""
                        ALTER TABLE events 
                        ADD COLUMN endDate TIMESTAMP WITH TIME ZONE
                    """))
                
                # Step 3: Populate startDate from datetime
                if 'datetime' in column_names:
                    logger.info("Populating startDate from datetime...")
                    conn.execute(text("""
                        UPDATE events 
                        SET startDate = datetime
                        WHERE datetime IS NOT NULL
                    """))
                
                # Step 4: Populate endDate from datetime + duration
                if 'datetime' in column_names and 'duration' in column_names:
                    logger.info("Populating endDate from datetime + duration...")
                    conn.execute(text("""
                        UPDATE events 
                        SET endDate = datetime + (duration || ' minutes')::interval
                        WHERE datetime IS NOT NULL AND duration IS NOT NULL AND duration > 0
                    """))
                
                # Step 5: Make startDate NOT NULL
                logger.info("Making startDate NOT NULL...")
                conn.execute(text("""
                    ALTER TABLE events 
                    ALTER COLUMN startDate SET NOT NULL
                """))
                
                # Step 6: Drop old columns
                if 'datetime' in column_names:
                    logger.info("Dropping datetime column...")
                    conn.execute(text("ALTER TABLE events DROP COLUMN datetime"))
                
                if 'duration' in column_names:
                    logger.info("Dropping duration column...")
                    conn.execute(text("ALTER TABLE events DROP COLUMN duration"))
                
                # Commit the transaction
                trans.commit()
                
                logger.info("Migration to startDate and endDate completed successfully")
                
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
    migrate_to_start_end_dates() 