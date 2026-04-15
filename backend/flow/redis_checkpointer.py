from langgraph.checkpoint.redis.aio import AsyncRedisSaver
from config import settings
import os
from dotenv import load_dotenv
from typing import Any, Dict
from langchain_core.runnables import RunnableConfig

load_dotenv(dotenv_path=f'.env.{settings.ENV}')

# Fields to persist in Redis checkpoints — must stay in sync with FlowState.
_PERSISTED_FIELDS = {
    'router_messages',
    'scheduling_messages',
    'conflict_resolution_messages',
    'scheduling_event_data',
    'conflict_check_request',
    'conflict_check_result',
    'scheduling_operation',
    'scheduling_result',
    'previous_route',
    'route',
    'conversation_summary',
}


class MessagesOnlyRedisSaver(AsyncRedisSaver):
    """Custom Redis checkpointer that only saves message/context fields."""

    def _filter_state_for_checkpoint(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Filter state to only include persisted fields."""
        return {
            key: value for key, value in state.items()
            if key in _PERSISTED_FIELDS
        }

    def _filter_versions_for_checkpoint(self, versions: Dict[str, Any]) -> Dict[str, Any]:
        """Filter channel_versions to only include persisted field versions."""
        return {
            key: value for key, value in versions.items()
            if key in _PERSISTED_FIELDS
        }

    async def aput(
        self,
        config: RunnableConfig,
        checkpoint: Dict[str, Any],
        metadata: Dict[str, Any],
        new_versions: Dict[str, Any],
    ) -> RunnableConfig:
        """Override aput to filter checkpoint data before saving."""
        if 'channel_values' in checkpoint:
            checkpoint['channel_values'] = self._filter_state_for_checkpoint(
                checkpoint['channel_values']
            )

        if 'channel_versions' in checkpoint:
            checkpoint['channel_versions'] = self._filter_versions_for_checkpoint(
                checkpoint['channel_versions']
            )

        filtered_new_versions = self._filter_versions_for_checkpoint(new_versions)

        return await super().aput(config, checkpoint, metadata, filtered_new_versions)


# ---------------------------------------------------------------------------
# Module-level singleton — keeps the Redis connection alive across requests.
# ---------------------------------------------------------------------------
_saver_instance: MessagesOnlyRedisSaver | None = None


async def get_checkpointer() -> MessagesOnlyRedisSaver:
    """Return (and lazily create) a long-lived Redis checkpointer singleton.

    Uses ``from_conn_string`` only once; subsequent calls return the same
    instance so the underlying Redis connection pool is reused.
    """
    global _saver_instance
    if _saver_instance is not None:
        return _saver_instance

    REDIS_URL = settings.redis_url

    # TTL: 7 days = 10080 minutes.  ``default_ttl`` is in minutes.
    ttl_config = {"default_ttl": 10080, "refresh_on_read": True}

    saver = MessagesOnlyRedisSaver(redis_url=REDIS_URL, ttl=ttl_config)
    await saver.asetup()
    _saver_instance = saver
    return _saver_instance
