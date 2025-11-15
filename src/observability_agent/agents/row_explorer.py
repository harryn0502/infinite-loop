"""Row exploration agent for debugging and data inspection."""

from langchain_core.messages import HumanMessage, SystemMessage

from ..core.state import ObsState
from ..tools.schema import get_observability_schema
from ..tools.database import run_sql
from ..utils.sql_parser import extract_sql_from_text


def row_agent_node(state: ObsState, llm) -> ObsState:
    """
    조건에 맞는 run row들을 보여달라는 요청 담당.

    Handles requests to list and explore specific rows:
    1. Converts natural language to SQL for row retrieval
    2. Executes the query
    3. Presents rows in a numbered format for easy reference

    Args:
        state: Current observability state
        llm: Language model instance

    Returns:
        Updated state with numbered rows for replay/inspection
    """
    schema = get_observability_schema()
    user_message = state["messages"][-1]

    system = SystemMessage(
        content=(
            "You are a debugging / row exploration SQL agent.\n"
            "The user wants to see specific rows (runs, tool_calls, traces) "
            "that match given conditions.\n"
            "You will:\n"
            "1) Read the database schema.\n"
            "2) Generate a SELECT SQL query that returns the most relevant rows.\n"
            "3) The query MUST be read-only and MUST include a LIMIT (e.g., LIMIT 20).\n"
            "4) Output only one final SQL query inside a ```sql ... ``` block."
            f"\n\nDatabase schema:\n{schema}"
        )
    )
    messages = [system] + state["messages"]
    draft = llm.invoke(messages)
    sql = extract_sql_from_text(draft.content)

    sql_result = run_sql(sql)
    columns = sql_result["columns"]
    rows = sql_result["rows"]
    row_dicts = [
        {col: value for col, value in zip(columns, row)}
        for row in rows
    ]

    # row 리스트를 그대로 요약해서 넘겨줌
    summary_system = SystemMessage(
        content=(
            "You are a debugging assistant.\n"
            "Explain to the user what rows you found.\n"
            "Number the rows as 1, 2, 3, ... so the user can say 'replay row 2'.\n"
            "Keep it concise but clear."
        )
    )
    summary_user = HumanMessage(
        content=(
            f"User question: {user_message.content}\n\n"
            f"Columns: {columns}\nRows: {rows}"
        )
    )
    summary = llm.invoke([summary_system, summary_user])

    # state.last_rows에 run_id가 들어있어야 replay_agent가 사용할 수 있음.
    return {
        "messages": [draft, summary],
        "active_agent": "row_agent",
        "last_rows": row_dicts,
    }
