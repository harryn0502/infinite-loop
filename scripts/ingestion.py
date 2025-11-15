import json
import os
import sqlite3
import uuid
from datetime import datetime
from typing import Any, Dict, List

from create_db import ensure_schema, DB_PATH

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
    """Get a SQLite connection, ensuring the schema exists first."""
    # Ensure the schema is present before opening the connection. This call is
    # idempotent and will initialise the database if it does not yet exist.
    ensure_schema(DB_PATH)
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


def parse_llm_step(run: Dict[str, Any]) -> Dict[str, Any]:
    """Extract fields for an LLM step from a LangSmith run dict."""
    usage = {
        'input_tokens': run.get('prompt_tokens'),
        'output_tokens': run.get('completion_tokens'),
        'total_tokens': run.get('total_tokens'),
    }
    # Costs may be nested or separate. We attempt to pull from top level.
    costs = {
        'prompt_cost': run.get('prompt_cost'),
        'completion_cost': run.get('completion_cost'),
        'total_cost': run.get('total_cost'),
    }
    # Attempt to extract the first generation for finish reason and text.
    finish_reason = safe_get(run, ['outputs', 'generations', 0, 0, 'message', 'kwargs', 'response_metadata', 'finish_reason'])
    llm_output_text = safe_get(run, ['outputs', 'generations', 0, 0, 'text'])
    tool_call_requests = safe_get(run, ['outputs', 'generations', 0, 0, 'message', 'kwargs', 'tool_calls'], [])
    # Model metadata
    meta = safe_get(run, ['extra', 'metadata'], {})
    return {
        'prompt_text': None,
        'llm_output_text': llm_output_text,
        'llm_input_tokens': usage['input_tokens'],
        'llm_output_tokens': usage['output_tokens'],
        'llm_total_tokens': usage['total_tokens'],
        'llm_prompt_cost': costs['prompt_cost'],
        'llm_completion_cost': costs['completion_cost'],
        'llm_total_cost': costs['total_cost'],
        'finish_reason': finish_reason,
        'model_name': meta.get('ls_model_name'),
        'model_provider': meta.get('ls_provider'),
        'tool_call_requests': tool_call_requests,
    }


def parse_tool_step(run: Dict[str, Any]) -> Dict[str, Any]:
    """Extract fields for a tool call step from a LangSmith run dict."""
    result: Dict[str, Any] = {}
    result['tool_name'] = run.get('name')
    # Parse tool arguments. They may be stored as a string representation of a dict.
    args_input = safe_get(run, ['inputs', 'input'])
    if isinstance(args_input, str):
        # Attempt to normalise single quotes to double quotes for JSON parsing
        try:
            cleaned = args_input
            # Replace single quotes with double quotes around keys and strings
            # This is a best‑effort; if it fails we store the raw string
            result['tool_args'] = json.loads(cleaned.replace("'", '"'))
        except Exception:
            result['tool_args'] = args_input
    else:
        result['tool_args'] = args_input
    # Tool status and response content
    status = safe_get(run, ['outputs', 'output', 'status'])
    # Output may be nested JSON or plain string. For tools we assume a dict with 'content' field or string.
    output_obj = safe_get(run, ['outputs', 'output'])
    if isinstance(output_obj, dict):
        response = output_obj.get('content')
    else:
        response = output_obj
    result['tool_status'] = status
    result['tool_response'] = response
    result['tool_message_content'] = response
    # Tool cost if provided
    result['tool_cost'] = run.get('total_cost')
    # Compute latency in milliseconds if timestamps parse
    try:
        start = datetime.strptime(run['start_time'], '%Y-%m-%d %H:%M:%S.%f')
        end = datetime.strptime(run['end_time'], '%Y-%m-%d %H:%M:%S.%f')
        result['tool_latency_ms'] = int((end - start).total_seconds() * 1000)
    except Exception:
        result['tool_latency_ms'] = None
    return result


def ingest_session(runs: List[Dict[str, Any]]) -> None:
    """Ingest a list of LangSmith run dicts belonging to the same session.

    This function groups runs by session and writes a single agent_runs row along
    with one steps row per run in temporal order. The session ID is used as
    the `run_id` primary key for the agent_runs table. If the session_id is
    missing, the trace_id or a generated UUID will be used instead.
    """
    if not runs:
        return
    # Determine a key for this agent run. Prefer the session_id if present.
    session_id = runs[0].get('session_id') or runs[0].get('trace_id') or str(uuid.uuid4())
    # Compute aggregate fields for the agent run
    # Sort runs by start_time for chronological info
    sorted_runs = sorted(runs, key=lambda r: r.get('start_time'))
    start_time = sorted_runs[0].get('start_time')
    end_time = sorted_runs[-1].get('end_time')
    # Determine status: if any run errored, mark agent run as error
    status = 'success'
    error_messages = []
    for run in sorted_runs:
        if run.get('status') == 'error' or run.get('error'):
            status = 'error'
            if run.get('error'):
                error_messages.append(str(run['error']))
    error = '\n'.join(error_messages) if error_messages else None
    # Gather input and output messages from first and last LLM runs if available
    first_llm = next((r for r in sorted_runs if r.get('run_type') == 'llm'), None)
    last_llm = next((r for r in reversed(sorted_runs) if r.get('run_type') == 'llm'), None)
    input_messages = safe_get(first_llm or sorted_runs[0], ['inputs', 'messages'])
    output_messages = safe_get(last_llm or sorted_runs[-1], ['outputs', 'generations'])
    # Metadata from the first run
    meta = safe_get(sorted_runs[0], ['extra', 'metadata'], {})
    runtime_info = safe_get(sorted_runs[0], ['extra', 'runtime'], {})
    model_name = meta.get('ls_model_name')
    tags = sorted_runs[0].get('tags')
    langgraph_metadata = meta
    # Aggregate token and cost at the agent level (sum across runs where available)
    # Coerce token counts to integers where possible
    def parse_int(x: Any) -> int:
        try:
            return int(x)
        except Exception:
            return 0
    total_tokens = sum(parse_int(run.get('total_tokens')) for run in sorted_runs)
    # Sum costs, coercing to float where possible
    def parse_cost(x: Any) -> float:
        try:
            return float(x)
        except Exception:
            return 0.0
    total_cost = sum(parse_cost(run.get('total_cost')) for run in sorted_runs)
    # Insert the agent run
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        """INSERT OR REPLACE INTO agent_runs (
            run_id, start_time, end_time, status, error,
            user_id, session_id, thread_id, input_messages, output_messages,
            model_name, tags, langgraph_metadata, runtime,
            total_tokens, total_cost
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            session_id,
            start_time,
            end_time,
            status,
            error,
            None,  # user_id (not present in input)
            session_id,
            None,  # thread_id (not present at run level)
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
    # Build and insert steps
    previous_step_id: str = None
    for idx, run in enumerate(sorted_runs):
        step_id = run.get('id') or str(uuid.uuid4())
        is_llm = 1 if run.get('run_type') == 'llm' else 0
        is_tool = 1 if run.get('run_type') == 'tool' else 0
        is_chain = 1 if run.get('run_type') == 'chain' else 0
        # Base fields
        step_data = {
            'step_id': step_id,
            'run_id': session_id,
            'step_index': idx,
            'is_llm_call': is_llm,
            'is_tool_call': is_tool,
            # LLM fields default to None
            'prompt_text': None,
            'llm_output_text': None,
            'llm_input_tokens': None,
            'llm_output_tokens': None,
            'llm_total_tokens': None,
            'llm_prompt_cost': None,
            'llm_completion_cost': None,
            'llm_total_cost': None,
            'finish_reason': None,
            'model_name': None,
            'model_provider': None,
            'tool_call_requests': None,
            # Tool fields default to None
            'tool_name': None,
            'tool_args': None,
            'tool_status': None,
            'tool_response': None,
            'tool_message_content': None,
            'tool_cost': None,
            'tool_latency_ms': None,
            'previous_step_id': previous_step_id,
        }
        if is_llm:
            llm_fields = parse_llm_step(run)
            step_data.update(llm_fields)
        if is_tool:
            tool_fields = parse_tool_step(run)
            step_data.update(tool_fields)
        # Insert this step into the database
        cur.execute(
            """INSERT OR REPLACE INTO steps (
                step_id, run_id, step_index,
                is_llm_call, is_tool_call,
                prompt_text, llm_output_text,
                llm_input_tokens, llm_output_tokens, llm_total_tokens,
                llm_prompt_cost, llm_completion_cost, llm_total_cost,
                finish_reason, model_name, model_provider,
                tool_call_requests,
                tool_name, tool_args, tool_status,
                tool_response, tool_message_content,
                tool_cost, tool_latency_ms,
                previous_step_id
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                step_data['step_id'],
                step_data['run_id'],
                step_data['step_index'],
                step_data['is_llm_call'],
                step_data['is_tool_call'],
                step_data['prompt_text'],
                step_data['llm_output_text'],
                step_data['llm_input_tokens'],
                step_data['llm_output_tokens'],
                step_data['llm_total_tokens'],
                step_data['llm_prompt_cost'],
                step_data['llm_completion_cost'],
                step_data['llm_total_cost'],
                step_data['finish_reason'],
                step_data['model_name'],
                step_data['model_provider'],
                json.dumps(step_data['tool_call_requests']) if step_data['tool_call_requests'] is not None else None,
                step_data['tool_name'],
                json.dumps(step_data['tool_args']) if step_data['tool_args'] is not None else None,
                step_data['tool_status'],
                step_data['tool_response'],
                step_data['tool_message_content'],
                step_data['tool_cost'],
                step_data['tool_latency_ms'],
                step_data['previous_step_id'],
            ),
        )
        # Update previous_step_id for next iteration
        previous_step_id = step_id
    conn.commit()
    conn.close()


def ingest_file(json_path: str) -> None:
    """High‑level helper to ingest a JSON file containing LangSmith runs.

    The file may contain either a list of run objects or a single run object.
    All runs with the same session_id will be grouped into a single agent
    run.
    """
    with open(json_path, 'r') as f:
        data = json.load(f)
    # print(len(data))
    # # Normalise to list
    # if isinstance(data, dict):
    #     data = [data]
    # Group by session_id or trace_id
    groups: Dict[str, List[Dict[str, Any]]] = {}
    for run in data:
        key = run.get('session_id') or run.get('trace_id') or str(uuid.uuid4())
        groups.setdefault(key, []).append(run)
    for session_runs in groups.values():
        ingest_session(session_runs)

if __name__ == '__main__':
    import sys
    if len(sys.argv) < 2:
        print('Usage: python ingestion.py <json_file>')
    else:
        ingest_file(sys.argv[1])