"""State definitions for the observability multi-agent system."""

from typing import TypedDict, Annotated, Literal, List, Dict, Any, Optional
from langgraph.graph.message import add_messages
from langchain_core.messages import AnyMessage


class ClarificationState(TypedDict, total=False):
    """State tracked when the clarifier agent asks for follow-ups."""

    status: Literal["none", "pending", "resolved"]
    question: Optional[str]
    original_user_message: Optional[str]
    resolved_query: Optional[str]
    hints: Dict[str, Any]
    required_detail: Optional[str]


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
        chart_context: Prepared chart rows + metadata
        plan: Planner output steps
        plan_step_index: Current step index within the plan
        clarification: Query clarification status
        plan_mode: Current planner mode ("default" vs "diagnostics")
        diagnostics_context: Aggregated diagnostics results
    """

    # LangGraph basic messages (add_messages reducer 사용)
    messages: Annotated[List[AnyMessage], add_messages]

    # 현재 어떤 agent가 일하는 중인지 (디버깅/로그용)
    active_agent: str

    # 최근 SQL 결과 row를 저장해서 후속 질문 시 참조
    last_rows: List[Dict[str, Any]]  # [{"run_id": "...", "latency_ms": ...}, ...]
    chart_context: Dict[str, Any]
    plan: List[Dict[str, Any]]
    plan_step_index: int
    clarification: ClarificationState
    plan_mode: Literal["default", "diagnostics"]
    diagnostics_context: DiagnosticsContext


# Agent name type for routing (planner is routed explicitly)
AgentName = Literal[
    "planner",
    "metrics_agent",
    "chart_agent",
    "clarifier_agent",
    "refusal_agent",
    "diagnostics_summary_agent",
    "complete",
]
