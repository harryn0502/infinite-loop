"""Database schema definition for observability tools."""

import sqlite3
from functools import lru_cache
from typing import Dict, List
from langchain_core.tools import StructuredTool

from .database import DB_PATH

TABLE_DESCRIPTIONS: Dict[str, str] = {
    "agent_runs": (
        "Agent-level metadata. Use for run status, user/session IDs, timings, "
        "and tags. Join with call_* tables on run_id."
    ),
    "call_model": (
        "LLM calls executed within the run. Contains tokens, costs, prompt text, "
        "and model metadata."
    ),
    "call_tool": (
        "All tool invocations (think_tool, search_tool, etc). Contains tool_name, "
        "arguments, status, response text, and tool_latency_ms."
    ),
    "call_chain": (
        "Higher-level chain executions (LangGraph/LangChain). Useful for tracing "
        "chain-level token usage and messages."
    ),
}


def _fetch_columns(table: str) -> List[Dict[str, str]]:
    try:
        conn = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute(f"PRAGMA table_info({table})")
        rows = cursor.fetchall()
        cursor.close()
        conn.close()
        return [{"name": row["name"], "type": row["type"]} for row in rows]
    except Exception:
        return []


def _format_table_section(table: str) -> str:
    columns = _fetch_columns(table)
    column_lines = "\n".join(
        f"      - {col['name']} {col['type'] or ''}".rstrip() for col in columns
    ) or "      - (no columns fetched)"
    description = TABLE_DESCRIPTIONS.get(table, "")
    desc_line = f"    Description: {description}\n" if description else ""
    return (
        f"    Table: {table}\n"
        f"{desc_line}"
        f"    Columns:\n{column_lines}\n"
    )


@lru_cache(maxsize=1)
def get_observability_schema() -> str:
    """
    Returns DB schema as a string for Text2SQL agent reference.

    Returns:
        Schema description as a formatted string
    """
    table_sections = "\n".join(_format_table_section(tbl) for tbl in TABLE_DESCRIPTIONS)

    guidance = """
    IMPORTANT NOTES:
    1. This database is READ-ONLY. Only SELECT queries are allowed.
    2. ALWAYS add a LIMIT clause when selecting rows (e.g., LIMIT 100).
    3. Table usage:
       - Use call_model for LLM reasoning/token usage queries
       - Use call_tool for tool latency/errors/arguments
       - Use call_chain for higher-level chain executions
    4. Time calculations (latency):
       - Run latency: (julianday(end_time) - julianday(start_time)) * 86400000 AS latency_ms
       - Tool latency: call_tool.tool_latency_ms (already calculated)
       - Model latency: julianday(end_time)-julianday(start_time) on call_model
    5. JSON field access (SQLite):
       - Extract from arrays: json_extract(tags, '$[0]')
       - Extract from objects: json_extract(tool_args, '$.param_name')
    6. Common queries:
       - Filter by time: WHERE start_time > date('now', '-7 days')
       - Filter by status: WHERE status = 'success' OR status = 'error'
       - Join example: SELECT r.run_id, m.step_id FROM agent_runs r JOIN call_model m ON r.run_id = m.run_id
       - Get tools with high latency: SELECT tool_name, tool_latency_ms FROM call_tool ORDER BY tool_latency_ms DESC
    7. Calculate token ratios:
       - Output/Input ratio for LLM calls (call_model table):
         CAST(llm_output_tokens AS REAL) / CAST(llm_input_tokens AS REAL)
    """

    schema = f"We have a SQLite database with the following tables:\n\n{table_sections}\n{guidance}"
    return schema.strip()


def _fetch_schema_tool() -> str:
    return get_observability_schema()


get_observability_schema_tool = StructuredTool.from_function(
    func=_fetch_schema_tool,
    name="get_observability_schema",
    description="Return the latest observability database schema description for Text2SQL prompts.",
)
