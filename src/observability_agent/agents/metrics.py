"""Metrics agent for Text2SQL analytics queries."""

from langchain_core.messages import HumanMessage, SystemMessage

from ..core.state import ObsState
from ..tools.schema import get_observability_schema
from ..tools.database import run_sql
from ..utils.sql_parser import extract_sql_from_text


def metrics_agent_node(state: ObsState, llm) -> ObsState:
    """
    자연어 → SQL 생성 → run_sql → 결과 요약.

    Handles metrics and analytics queries by:
    1. Converting natural language to SQL
    2. Executing the query
    3. Summarizing results for the user

    Args:
        state: Current observability state
        llm: Language model instance

    Returns:
        Updated state with agent responses and data
    """
    schema = get_observability_schema()
    user_message = state["messages"][-1]

    system = SystemMessage(
        content=(
            "You are an expert observability & SQL analytics agent.\n"
            "You will:\n"
            "1) Read the database schema.\n"
            "2) Convert the user's question into a single safe SQL query.\n"
            "3) The query MUST be read-only and MUST include a LIMIT when selecting rows.\n"
            "4) Return your answer in this format:\n"
            "   - First, explain your reasoning briefly.\n"
            "   - Then output the final SQL query inside a ```sql ... ``` block.\n\n"
            f"Database schema:\n{schema}"
        )
    )

    # 1st LLM call: 자연어 → SQL
    messages = [system] + state["messages"]
    draft = llm.invoke(messages)
    sql = extract_sql_from_text(draft.content)

    # 2nd: SQL 실행 (stub) + 결과를 다시 LLM으로 요약하게 하기
    sql_result = run_sql(sql)  # {"columns": [...], "rows": [...]}

    # rows를 dict 리스트로 변환해서 state에 저장
    columns = sql_result["columns"]
    rows = sql_result["rows"]
    row_dicts = [
        {col: value for col, value in zip(columns, row)}
        for row in rows
    ]

    # 결과 요약 프롬프트
    result_system = SystemMessage(
        content=(
            "You are an observability analyst. The user asked a metrics question.\n"
            "You are given:\n"
            "1) The SQL you executed.\n"
            "2) The result rows.\n\n"
            "Summarize the answer clearly for the user.\n"
            "- If it's a ranking, mention the top entries.\n"
            "- If there are many rows, summarize the most important ones.\n"
            "- You may also suggest follow-up questions the user can ask."
        )
    )
    result_user = HumanMessage(
        content=(
            f"User question: {user_message.content}\n\n"
            f"Executed SQL:\n{sql}\n\n"
            f"Result columns: {columns}\n"
            f"Result rows: {rows}"
        )
    )
    summary = llm.invoke([result_system, result_user])

    return {
        "messages": [draft, summary],  # SQL 생성 답변 + 요약 답변 모두 추가
        "active_agent": "metrics_agent",
        "last_rows": row_dicts,
    }
