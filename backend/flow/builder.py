from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver
from .router_agent.router_agent import router_agent, route_action, router_message_handler
from .scheduling_agent.scheduling_agent import scheduling_agent, scheduling_finalize, scheduling_route
from .conflict_resolution.conflict_resolution_agent import conflict_resolution_agent
from .leisure_search_agent.leisure_search_agent import leisure_search_agent
from .notification_agent.notification_agent import notification_agent
from .state import FlowState

# Module-level singleton — persists for the lifetime of the server process.
# Swap this for AsyncRedisSaver when ready for production persistence.
_checkpointer = MemorySaver()


class FlowBuilder:
    async def create_flow(self):
        graph_builder = StateGraph(FlowState)

        # Nodes
        graph_builder.add_node("router_agent", router_agent)
        graph_builder.add_node("router_message_handler", router_message_handler)
        graph_builder.add_node("leisure_search_agent", leisure_search_agent)
        graph_builder.add_node("scheduling_agent", scheduling_agent)
        graph_builder.add_node("conflict_resolution_agent", conflict_resolution_agent)
        graph_builder.add_node("scheduling_finalize", scheduling_finalize)
        graph_builder.add_node("notification_agent", notification_agent)

        # Edges from router
        graph_builder.add_edge(START, "router_agent")
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
        flow = graph_builder.compile(checkpointer=_checkpointer)
        return flow
