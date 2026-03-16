from langgraph.graph import StateGraph, START, END
from .router_agent.router_agent import router_agent, route_action, router_message_handler
from .state import FlowState

# Note: create, delete, update, list agents removed from graph for new architecture.
# Agent files preserved in: create_agent/, delete_agent/, update_agent/, list_agent/


class FlowBuilder:
    async def create_flow(self):
        # Add nodes
        graph_builder = StateGraph(FlowState)

        graph_builder.add_node("router_agent", router_agent)
        graph_builder.add_node("router_message_handler", router_message_handler)

        # Add edges
        graph_builder.add_edge(START, "router_agent")
        graph_builder.add_conditional_edges("router_agent", route_action)
        graph_builder.add_edge("router_message_handler", END)

        flow = graph_builder.compile()
        return flow
    
        
    
        
    
    