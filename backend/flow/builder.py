from langgraph.graph import StateGraph, START, END
from .router_agent.router_agent import router_agent, route_action, router_message_handler
from .create_agent.create_agent import create_agent, create_message_handler, create_action
from .list_agent.list_agent import list_agent, list_message_handler, list_action
from .delete_agent.delete_agent import delete_agent_timestamp, delete_message_timestamp_handler, delete_action_timestamp
from .state import FlowState

class FlowBuilder:    
    def create_flow(self):      
        
        # Add nodes
        graph_builder = StateGraph(FlowState)

        graph_builder.add_node("router_agent", router_agent)
        graph_builder.add_node("router_message_handler", router_message_handler)
        graph_builder.add_node("create_agent", create_agent)
        graph_builder.add_node("create_message_handler", create_message_handler)
        graph_builder.add_node("list_agent", list_agent)
        graph_builder.add_node("list_message_handler", list_message_handler)
        graph_builder.add_node("delete_agent_timestamp", delete_agent_timestamp)
        graph_builder.add_node("delete_message_timestamp_handler", delete_message_timestamp_handler)

        # TODO: Add your actual agent nodes here
        # graph_builder.add_node("update_agent", update_agent)
        # graph_builder.add_node("delete_agent", delete_agent)
        

        # Add edges
        graph_builder.add_edge(START, "router_agent")
        graph_builder.add_conditional_edges("router_agent", route_action)
        graph_builder.add_edge("router_message_handler", END)
        # TODO: Add edges from agents to END

        graph_builder.add_conditional_edges("create_agent", create_action)
        graph_builder.add_edge("create_message_handler", END)

        graph_builder.add_conditional_edges("list_agent", list_action)
        graph_builder.add_edge("list_message_handler", END)

        graph_builder.add_conditional_edges("delete_agent_timestamp", delete_action_timestamp)
        graph_builder.add_edge("delete_message_timestamp_handler", END)
        # graph_builder.add_edge("update_agent", END)
        # graph_builder.add_edge("delete_agent", END)
        # graph_builder.add_edge("list_agent", END)

        #checkpointer = get_checkpointer()

        flow = graph_builder.compile()
        return flow
    
        
    
        
    
    