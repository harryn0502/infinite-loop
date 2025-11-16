"""Simple refusal agent for disallowed or malicious requests."""

from langchain_core.messages import AIMessage

from ..core.state import ObsState
from ..core.state_utils import agent_state_update

REFUSAL_MESSAGE = (
    "이 요청은 Observability 분석과 무관하거나 시스템을 손상시킬 수 있으므로 도와드릴 수 없습니다. "
    "토큰/지표/차트 분석이 필요하다면 구체적으로 말씀해 주세요."
)


def refusal_agent_node(state: ObsState, llm) -> ObsState:
    plan_index = state.get("plan_step_index", 0) + 1
    msg = AIMessage(content=REFUSAL_MESSAGE)
    return agent_state_update(
        state,
        messages=[msg],
        active_agent="refusal_agent",
        plan_step_index=plan_index,
        clarification={"status": "none"},
        plan=[],
    )
