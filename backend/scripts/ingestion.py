import json
import os
import sqlite3
import uuid
from datetime import datetime
from typing import Any, Dict, List

# Make sure this import is correct based on your project structure
# If main.py is in the root, and this is in /scripts, it should be:
# from .create_db import ensure_schema, DB_PATH
from scripts.create_db import ensure_schema, DB_PATH


def safe_get(d: Dict[str, Any], path: List[Any], default: Any = None) -> Any:
    """Safely traverse nested dictionaries and lists.

    Given a dictionary `d` and a sequence of keys/indexes `path`, attempt to
    navigate the nested structure and return the value found. If any part of
    the path does not exist, return `default` instead of raising an error.
    """
    cur: Any = d
    for p in path:
        if isinstance(cur, dict):
            cur = cur.get(p, default)
        elif isinstance(cur, list) and isinstance(p, int) and 0 <= p < len(cur):
            cur = cur[p]
        else:
            return default
        if cur is None:
            return default
    return cur


def get_conn() -> sqlite3.Connection:
    """Get a SQLite connection without resetting existing tables.

    If the database file does not yet exist, this will call
    `ensure_schema()` once to create the tables. Unlike the previous
    implementation, we do not call `ensure_schema()` on every connection
    because that would drop and recreate the tables, losing data. Instead,
    this lazily initialises the schema only if needed.
    """
    # Only initialise schema if database file does not exist
    if not os.path.exists(DB_PATH):
        ensure_schema(DB_PATH)
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


def parse_llm_step(run: Dict[str, Any]) -> Dict[str, Any]:
    """Extract fields for an LLM step from a LangSmith run dict."""
    usage = {
        "input_tokens": run.get("prompt_tokens"),
        "output_tokens": run.get("completion_tokens"),
        "total_tokens": run.get("total_tokens"),
    }
    # Costs may be nested or separate. We attempt to pull from top level.
    costs = {
        "prompt_cost": run.get("prompt_cost"),
        "completion_cost": run.get("completion_cost"),
        "total_cost": run.get("total_cost"),
    }
    # Attempt to extract the first generation for finish reason and text.
    finish_reason = safe_get(
        run,
        ["outputs", "generations", 0, 0, "message", "kwargs", "response_metadata", "finish_reason"],
    )
    llm_output_text = safe_get(run, ["outputs", "generations", 0, 0, "text"])
    tool_call_requests = safe_get(
        run, ["outputs", "generations", 0, 0, "message", "kwargs", "tool_calls"], []
    )
    # Model metadata
    meta = safe_get(run, ["extra", "metadata"], {})
    return {
        "prompt_text": None,
        "llm_output_text": llm_output_text,
        "llm_input_tokens": usage["input_tokens"],
        "llm_output_tokens": usage["output_tokens"],
        "llm_total_tokens": usage["total_tokens"],
        "llm_prompt_cost": costs["prompt_cost"],
        "llm_completion_cost": costs["completion_cost"],
        "llm_total_cost": costs["total_cost"],
        "finish_reason": finish_reason,
        "model_name": meta.get("ls_model_name") or run.get("name"),  # Fallback to run name
        "model_provider": meta.get("ls_provider"),
        "tool_call_requests": tool_call_requests,
    }


def parse_tool_step(run: Dict[str, Any]) -> Dict[str, Any]:
    """Extract fields for a tool call step from a LangSmith run dict."""
    result: Dict[str, Any] = {}
    result["tool_name"] = run.get("name")
    # Parse tool arguments. They may be stored as a string representation of a dict.
    args_input = safe_get(run, ["inputs", "input"])
    if isinstance(args_input, str):
        # Attempt to normalise single quotes to double quotes for JSON parsing
        try:
            cleaned = args_input
            # Replace single quotes with double quotes around keys and strings
            # This is a best‑effort; if it fails we store the raw string
            result["tool_args"] = json.loads(cleaned.replace("'", '"'))
        except Exception:
            result["tool_args"] = args_input
    else:
        result["tool_args"] = args_input
    # Tool status and response content
    status = safe_get(run, ["outputs", "output", "status"])
    # Output may be nested JSON or plain string. For tools we assume a dict with 'content' field or string.
    output_obj = safe_get(run, ["outputs", "output"])
    if isinstance(output_obj, dict):
        response = output_obj.get("content")
    else:
        response = output_obj
    result["tool_status"] = status
    result["tool_response"] = response
    result["tool_message_content"] = response
    # Tool cost if provided
    result["tool_cost"] = run.get("total_cost")
    # Compute latency in milliseconds if timestamps parse
    try:
        # Timestamps might not have fractional seconds
        start_str = run["start_time"].split("+")[0]  # Remove timezone
        end_str = run["end_time"].split("+")[0]  # Remove timezone
        time_format = "%Y-%m-%d %H:%M:%S"
        if "." in start_str:
            time_format += ".%f"

        start = datetime.strptime(start_str, time_format)
        end = datetime.strptime(end_str, time_format)
        result["tool_latency_ms"] = int((end - start).total_seconds() * 1000)
    except Exception:
        result["tool_latency_ms"] = None
    return result


def parse_chain_step(run: Dict[str, Any]) -> Dict[str, Any]:
    """Extract fields for a chain step from a LangSmith run dict.

    A "chain" run in LangSmith represents a high‑level composition of
    sub‑runs (for example, a LangGraph node). Unlike pure LLM or tool
    runs, these objects encapsulate their own token usage and cost
    information.
    """

    # Helper to coerce values to int/float where appropriate
    def to_int(val: Any) -> Any:
        try:
            return int(val) if val is not None else None
        except Exception:
            return None

    def to_float(val: Any) -> Any:
        try:
            return float(val) if val is not None else None
        except Exception:
            return None

    result: Dict[str, Any] = {}
    # Chain‑specific fields
    result["chain_name"] = run.get("name")
    result["chain_status"] = run.get("status")
    result["chain_input_messages"] = safe_get(run, ["inputs", "messages"]) or safe_get(
        run, ["inputs", "input"]
    )
    result["chain_output_messages"] = safe_get(run, ["outputs", "messages"]) or safe_get(
        run, ["outputs", "output"]
    )
    result["chain_prompt_tokens"] = to_int(run.get("prompt_tokens"))
    result["chain_completion_tokens"] = to_int(run.get("completion_tokens"))
    result["chain_total_tokens"] = to_int(run.get("total_tokens"))
    result["chain_prompt_cost"] = to_float(run.get("prompt_cost"))
    result["chain_completion_cost"] = to_float(run.get("completion_cost"))
    result["chain_total_cost"] = to_float(run.get("total_cost"))
    return result


def ingest_session(runs: List[Dict[str, Any]], trace_id: str) -> None:
    """Ingest a list of LangSmith run dicts belonging to the same trace.

    This function aggregates the runs into a single agent_runs row identified
    by `trace_id` and inserts one row per run into the corresponding
    `call_model`, `call_tool`, or `call_chain` table.
    """
    if not runs:
        return

    # Find the root run (the one whose id matches the trace_id, or has no parent)
    root_run = next((r for r in runs if r.get("id") == trace_id), None)
    if not root_run:
        # Fallback: find run with no parent_run_ids or only trace_id in parent_run_ids
        root_run = next(
            (
                r
                for r in runs
                if not r.get("parent_run_ids") or r.get("parent_run_ids") == [trace_id]
            ),
            runs[0],  # As a last resort, just use the first run
        )

    # Sort runs chronologically by start_time for ordering
    # Add a fallback for runs that might be missing start_time
    sorted_runs = sorted(runs, key=lambda r: r.get("start_time") or "1970-01-01T00:00:00")

    start_time = root_run.get("start_time")
    end_time = root_run.get("end_time")
    session_id = root_run.get("session_id") or root_run.get("trace_id")
    name = root_run.get("name")

    # Determine status and collect error messages across ALL runs
    status = "success"
    error_messages: List[str] = []
    for run in sorted_runs:
        if run.get("status") == "error" or run.get("error"):
            status = "error"
            if run.get("error"):
                error_messages.append(str(run["error"]))
    error = "\n".join(error_messages) if error_messages else None

    # Get input from root and output from last run
    input_messages = safe_get(root_run, ["inputs", "input"]) or safe_get(
        root_run, ["inputs", "messages"]
    )
    output_messages = safe_get(root_run, ["outputs", "output"]) or safe_get(
        root_run, ["outputs", "messages"]
    )

    # Metadata and runtime from the root run
    meta = safe_get(root_run, ["extra", "metadata"], {})
    runtime_info = safe_get(root_run, ["extra", "runtime"], {})
    model_name = meta.get("ls_model_name")
    tags = root_run.get("tags")
    langgraph_metadata = meta

    # Aggregate total tokens and cost across ALL runs
    def parse_int(x: Any) -> int:
        try:
            return int(x)
        except Exception:
            return 0

    total_tokens = sum(parse_int(run.get("total_tokens")) for run in sorted_runs)

    def parse_cost(x: Any) -> float:
        try:
            return float(x)
        except Exception:
            return 0.0

    total_cost = sum(parse_cost(run.get("total_cost")) for run in sorted_runs)

    # Insert or replace the agent run row with run_id = trace_id
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        """INSERT OR REPLACE INTO agent_runs (
            run_id, name, start_time, end_time, status, error,
            user_id, session_id, thread_id, input_messages, output_messages,
            model_name, tags, langgraph_metadata, runtime,
            total_tokens, total_cost
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            trace_id,  # Use the common trace_id as the primary run_id
            name,
            start_time,
            end_time,
            status,
            error,
            None,
            session_id,
            None,
            json.dumps(input_messages) if input_messages is not None else None,
            json.dumps(output_messages) if output_messages is not None else None,
            model_name,
            json.dumps(tags) if tags is not None else None,
            json.dumps(langgraph_metadata) if langgraph_metadata is not None else None,
            json.dumps(runtime_info) if runtime_info is not None else None,
            total_tokens,
            total_cost,
        ),
    )

    # Build and insert step rows into their respective tables
    previous_step_id: str = None
    step_id_map = {r.get("id"): r for r in sorted_runs}

    # Find direct parent
    def get_direct_parent_id(run: Dict[str, Any]) -> str:
        parent_ids = run.get("parent_run_ids", [])
        if not parent_ids:
            return None
        # The direct parent is the last ID in the list that isn't the trace_id
        for parent_id in reversed(parent_ids):
            if parent_id != trace_id and parent_id in step_id_map:
                return parent_id
        return None

    for idx, run in enumerate(sorted_runs):
        step_id = run.get("id") or str(uuid.uuid4())
        run_type = run.get("run_type")

        # Use direct parent ID if available, otherwise fall back to chronological previous step
        parent_id = get_direct_parent_id(run) or previous_step_id

        # Common fields for all step types
        common_values = (
            step_id,
            trace_id,
            idx,
            parent_id,
            run.get("start_time"),  # <-- ADDED
            run.get("end_time"),  # <-- ADDED
        )

        if run_type == "llm":
            llm_fields = parse_llm_step(run)
            cur.execute(
                """INSERT OR REPLACE INTO call_model (
                    step_id, run_id, step_index, previous_step_id,
                    start_time, end_time,
                    prompt_text, llm_output_text,
                    llm_input_tokens, llm_output_tokens, llm_total_tokens,
                    llm_prompt_cost, llm_completion_cost, llm_total_cost,
                    finish_reason, model_name, model_provider,
                    tool_call_requests
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                common_values
                + (
                    llm_fields["prompt_text"],
                    llm_fields["llm_output_text"],
                    llm_fields["llm_input_tokens"],
                    llm_fields["llm_output_tokens"],
                    llm_fields["llm_total_tokens"],
                    llm_fields["llm_prompt_cost"],
                    llm_fields["llm_completion_cost"],
                    llm_fields["llm_total_cost"],
                    llm_fields["finish_reason"],
                    llm_fields["model_name"],
                    llm_fields["model_provider"],
                    (
                        json.dumps(llm_fields["tool_call_requests"])
                        if llm_fields["tool_call_requests"] is not None
                        else None
                    ),
                ),
            )
        elif run_type == "tool":
            tool_fields = parse_tool_step(run)
            cur.execute(
                """INSERT OR REPLACE INTO call_tool (
                    step_id, run_id, step_index, previous_step_id,
                    start_time, end_time,
                    tool_name, tool_args, tool_status,
                    tool_response, tool_message_content,
                    tool_cost, tool_latency_ms
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                common_values
                + (
                    tool_fields["tool_name"],
                    (
                        json.dumps(tool_fields["tool_args"])
                        if tool_fields["tool_args"] is not None
                        else None
                    ),
                    tool_fields["tool_status"],
                    tool_fields["tool_response"],
                    tool_fields["tool_message_content"],
                    tool_fields["tool_cost"],
                    tool_fields["tool_latency_ms"],
                ),
            )
        elif run_type == "chain":
            chain_fields = parse_chain_step(run)
            cur.execute(
                """INSERT OR REPLACE INTO call_chain (
                    step_id, run_id, step_index, previous_step_id,
                    start_time, end_time,
                    chain_name, chain_status, chain_input_messages, chain_output_messages,
                    chain_prompt_tokens, chain_completion_tokens, chain_total_tokens,
                    chain_prompt_cost, chain_completion_cost, chain_total_cost
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                common_values
                + (
                    chain_fields["chain_name"],
                    chain_fields["chain_status"],
                    (
                        json.dumps(chain_fields["chain_input_messages"])
                        if chain_fields["chain_input_messages"] is not None
                        else None
                    ),
                    (
                        json.dumps(chain_fields["chain_output_messages"])
                        if chain_fields["chain_output_messages"] is not None
                        else None
                    ),
                    chain_fields["chain_prompt_tokens"],
                    chain_fields["chain_completion_tokens"],
                    chain_fields["chain_total_tokens"],
                    chain_fields["chain_prompt_cost"],
                    chain_fields["chain_completion_cost"],
                    chain_fields["chain_total_cost"],
                ),
            )

        # This is for the *chronological* previous step, as a fallback
        previous_step_id = step_id

    conn.commit()
    conn.close()


def ingest_dict(data: dict) -> None:
    """High-level helper to ingest a JSON dictionary containing LangSmith runs.

    The file may contain a list of run objects, a single run object,
    or a dictionary containing a 'runs' key.
    """
    runs_list: List[Dict[str, Any]] = []
    if isinstance(data, dict):
        if "runs" in data and isinstance(data.get("runs"), list):
            # Handle format like the example: {"rule_id": ..., "runs": [...]}
            runs_list = data["runs"]
        else:
            # Handle format as a single run object
            runs_list = [data]
    elif isinstance(data, list):
        # Handle format as a flat list of runs
        runs_list = data
    else:
        print(f"Warning: Unrecognized JSON format in input data")
        return

    if not runs_list:
        print("No runs found to ingest.")
        return

    # *** MODIFIED SECTION ***
    # Group all runs by their 'trace_id'
    groups: Dict[str, List[Dict[str, Any]]] = {}
    for run in runs_list:
        trace_id = run.get("trace_id")
        if not trace_id:
            # Fallback for runs that might be missing a trace_id
            trace_id = run.get("id") or str(uuid.uuid4())
        groups.setdefault(trace_id, []).append(run)

    # Ingest each group using its trace_id
    for trace_id, group_runs in groups.items():
        ingest_session(group_runs, trace_id)


def ingest_file(json_path: str) -> None:
    """High-level helper to ingest a JSON file containing LangSmith runs.

    The file may contain a list of run objects, a single run object,
    or a dictionary containing a 'runs' key.
    """
    with open(json_path, "r") as f:
        data = json.load(f)
    ingest_dict(data)


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python ingestion.py <json_file>")
    else:
        ingest_file(sys.argv[1])
