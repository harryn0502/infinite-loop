"""LangGraph workflow definition for the observability agent system."""

from functools import partial
from langgraph.graph import StateGraph, START, END

from .state import ObsState
from ..agents.router import router_agent_node
from ..agents.metrics import metrics_agent_node
from ..agents.chart import chart_agent_node
from ..agents.planner import planner_agent_node
from ..agents.diagnostics_summary import diagnostics_summary_agent_node


def build_graph(llm):
    """
    Build and compile the observability agent LangGraph workflow.

    Creates a multi-agent system with:
    - Planner: Breaks down user intent into steps
    - Router: Executes each plan step in sequence (also handles refusals)
    - Metrics Agent: Handles analytics and Text2SQL queries
    - Chart Agent: Generates visualization specifications
    - Diagnostics Summary Agent: Explains root causes from diagnostics context

    Args:
        llm: Language model instance to use for all agents

    Returns:
        Compiled LangGraph application ready to execute
    """
    workflow = StateGraph(ObsState)

    # Bind the LLM to each agent node using partial
    planner_node = partial(planner_agent_node, llm=llm)
    router_node = partial(router_agent_node, llm=llm)
    metrics_node = partial(metrics_agent_node, llm=llm)
    chart_node = partial(chart_agent_node, llm=llm)
    diagnostics_node = partial(diagnostics_summary_agent_node, llm=llm)

    # Add nodes
    workflow.add_node("planner", planner_node)
    workflow.add_node("router", router_node)
    workflow.add_node("metrics_agent", metrics_node)
    workflow.add_node("chart_agent", chart_node)
    workflow.add_node("diagnostics_summary_agent", diagnostics_node)

    # Add edges
    workflow.add_edge(START, "router")
    workflow.add_edge("planner", "router")

    def route_from_state(state: ObsState) -> str:
        plan = state.get("plan", []) or []
        idx = state.get("plan_step_index", 0)
        valid_agents = {
            "metrics_agent",
            "chart_agent",
            "diagnostics_summary_agent",
        }

        if plan and idx < len(plan):
            agent = plan[idx].get("agent", "metrics_agent")
            return agent if agent in valid_agents else "metrics_agent"

        if plan and idx >= len(plan):
            return "complete"

        if not plan and idx > 0:
            return "complete"

        agent = state.get("active_agent") or "planner"
        if agent == "planner":
            return "planner"
        if agent in valid_agents:
            return agent
        return "complete"

    workflow.add_conditional_edges(
        "router",
        route_from_state,
        {
            "planner": "planner",
            "metrics_agent": "metrics_agent",
            "chart_agent": "chart_agent",
            "diagnostics_summary_agent": "diagnostics_summary_agent",
            "complete": END,
        },
    )

    workflow.add_edge("metrics_agent", "router")
    workflow.add_edge("chart_agent", "router")
    workflow.add_edge("diagnostics_summary_agent", "router")

    return workflow.compile()
