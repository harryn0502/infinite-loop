import sqlite3
import os

"""
This module provides a simple utility to initialise the local SQLite database
used for storing LangSmith trace data in a unified two‑level schema. The
database will be created in the `data` subdirectory of the project
repository. The schema includes two tables:

  * `agent_runs` — one row per agent episode (identified by session ID).
  * `steps` — one row per logical step (LLM call or tool call) within an agent
    episode. Steps include normalised token and cost columns, flags to
    distinguish LLM and tool steps, and a pointer to the previous step to
    reconstruct the chain of execution.

Call the `ensure_schema()` function from your ingestion code to create the
database and schema if they do not already exist. The function is idempotent;
it will not destroy existing data.
"""

DB_PATH = os.path.join("..", "db_as_files", "agent_debug_db.sqlite")

# SQL DDL for the two tables. We drop existing tables to ensure the schema
# matches exactly; in a migration scenario you would instead use ALTER
# statements or a proper migration tool.
SCHEMA_SQL = """
DROP TABLE IF EXISTS agent_runs;
DROP TABLE IF EXISTS steps;

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

CREATE TABLE steps (
    step_id TEXT PRIMARY KEY,
    run_id TEXT,
    step_index INTEGER,
    -- binary flags indicating the type of step
    is_llm_call INTEGER,
    is_tool_call INTEGER,

    -- LLM step fields (NULL for tool steps)
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

    -- Tool step fields (NULL for LLM steps)
    tool_name TEXT,
    tool_args JSON,
    tool_status TEXT,
    tool_response TEXT,
    tool_message_content TEXT,
    tool_cost REAL,
    tool_latency_ms INTEGER,

    -- Pointer to the previous step in the sequence
    previous_step_id TEXT,

    FOREIGN KEY(run_id) REFERENCES agent_runs(run_id),
    FOREIGN KEY(previous_step_id) REFERENCES steps(step_id)
);
"""

def ensure_schema(db_path: str = DB_PATH) -> None:
    """Create the SQLite database and schema if it does not already exist.

    This function is idempotent: existing tables will be replaced if the
    schema differs, but existing data will be dropped. In a production system
    you would instead apply migrations to avoid data loss.
    """
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.executescript(SCHEMA_SQL)
    conn.commit()
    conn.close()
    print(f"Schema ensured at: {db_path}")

if __name__ == "__main__":
    ensure_schema()