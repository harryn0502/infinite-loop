"""Helper utilities for running the observability agent."""

from typing import Optional
from langchain_core.messages import HumanMessage, AIMessage

from ..core.state import ObsState


def run_obs_agent(
    user_message: str,
    app,
    prev_state: Optional[ObsState] = None
) -> ObsState:
    """
    멀티턴 지원용 실행 함수.

    Executes the observability agent with multi-turn conversation support.
    - If prev_state is provided, continues the conversation
    - Otherwise starts a new conversation

    Args:
        user_message: User's input message
        app: Compiled LangGraph application
        prev_state: Previous conversation state (optional)

    Returns:
        Final state after processing the message
    """
    print("\n=== User ===")
    print(user_message)
    print("============")

    if prev_state is None:
        state: ObsState = {
            "messages": [HumanMessage(content=user_message)],
            "active_agent": "router",
            "last_rows": [],
            "chart_context": {"rows": [], "metadata": {}},
            "plan": [],
            "plan_step_index": 0,
        }
    else:
        # 이전 대화에 새로운 user message 추가
        state = {
            "messages": prev_state["messages"] + [HumanMessage(content=user_message)],
            "active_agent": prev_state["active_agent"],
            "last_rows": prev_state.get("last_rows", []),
            "chart_context": prev_state.get("chart_context", {"rows": prev_state.get("last_rows", []), "metadata": {}}),
            "plan": [],
            "plan_step_index": 0,
        }

    final_state: Optional[ObsState] = None
    printed = len(state["messages"])

    for event in app.stream(state, stream_mode="values"):
        final_state = event
        messages = event["messages"]
        if not messages:
            continue

        new_messages = messages[printed:]
        printed = len(messages)

        for msg in new_messages:
            if not isinstance(msg, AIMessage):
                continue

            print("\n=== Agent Response ===")
            print(msg.content)

            meta = getattr(msg, "additional_kwargs", {})
            reasoning = meta.get("reasoning")
            content_text = msg.content if isinstance(msg.content, str) else ""
            if reasoning and (not content_text or reasoning not in content_text):
                print(f"\n💡 Reasoning: {reasoning}")

            print("======================")

    return final_state or state
