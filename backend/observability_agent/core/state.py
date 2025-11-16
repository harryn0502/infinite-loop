"""State definitions for the observability multi-agent system."""

from typing import TypedDict, Annotated, Literal, List, Dict, Any
from langgraph.graph.message import add_messages
from langchain_core.messages import AnyMessage


class DiagnosticsQueryResult(TypedDict):
    """Single diagnostics step output tracked for later summary."""

    name: str
    description: str
    rows: List[Dict[str, Any]]


class DiagnosticsContext(TypedDict, total=False):
    """Shared context across diagnostics plan steps."""

    target_metric: Literal["latency", "tokens", "both"]
    baseline_window_hours: int
    recent_window_hours: int
    results: List[DiagnosticsQueryResult]


class ObsState(TypedDict):
    """
    State for the observability agent system.

    Attributes:
        messages: LangGraph message list with add_messages reducer
        active_agent: Currently active agent name (for debugging/logging)
        last_rows: Recent SQL result rows for follow-up questions and chart generation
        plan: Planner output steps
        plan_step_index: Current step index within the plan
        plan_mode: Current planner mode ("default" vs "diagnostics")
        diagnostics_context: Aggregated diagnostics results
        has_error: Whether a fatal error occurred (stops execution)
    """

    # LangGraph basic messages (using add_messages reducer)
    messages: Annotated[List[AnyMessage], add_messages]

    # Currently active agent (for debugging/logging)
    active_agent: str

    # Store recent SQL result rows for follow-up questions
    last_rows: List[Dict[str, Any]]  # [{"run_id": "...", "latency_ms": ...}, ...]
    plan: List[Dict[str, Any]]
    plan_step_index: int
    plan_mode: Literal["default", "diagnostics"]
    diagnostics_context: DiagnosticsContext
    has_error: bool


# Agent name type for routing (planner is routed explicitly)
AgentName = Literal[
    "planner",
    "metrics_agent",
    "chart_agent",
    "refusal_agent",
    "diagnostics_summary_agent",
    "complete",
]
