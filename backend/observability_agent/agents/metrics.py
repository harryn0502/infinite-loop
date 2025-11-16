"""Metrics agent for Text2SQL analytics queries."""

import re
from typing import List, Optional, Tuple

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_core.runnables import RunnableConfig

from ..core.state import ObsState
from ..tools import (
    get_observability_schema_tool,
    run_sql_tool,
)
from .schemas import MetricsSQLResponse, MetricsSummaryResponse

MAX_METADATA_ROWS = 20
MAX_SQL_ATTEMPTS = 3
FORBIDDEN_DML = re.compile(r"\b(insert|update|delete|drop|create|replace)\b", re.IGNORECASE)
ALLOWED_TABLES = ("agent_runs", "call_model", "call_tool", "call_chain")


def _normalize_sql(sql: str) -> str:
    """Auto-fix common incompatibilities."""
    normalized = re.sub(r"(?i)string_agg", "GROUP_CONCAT", sql)

    def _strip_distinct_delimiter(match: re.Match) -> str:
        column = match.group(1)
        return f"GROUP_CONCAT(DISTINCT {column})"

    normalized = re.sub(
        r"GROUP_CONCAT\s*\(\s*DISTINCT\s+([^)]+?),\s*[^)]+?\)",
        _strip_distinct_delimiter,
        normalized,
        flags=re.IGNORECASE,
    )
    return normalized


def _validate_sql(sql: str) -> List[str]:
    """Check SQL for obvious problems before execution."""
    issues: List[str] = []
    lowered = sql.lower()

    if not any(re.search(fr"\b(from|join)\s+{table}\b", lowered) for table in ALLOWED_TABLES):
        issues.append("Query must reference at least one real table (agent_runs, call_model, call_tool, call_chain).")

    if re.search(r"\bvalues\s*\(", lowered):
        issues.append("VALUES clauses are not allowed; query real tables instead of fabricating data.")

    if re.search(r"\bunion\s+all\s+select\s+'", lowered):
        issues.append("Do not union fabricated literals; read from actual tables.")

    if FORBIDDEN_DML.search(lowered):
        issues.append("Only read-only SELECT queries are allowed.")

    if re.search(r"\bstring_agg\b", lowered):
        issues.append("SQLite does not support STRING_AGG; use GROUP_CONCAT.")

    return issues


def _build_sql_message(sql_response: MetricsSQLResponse, sql: str, user_text: str) -> Tuple[AIMessage, dict]:
    reasoning = sql_response.reasoning or "Model did not supply reasoning."
    sql_metadata = {
        "agent": "metrics_agent",
        "stage": "sql_generation",
        "sql_query": sql,
        "user_request": user_text,
        "schema_source": "observability_db",
    }
    draft = AIMessage(
        content=f"**Reasoning:** {reasoning}\n\n```sql\n{sql}\n```",
        additional_kwargs={
            "reasoning": reasoning,
            "agent_metadata": sql_metadata,
        }
    )
    return draft, sql_metadata


def _attempt_sql_execution(
    initial_response: MetricsSQLResponse,
    llm_with_structure,
    base_messages: List,
    user_text: str,
    sql_tool,
    config: Optional[RunnableConfig],
) -> Tuple[str, Optional[dict], MetricsSQLResponse, Optional[str]]:
    """Try to execute SQL, repairing it with feedback when necessary."""
    sql_response = initial_response
    sql = sql_response.sql_query
    last_error: Optional[str] = None

    for attempt in range(1, MAX_SQL_ATTEMPTS + 1):
        sql = _normalize_sql(sql)
        validation_errors = _validate_sql(sql)

        if not validation_errors:
            try:
                result = sql_tool.invoke({"sql": sql}, config=config)
                return sql, result, sql_response, None
            except Exception as exc:
                last_error = f"Database error: {exc}"
        else:
            last_error = "Validation errors:\n- " + "\n- ".join(validation_errors)

        if attempt == MAX_SQL_ATTEMPTS:
            break

        repair_feedback = (
            f"The previous SQL was invalid.\n\nSQL:\n{sql}\n\n"
            f"Issue:\n{last_error}\n\n"
            "Please return ONLY a corrected SQLite SELECT query. "
            "You must query the real tables (agent_runs, call_model, call_tool, call_chain) defined in the schema, "
            "never fabricate data with VALUES or literals, and keep the query read-only."
        )
        repair_messages = base_messages + [HumanMessage(content=repair_feedback)]
        sql_response = llm_with_structure.invoke(repair_messages)
        sql = sql_response.sql_query

    return sql, None, sql_response, last_error


def metrics_agent_node(state: ObsState, llm, config: Optional[RunnableConfig] = None) -> ObsState:
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
    schema = get_observability_schema_tool.invoke({}, config=config)
    user_message = state["messages"][-1]
    plan_steps = state.get("plan", []) or []
    plan_index = state.get("plan_step_index", 0)
    planner_step = plan_steps[plan_index] if plan_steps and plan_index < len(plan_steps) else None
    planner_hint = None
    if planner_step:
        planner_hint = HumanMessage(
            content=(
                "Planner instruction for this step:\n"
                f"Objective: {planner_step.get('objective', '')}\n"
                f"Required context: {planner_step.get('input_context', '')}\n"
                f"Success criteria: {planner_step.get('success_criteria', '')}"
            )
        )

    system = SystemMessage(
        content=(
            "You are an expert observability & SQL analytics agent.\n"
            "You will:\n"
            "1) Read the database schema.\n"
            "2) Convert the user's question into a single safe SQL query.\n"
            "3) The query MUST be read-only and MUST include a LIMIT when selecting rows.\n"
            "4) Return a structured response with:\n"
            "   - sql_query: The complete SQL query to execute\n"
            "   - reasoning: Brief explanation of why this query was chosen and what it does\n\n"
            "CRITICAL SQL RULES:\n"
            "- Only use tables and columns that exist in the schema (agent_runs, call_model, call_tool, call_chain).\n"
            "- NEVER fabricate data with VALUES clauses or temporary tables filled with hardcoded rows.\n"
            "- This database is SQLite. Use GROUP_CONCAT instead of STRING_AGG and avoid unsupported functions.\n"
            "- Use json_extract when reading JSON columns.\n\n"
            f"Database schema:\n{schema}"
        )
    )

    # 1st LLM call: 자연어 → SQL with structured output
    planner_messages = [planner_hint] if planner_hint else []
    messages = [system] + planner_messages + state["messages"]
    llm_with_structure = llm.with_structured_output(MetricsSQLResponse)
    sql_response = llm_with_structure.invoke(messages)

    sql, sql_result, sql_response, last_error = _attempt_sql_execution(
        sql_response,
        llm_with_structure,
        messages,
        user_message.content,
        run_sql_tool,
        config,
    )

    draft, sql_generation_metadata = _build_sql_message(sql_response, sql, user_message.content)

    if sql_result is None:
        error_metadata = {
            "agent": "metrics_agent",
            "stage": "sql_execution_error",
            "sql_query": sql,
            "error_message": last_error or "Unknown SQL error",
        }
        error_msg = AIMessage(
            content=(
                "I attempted multiple fixes but the database continues to reject the SQL:\n\n"
                f"```sql\n{sql}\n```\n\n"
                f"Error details: {last_error}\n\n"
                "Please adjust the question or try a simpler aggregation."
            ),
            additional_kwargs={
                "agent_metadata": error_metadata,
            },
        )
        return {
            "messages": [draft, error_msg],
            "active_agent": "metrics_agent",
            "last_rows": state.get("last_rows", []),
            "chart_context": state.get("chart_context", {"rows": state.get("last_rows", []), "metadata": {}}),
            "plan": plan_steps,
            "plan_step_index": plan_index + 1,
        }

    # rows를 dict 리스트로 변환해서 state에 저장
    columns = sql_result["columns"]
    rows = sql_result["rows"]
    query_metadata = sql_result.get("metadata", {})
    row_dicts = [
        {col: value for col, value in zip(columns, row)}
        for row in rows
    ]

    chart_context = {
        "rows": row_dicts,
        "metadata": {},
        "raw_rows": row_dicts,
    }

    # 결과 요약 프롬프트 with structured output
    result_system = SystemMessage(
        content=(
            "You are an observability analyst. The user asked a metrics question.\n"
            "You are given:\n"
            "1) The SQL you executed.\n"
            "2) The result rows.\n\n"
            "Return a structured response with:\n"
            "- summary: Clear answer for the user. If it's a ranking, mention top entries. "
            "If there are many rows, summarize the most important ones. "
            "IMPORTANT: If the query returns multiple runs/rows, number them (1, 2, 3, ...) "
            "so the user can refer back to specific rows later. "
            "You may also suggest follow-up questions.\n"
            "- reasoning: Brief explanation of how you interpreted and summarized the results"
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

    llm_with_summary = llm.with_structured_output(MetricsSummaryResponse)
    summary_response = llm_with_summary.invoke([result_system, result_user])

    summary_metadata = {
        "agent": "metrics_agent",
        "stage": "summary",
        "sql_query": sql,
        "row_count": len(rows),
        "columns": columns,
        "rows_preview": row_dicts[:MAX_METADATA_ROWS],
        "query_metadata": query_metadata,
        "chart_metadata": chart_context["metadata"],
    }

    summary = AIMessage(
        content=summary_response.summary,
        additional_kwargs={
            "reasoning": summary_response.reasoning,
            "agent_metadata": summary_metadata,
        }
    )

    return {
        "messages": [draft, summary],  # SQL 생성 답변 + 요약 답변 모두 추가
        "active_agent": "metrics_agent",
        "last_rows": row_dicts,
        "chart_context": chart_context,
        "plan": plan_steps,
        "plan_step_index": plan_index + 1,
    }
