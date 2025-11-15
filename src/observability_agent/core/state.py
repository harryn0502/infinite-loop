"""State definitions for the observability multi-agent system."""

from typing import TypedDict, Annotated, Literal, List, Dict, Any
from langgraph.graph.message import add_messages
from langchain_core.messages import AnyMessage


class ObsState(TypedDict):
    """
    State for the observability agent system.

    Attributes:
        messages: LangGraph message list with add_messages reducer
        active_agent: Currently active agent name (for debugging/logging)
        last_rows: Recent SQL result rows for replay and chart generation
    """
    # LangGraph basic messages (add_messages reducer 사용)
    messages: Annotated[List[AnyMessage], add_messages]

    # 현재 어떤 agent가 일하는 중인지 (디버깅/로그용)
    active_agent: str

    # 최근 SQL 결과 row를 저장해서 "2번째 row replay" 같은 요청에 사용
    last_rows: List[Dict[str, Any]]  # [{"run_id": "...", "latency_ms": ...}, ...]


# Agent name type for routing
AgentName = Literal["metrics_agent", "row_agent", "replay_agent", "chart_agent"]
