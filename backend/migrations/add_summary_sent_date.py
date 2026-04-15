"""
Migration: add summary_sent_date column to users table.

Run once:
    cd backend && python -m migrations.add_summary_sent_date
"""

from sqlalchemy import text
from database.config import engine


def run():
    with engine.connect() as conn:
        conn.execute(text("""
            ALTER TABLE users
            ADD COLUMN IF NOT EXISTS summary_sent_date DATE;
        """))
        conn.commit()
    print("Migration complete: users.summary_sent_date added.")


if __name__ == "__main__":
    run()
