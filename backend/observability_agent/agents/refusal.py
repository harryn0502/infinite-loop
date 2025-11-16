"""Simple refusal agent for disallowed or malicious requests."""

from langchain_core.messages import AIMessage

from ..core.state import ObsState
from ..core.state_utils import agent_state_update

REFUSAL_MESSAGE = (
    "I cannot help with this request as it is either unrelated to observability analysis "
    "or could potentially harm the system. If you need token/metrics/chart analysis, "
    "please be specific about your requirements."
)


def refusal_agent_node(state: ObsState, llm) -> ObsState:
    plan_index = state.get("plan_step_index", 0) + 1
    msg = AIMessage(content=REFUSAL_MESSAGE)
    return agent_state_update(
        state,
        messages=[msg],
        active_agent="refusal_agent",
        plan_step_index=plan_index,
        plan=[],
    )
