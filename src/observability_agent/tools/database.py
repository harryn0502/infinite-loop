"""Database query execution tools (stub implementation)."""

from typing import Dict, Any


def run_sql(sql: str) -> Dict[str, Any]:
    """
    Execute SQL query and return results.

    This is a stub implementation that returns demo data.
    In production, this should connect to an actual database.

    Args:
        sql: SQL query string to execute

    Returns:
        Dictionary with 'columns' and 'rows' keys:
        {
            "columns": ["col1", "col2", ...],
            "rows": [
                [value1, value2, ...],
                [value1, value2, ...],
                ...
            ]
        }
    """
    print("Executing SQL (stub):")
    print(sql)
    print("--------")

    # 데모를 위해 질문 유형 상관없이 고정된 예시 row 반환
    return {
        "columns": ["tool_name", "avg_latency_ms", "calls"],
        "rows": [
            ["search_tool", 120.5, 32],
            ["db_tool", 250.0, 12],
            ["email_tool", 95.3, 7],
        ],
    }
