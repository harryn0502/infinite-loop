"""Routing logic for the observability multi-agent system."""

from .state import ObsState, AgentName


def route_from_user_message(state: ObsState) -> AgentName:
    """
    유저의 마지막 발화를 보고 어느 agent로 보낼지 결정.

    Routes based on keywords in the user message:
    - replay keywords → replay_agent
    - chart/visualization keywords → chart_agent
    - row listing keywords → row_agent
    - default → metrics_agent

    Args:
        state: Current observability state

    Returns:
        Name of the agent to route to
    """
    last_msg = state["messages"][-1]
    content = last_msg.content.lower()

    # 엄청 단순한 규칙 기반 라우팅 (나중에 LLM 라우터로 교체 가능)
    replay_keywords = ["replay", "다시 돌려", "다시 실행", "재실행"]
    chart_keywords = ["chart", "bar chart", "line chart", "visualize", "시각화", "그래프"]
    row_keywords = ["row", "rows", "list", "보여줘", "run들", "런들", "에러난 run", "오류난 run"]

    if any(k in content for k in replay_keywords):
        return "replay_agent"
    if any(k in content for k in chart_keywords):
        return "chart_agent"
    if any(k in content for k in row_keywords):
        return "row_agent"
    # 기본은 metrics
    return "metrics_agent"


def router_node(state: ObsState) -> ObsState:
    """
    Router node that determines which agent to use.

    This node doesn't add any messages to the conversation,
    it just sets the active_agent field for routing.

    Args:
        state: Current observability state

    Returns:
        Updated state with active_agent set
    """
    agent_name = route_from_user_message(state)
    return {
        "messages": [],  # router 자체는 message 추가 안 함
        "active_agent": agent_name,
        "last_rows": state.get("last_rows", []),
    }
