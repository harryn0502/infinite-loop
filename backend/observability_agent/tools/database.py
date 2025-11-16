"""Database query execution tools (SQLite implementation)."""

import sqlite3
import re
import time
from datetime import datetime, timezone
from typing import Dict, Any, Optional
from pathlib import Path
from langchain_core.tools import StructuredTool


# Database path relative to project root
DB_PATH = Path("/app/data/agent_debug_db.sqlite")


def _ensure_limit(sql: str, default_limit: int = 100) -> str:
    """
    Ensure SQL query has a LIMIT clause for safety.

    Args:
        sql: SQL query string
        default_limit: Default limit to add if none exists

    Returns:
        SQL with LIMIT clause
    """
    # Check if LIMIT already exists (case-insensitive)
    if not re.search(r"\bLIMIT\b", sql, re.IGNORECASE):
        # Add LIMIT at the end
        sql = sql.rstrip(";").strip() + f" LIMIT {default_limit}"
    return sql


def _extract_limit_value(sql: str) -> Optional[int]:
    """Extract LIMIT value if present."""
    match = re.search(r"\bLIMIT\s+(\d+)", sql, re.IGNORECASE)
    if match:
        try:
            return int(match.group(1))
        except (TypeError, ValueError):
            return None
    return None


def run_sql(sql: str) -> Dict[str, Any]:
    """
    Execute SQL query on SQLite database and return results.

    Connects to the observability SQLite database and executes
    the provided SQL query in READ-ONLY mode for safety.

    Args:
        sql: SQL query string to execute (SELECT only)

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

    Raises:
        sqlite3.Error: If query execution fails
        FileNotFoundError: If database file doesn't exist
    """
    # Check database exists
    if not DB_PATH.exists():
        raise FileNotFoundError(
            f"Database not found at {DB_PATH}. " f"Expected: backend/agent_debug_db.sqlite"
        )

    original_sql = sql
    had_limit = bool(re.search(r"\bLIMIT\b", original_sql, re.IGNORECASE))

    # Ensure query has LIMIT for safety
    sql = _ensure_limit(sql)

    print("Executing SQL:")
    print(sql)
    print("--------")

    try:
        # Connect in READ-ONLY mode
        conn = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
        cursor = conn.cursor()

        # Execute query and capture latency
        start_time = time.perf_counter()
        cursor.execute(sql)

        # Get column names
        columns = [desc[0] for desc in cursor.description] if cursor.description else []

        # Fetch all rows
        rows = cursor.fetchall()
        latency_ms = (time.perf_counter() - start_time) * 1000.0

        # Close connection
        cursor.close()
        conn.close()

        print(f"Retrieved {len(rows)} rows")
        print("--------")

        query_metadata = {
            "executed_sql": sql,
            "original_sql": original_sql,
            "rows_returned": len(rows),
            "columns_returned": len(columns),
            "limit_applied": bool(re.search(r"\bLIMIT\b", sql, re.IGNORECASE)),
            "auto_limit_added": not had_limit,
            "limit_value": _extract_limit_value(sql),
            "execution_ms": round(latency_ms, 3),
            "database_path": str(DB_PATH),
            "queried_at": datetime.now(timezone.utc).isoformat(),
        }

        return {
            "columns": columns,
            "rows": rows,
            "metadata": query_metadata,
        }

    except sqlite3.Error as e:
        print(f"SQL Error: {e}")
        print("--------")
        raise


def _run_sql_tool(sql: str) -> Dict[str, Any]:
    """Wrapper so run_sql can be exposed as a LangChain tool."""
    return run_sql(sql)


run_sql_tool = StructuredTool.from_function(
    func=_run_sql_tool,
    name="run_sql",
    description=(
        "Execute a read-only SQL query against the observability SQLite database "
        "and return columns, rows, and metadata."
    ),
)
