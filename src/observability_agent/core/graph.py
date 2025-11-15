"""LangGraph workflow definition for the observability agent system."""

from functools import partial
from langgraph.graph import StateGraph, START, END

from .state import ObsState
from .router import router_node, route_from_user_message
from ..agents.metrics import metrics_agent_node
from ..agents.row_explorer import row_agent_node
from ..agents.replay import replay_agent_node
from ..agents.chart import chart_agent_node


def build_graph(llm):
    """
    Build and compile the observability agent LangGraph workflow.

    Creates a multi-agent system with:
    - Router: Routes user messages to appropriate agent
    - Metrics Agent: Handles analytics and Text2SQL queries
    - Row Agent: Lists and explores data rows
    - Replay Agent: Re-runs previous agent executions
    - Chart Agent: Generates visualization specifications

    Args:
        llm: Language model instance to use for all agents

    Returns:
        Compiled LangGraph application ready to execute
    """
    workflow = StateGraph(ObsState)

    # Bind the LLM to each agent node using partial
    metrics_node = partial(metrics_agent_node, llm=llm)
    row_node = partial(row_agent_node, llm=llm)
    replay_node = partial(replay_agent_node, llm=llm)
    chart_node = partial(chart_agent_node, llm=llm)

    # Add nodes
    workflow.add_node("router", router_node)
    workflow.add_node("metrics_agent", metrics_node)
    workflow.add_node("row_agent", row_node)
    workflow.add_node("replay_agent", replay_node)
    workflow.add_node("chart_agent", chart_node)

    # Add edges
    workflow.add_edge(START, "router")

    workflow.add_conditional_edges(
        "router",
        route_from_user_message,
        {
            "metrics_agent": "metrics_agent",
            "row_agent": "row_agent",
            "replay_agent": "replay_agent",
            "chart_agent": "chart_agent",
        },
    )

    workflow.add_edge("metrics_agent", END)
    workflow.add_edge("row_agent", END)
    workflow.add_edge("replay_agent", END)
    workflow.add_edge("chart_agent", END)

    return workflow.compile()
