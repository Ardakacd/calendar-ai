import os
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver
from .router_agent.router_agent import router_agent, route_action, router_message_handler
from .scheduling_agent.scheduling_agent import scheduling_agent, scheduling_finalize, scheduling_route
from .conflict_resolution.conflict_resolution_agent import conflict_resolution_agent
from .leisure_search_agent.leisure_search_agent import leisure_search_agent
from .notification_agent.notification_agent import notification_agent
from .summarizer import summarize_conversation
from .state import FlowState

# Module-level singleton — persists for the lifetime of the server process.
# When USE_REDIS_CHECKPOINTER=1 the singleton is created lazily (async) the
# first time create_flow() is called.
_checkpointer = None
_checkpointer_initialised = False


async def _get_checkpointer():
    """Return the checkpointer singleton, initialising it once."""
    global _checkpointer, _checkpointer_initialised
    if _checkpointer_initialised:
        return _checkpointer

    if os.environ.get("USE_REDIS_CHECKPOINTER") == "1":
        from .redis_checkpointer import get_checkpointer
        _checkpointer = await get_checkpointer()
    else:
        _checkpointer = MemorySaver()

    _checkpointer_initialised = True
    return _checkpointer


async def reset_thread(thread_id: str) -> None:
    """Clear all checkpoint data for a given thread.

    Uses LangGraph's ``adelete_thread`` API (MemorySaver and AsyncRedisSaver /
    MessagesOnlyRedisSaver in langgraph 0.5.x).  Safe to call even if no
    checkpoints exist for *thread_id*.

    Note: older code looked for ``adelete`` and ``_redis``; AsyncRedisSaver
    exposes neither, so Redis resets were effectively no-ops before this fix.
    """
    import logging

    logger = logging.getLogger(__name__)
    cp = await _get_checkpointer()

    try:
        await cp.adelete_thread(thread_id)
    except AttributeError:
        # Extremely old or custom checkpointer without adelete_thread.
        if isinstance(cp, MemorySaver):
            cp.storage.pop(thread_id, None)
            cp.writes.pop(thread_id, None)
        else:
            logger.warning(
                "Cannot reset thread %s: checkpointer %s has no adelete_thread",
                thread_id,
                type(cp).__name__,
            )
    except Exception:
        logger.warning(
            "Failed to reset checkpoints for thread %s", thread_id, exc_info=True
        )


class FlowBuilder:
    async def create_flow(self):
        graph_builder = StateGraph(FlowState)

        # Nodes
        graph_builder.add_node("summarize_conversation", summarize_conversation)
        graph_builder.add_node("router_agent", router_agent)
        graph_builder.add_node("router_message_handler", router_message_handler)
        graph_builder.add_node("leisure_search_agent", leisure_search_agent)
        graph_builder.add_node("scheduling_agent", scheduling_agent)
        graph_builder.add_node("conflict_resolution_agent", conflict_resolution_agent)
        graph_builder.add_node("scheduling_finalize", scheduling_finalize)
        graph_builder.add_node("notification_agent", notification_agent)

        # Edges from start: summarise (no-op when short) then route
        graph_builder.add_edge(START, "summarize_conversation")
        graph_builder.add_edge("summarize_conversation", "router_agent")

        graph_builder.add_conditional_edges(
            "router_agent",
            route_action,
            {
                "scheduling_agent": "scheduling_agent",
                "leisure_search_agent": "leisure_search_agent",
                "router_message_handler": "router_message_handler",
            },
        )

        # Scheduling flow
        graph_builder.add_conditional_edges(
            "scheduling_agent",
            scheduling_route,
            {
                "conflict_resolution_agent": "conflict_resolution_agent",
                "scheduling_finalize": "scheduling_finalize",
            },
        )
        graph_builder.add_edge("conflict_resolution_agent", "scheduling_finalize")
        graph_builder.add_edge("scheduling_finalize", "notification_agent")
        graph_builder.add_edge("notification_agent", END)

        # Terminal nodes
        graph_builder.add_edge("router_message_handler", END)
        graph_builder.add_edge("leisure_search_agent", END)

        # Compile with checkpointer so state persists across turns per user
        checkpointer = await _get_checkpointer()
        flow = graph_builder.compile(checkpointer=checkpointer)
        return flow
