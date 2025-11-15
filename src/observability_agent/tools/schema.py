"""Database schema definition for observability tools."""


def get_observability_schema() -> str:
    """
    Text2SQL agent가 참고할 DB 스키마를 문자열로 리턴.

    Returns a PostgreSQL schema description for:
    - runs: Agent execution records
    - tool_calls: Tool invocation logs
    - traces: Detailed trace events

    Returns:
        Schema description as a formatted string
    """
    schema = """
    We have a PostgreSQL database with the following tables:

    Table: runs
      - run_id TEXT PRIMARY KEY
      - project TEXT
      - agent_name TEXT
      - started_at TIMESTAMP
      - finished_at TIMESTAMP
      - latency_ms INTEGER
      - total_tokens INTEGER
      - input_tokens INTEGER
      - output_tokens INTEGER
      - error_flag BOOLEAN

    Table: tool_calls
      - id SERIAL PRIMARY KEY
      - run_id TEXT REFERENCES runs(run_id)
      - tool_name TEXT
      - started_at TIMESTAMP
      - latency_ms INTEGER
      - input_tokens INTEGER
      - output_tokens INTEGER
      - error_flag BOOLEAN

    Table: traces
      - trace_id TEXT PRIMARY KEY
      - run_id TEXT REFERENCES runs(run_id)
      - step_index INTEGER
      - event_type TEXT
      - timestamp TIMESTAMP
      - detail JSONB

    This database is READ-ONLY for the agent. The agent must:
      - Always add a LIMIT when selecting rows.
      - Prefer filtering by time (started_at) or project when possible.
    """
    return schema.strip()
