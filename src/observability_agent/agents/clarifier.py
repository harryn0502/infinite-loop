"""Clarifier agent to ask follow-up questions for ambiguous queries."""

from langchain_core.messages import AIMessage

from ..core.state import ObsState
from ..core.state_utils import agent_state_update

DEFAULT_FOLLOWUP = "조금 더 구체적으로 설명해 주실 수 있을까요?"


def clarifier_agent_node(state: ObsState, llm) -> ObsState:
    """
    Sends a single clarifying question back to the user.

    The router populates state["clarification"]["question"] before invoking this node.
    """
    clarification = state.get("clarification", {"status": "none"})
    question = clarification.get("question") or DEFAULT_FOLLOWUP

    msg = AIMessage(content=question)
    next_index = state.get("plan_step_index", 0) + 1
    clarification_state = state.get("clarification", {"status": "pending"})
    return agent_state_update(
        state,
        messages=[msg],
        active_agent="clarifier_agent",
        plan_step_index=next_index,
        clarification=clarification_state,
    )
