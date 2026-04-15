"""
Webhook Cleanup Service

Deletes processed_webhooks rows older than RETENTION_DAYS to prevent unbounded growth.
Runs once daily at 3 AM (server time) via APScheduler.
"""

import logging
from datetime import datetime, timezone, timedelta

from sqlalchemy import delete

from database.config import get_async_db_context_manager
from database.models.webhook import ProcessedWebhookModel

logger = logging.getLogger(__name__)

RETENTION_DAYS = 30


async def purge_old_webhooks() -> None:
    """Delete processed_webhooks rows older than RETENTION_DAYS days."""
    cutoff = datetime.now(timezone.utc) - timedelta(days=RETENTION_DAYS)
    async with get_async_db_context_manager() as db:
        result = await db.execute(
            delete(ProcessedWebhookModel).where(ProcessedWebhookModel.created_at < cutoff)
        )
        await db.commit()
    logger.info(f"Webhook cleanup: deleted {result.rowcount} rows older than {RETENTION_DAYS} days")
