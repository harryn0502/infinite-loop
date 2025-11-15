# create_db.py
import sqlite3
import os

DB_PATH = "data/agent_debug_db.sqlite"

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS agent_runs (
    run_id TEXT PRIMARY KEY,
    start_time TEXT,
    end_time TEXT,
    status TEXT,
    error TEXT,
    user_id TEXT,
    session_id TEXT,
    thread_id TEXT,
    input_messages JSON,
    output_messages JSON,
    model_name TEXT,
    tags JSON,
    langgraph_metadata JSON,
    total_tokens INTEGER,
    total_cost REAL
);

CREATE TABLE IF NOT EXISTS llm_calls (
    llm_call_id TEXT PRIMARY KEY,
    run_id TEXT,
    step_index INTEGER,
    prompt_text TEXT,
    finish_reason TEXT,
    model_name TEXT,
    model_provider TEXT,
    usage_metadata JSON,
    tool_call_requests JSON,
    llm_output_text TEXT,
    error_flag INTEGER,
    FOREIGN KEY(run_id) REFERENCES agent_runs(run_id)
);

CREATE TABLE IF NOT EXISTS tool_calls (
    tool_call_id TEXT PRIMARY KEY,
    run_id TEXT,
    llm_call_id TEXT,
    tool_name TEXT,
    tool_args JSON,
    tool_status TEXT,
    tool_response TEXT,
    tool_message_content TEXT,
    execution_latency_ms INTEGER,
    is_tool_error INTEGER,
    error_type TEXT,
    FOREIGN KEY(run_id) REFERENCES agent_runs(run_id),
    FOREIGN KEY(llm_call_id) REFERENCES llm_calls(llm_call_id)
);
"""

def ensure_schema(db_path: str = DB_PATH):
    """Create DB + schema if missing. If DB exists, ensure tables exist."""
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.executescript(SCHEMA_SQL)
    conn.commit()
    conn.close()
