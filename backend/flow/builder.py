from langgraph.graph import StateGraph, START, END
from .router_agent.router_agent import router_agent, route_action, router_message_handler
from .create_agent.create_agent import create_agent, create_message_handler, create_action, check_event_conflict, create_conflict_action, create_conflict_message_handler
from .list_agent.list_agent import list_date_range_agent, list_message_handler, list_action, list_event_by_date_range, list_filter_event_agent
from .delete_agent.delete_agent import delete_date_range_agent, delete_message_handler, delete_action, delete_event_by_date_range, delete_filter_event_agent
from .update_agent.update_agent import update_date_range_agent, update_message_handler, update_action, get_events_for_update, update_filter_event_agent
from .state import FlowState

class FlowBuilder:    
    def create_flow(self):      
        
        # Add nodes
        graph_builder = StateGraph(FlowState)

        graph_builder.add_node("router_agent", router_agent)
        graph_builder.add_node("router_message_handler", router_message_handler)
        graph_builder.add_node("create_agent", create_agent)
        graph_builder.add_node("create_message_handler", create_message_handler)
        graph_builder.add_node("check_event_conflict", check_event_conflict)
        graph_builder.add_node("create_conflict_message_handler", create_conflict_message_handler)
        graph_builder.add_node("list_date_range_agent", list_date_range_agent)
        graph_builder.add_node("list_message_handler", list_message_handler)
        graph_builder.add_node("list_event_by_date_range", list_event_by_date_range)
        graph_builder.add_node("list_filter_event_agent", list_filter_event_agent)
        graph_builder.add_node("delete_date_range_agent", delete_date_range_agent)
        graph_builder.add_node("delete_message_handler", delete_message_handler)
        graph_builder.add_node("delete_event_by_date_range", delete_event_by_date_range)
        graph_builder.add_node("delete_filter_event_agent", delete_filter_event_agent)
        graph_builder.add_node("update_date_range_agent", update_date_range_agent)
        graph_builder.add_node("update_message_handler", update_message_handler)
        graph_builder.add_node("get_events_for_update", get_events_for_update)
        graph_builder.add_node("update_filter_event_agent", update_filter_event_agent)

        

        # Add edges
        graph_builder.add_edge(START, "router_agent")
        graph_builder.add_conditional_edges("router_agent", route_action)
        graph_builder.add_edge("router_message_handler", END)
        # TODO: Add edges from agents to END
        graph_builder.add_conditional_edges("create_agent", create_action)
        graph_builder.add_edge("create_message_handler", END)
        graph_builder.add_conditional_edges("check_event_conflict", create_conflict_action)
        graph_builder.add_edge("create_conflict_message_handler", END)

        graph_builder.add_conditional_edges("list_date_range_agent", list_action)
        graph_builder.add_edge("list_message_handler", END)
        graph_builder.add_edge("list_event_by_date_range", "list_filter_event_agent")
        graph_builder.add_edge("list_filter_event_agent", END)


        

        graph_builder.add_conditional_edges("delete_date_range_agent", delete_action)
        graph_builder.add_edge("delete_message_handler", END)
        graph_builder.add_edge("delete_event_by_date_range", "delete_filter_event_agent")
        graph_builder.add_edge("delete_filter_event_agent", END)

        graph_builder.add_conditional_edges("update_date_range_agent", update_action)
        graph_builder.add_edge("update_message_handler", END)
        graph_builder.add_edge("get_events_for_update", "update_filter_event_agent")
        graph_builder.add_edge("update_filter_event_agent", END)

        #checkpointer = get_checkpointer()

        flow = graph_builder.compile()
        return flow
    
        
    
        
    
    