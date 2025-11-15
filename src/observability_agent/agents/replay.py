"""Replay agent for re-running previous agent executions."""

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

from ..core.state import ObsState
from ..tools.replay_api import replay_run


def replay_agent_node(state: ObsState, llm) -> ObsState:
    """
    '2번 row replay해줘' 같은 요청 처리.

    Handles replay requests by:
    1. Checking if previous rows exist in state
    2. Using LLM to parse which row number the user wants
    3. Extracting run_id and calling replay_run()

    Args:
        state: Current observability state with last_rows
        llm: Language model instance

    Returns:
        Updated state with replay confirmation or error message
    """
    user_message = state["messages"][-1]
    last_rows = state.get("last_rows", [])

    if not last_rows:
        # row 정보가 없으면 안내
        error_msg = AIMessage(
            content=(
                "I don't have any recent rows to replay. "
                "Please first ask me to list some runs or tool calls, "
                "then tell me which row number to replay."
            )
        )
        return {
            "messages": [error_msg],
            "active_agent": "replay_agent",
            "last_rows": last_rows,
        }

    # LLM에게 "유저가 말한 row 번호"만 파싱하게 한다
    system = SystemMessage(
        content=(
            "The user wants to replay one of the previously shown rows.\n"
            "You are given the list of rows and the user's message.\n"
            "Your job is ONLY to output the index (1-based) of the row to replay, as an integer.\n"
            "If you cannot tell, output 1.\n\n"
            "Answer format: just the integer, nothing else."
        )
    )
    rows_for_llm = "\n".join([f"{i+1}. {row}" for i, row in enumerate(last_rows)])
    helper_user = HumanMessage(
        content=(
            f"Rows:\n{rows_for_llm}\n\n"
            f"User message: {user_message.content}\n\n"
            "Which row index should be replayed?"
        )
    )
    idx_msg = llm.invoke([system, helper_user])

    try:
        idx = int(idx_msg.content.strip())
    except ValueError:
        idx = 1

    idx = max(1, min(idx, len(last_rows)))  # 범위 클램프
    target_row = last_rows[idx - 1]

    run_id = target_row.get("run_id") or target_row.get("RUN_ID") or target_row.get("RunId")
    if not run_id:
        # run_id 못 찾으면 row 자체를 보여주고 실패 안내
        fail_msg = AIMessage(
            content=(
                f"I tried to replay row {idx}, but I couldn't find a 'run_id' column "
                f"in the row: {target_row}\n"
                "Please ensure that the SQL query returns a 'run_id' field."
            )
        )
        return {
            "messages": [idx_msg, fail_msg],
            "active_agent": "replay_agent",
            "last_rows": last_rows,
        }

    replay_result = replay_run(run_id)

    final_msg = AIMessage(
        content=(
            f"I have scheduled a replay for run_id={run_id} (row {idx}).\n"
            f"Status: {replay_result['status']}\n"
            f"Replay run id: {replay_result['replay_run_id']}\n"
            f"Replay URL: {replay_result['replay_url']}"
        )
    )

    return {
        "messages": [idx_msg, final_msg],
        "active_agent": "replay_agent",
        "last_rows": last_rows,
    }
