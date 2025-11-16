import sqlite3
import os

"""
This module provides a simple utility to initialise the local SQLite database
used for storing LangSmith trace data in a unified schema.

  * `agent_runs` — one row per agent episode (identified by run_id).
  * `call_model` — one row per LLM call.
  * `call_tool` — one row per tool call.
  * `call_chain` — one row per chain/graph node call.
"""

# --- MODIFIED LINE ---
# This path is now relative to the CWD (which is /backend when you run uvicorn)
# This will place the DB next to main.py
DB_PATH = "agent_debug_db.sqlite"

# SQL DDL for the tables. We drop existing tables to ensure the schema
# matches exactly.
SCHEMA_SQL = """
DROP TABLE IF EXISTS agent_runs;
DROP TABLE IF EXISTS steps;
DROP TABLE IF EXISTS call_model;
DROP TABLE IF EXISTS call_tool;
DROP TABLE IF EXISTS call_chain;

CREATE TABLE agent_runs (
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
    runtime JSON,
    total_tokens INTEGER,
    total_cost REAL
);

CREATE TABLE call_model (
    step_id TEXT PRIMARY KEY,
    run_id TEXT,
    step_index INTEGER,
    previous_step_id TEXT,

    -- LLM step fields
    prompt_text TEXT,
    llm_output_text TEXT,
    llm_input_tokens INTEGER,
    llm_output_tokens INTEGER,
    llm_total_tokens INTEGER,
    llm_prompt_cost REAL,
    llm_completion_cost REAL,
    llm_total_cost REAL,
    finish_reason TEXT,
    model_name TEXT,
    model_provider TEXT,
    tool_call_requests JSON,

    FOREIGN KEY(run_id) REFERENCES agent_runs(run_id)
    -- Note: We cannot have a FOREIGN KEY on previous_step_id as it could
    -- reference any of the three 'call_*' tables.
);

CREATE TABLE call_tool (
    step_id TEXT PRIMARY KEY,
    run_id TEXT,
    step_index INTEGER,
    previous_step_id TEXT,

    -- Tool step fields
    tool_name TEXT,
    tool_args JSON,
    tool_status TEXT,
    tool_response TEXT,
    tool_message_content TEXT,
    tool_cost REAL,
    tool_latency_ms INTEGER,

    FOREIGN KEY(run_id) REFERENCES agent_runs(run_id)
);

CREATE TABLE call_chain (
    step_id TEXT PRIMARY KEY,
    run_id TEXT,
    step_index INTEGER,
    previous_step_id TEXT,

    -- Chain step fields
    chain_name TEXT,
    chain_status TEXT,
    chain_input_messages JSON,
    chain_output_messages JSON,
    chain_prompt_tokens INTEGER,
    chain_completion_tokens INTEGER,
    chain_total_tokens INTEGER,
    chain_prompt_cost REAL,
    chain_completion_cost REAL,
    chain_total_cost REAL,

    FOREIGN KEY(run_id) REFERENCES agent_runs(run_id)
);
"""


def ensure_schema(db_path: str = DB_PATH) -> None:
    """Create the SQLite database and schema if it does not already exist.

    This function is idempotent: existing tables will be replaced if the
    schema differs, but existing data will be dropped. In a production system
    you would instead apply migrations to avoid data loss.
    """
    # os.path.dirname("agent_debug_db.sqlite") is "" (empty string)
    # os.makedirs("", exist_ok=True) will do nothing, which is correct.
    dirname = os.path.dirname(db_path)
    if dirname:
        os.makedirs(dirname, exist_ok=True)

    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.executescript(SCHEMA_SQL)
    conn.commit()
    conn.close()
    print(f"Schema ensured at: {db_path}")


if __name__ == "__main__":
    ensure_schema()
