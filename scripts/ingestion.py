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


def build_root_id_map(runs: List[Dict[str, Any]]) -> Dict[str, str]:
    """Build a mapping from each run's id to the id of its root parent run.

    LangSmith traces form a tree where each run references its parent via
    the `parent_run_id` field. A run whose `parent_run_id` is None is a root.
    This helper walks the parent chain to find the root id for each run.

    Parameters
    ----------
    runs: List[Dict]
        A list of run dicts loaded from JSON.

    Returns
    -------
    Dict[str, str]
        A mapping from run id to its root id. Runs without an id will be
        ignored in the mapping.
    """
    # Build a lookup by run id for quick parent traversal
    by_id: Dict[str, Dict[str, Any]] = {r.get('id'): r for r in runs if r.get('id')}
    root_cache: Dict[str, str] = {}

    def find_root(rid: str) -> str:
        # Return cached if computed
        if rid in root_cache:
            return root_cache[rid]
        # If run not found, treat id as its own root
        run = by_id.get(rid)
        if not run:
            root_cache[rid] = rid
            return rid
        parent_id = run.get('parent_run_id')
        # If no parent, this run is the root
        if not parent_id:
            root_cache[rid] = rid
            return rid
        # Otherwise, recursively find parent root
        root = find_root(parent_id)
        root_cache[rid] = root
        return root

    # Compute root id for all runs with ids
    for rid in by_id:
        find_root(rid)
    return root_cache


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

def parse_chain_step(run: Dict[str, Any]) -> Dict[str, Any]:
    """Extract fields for a chain step from a LangSmith run dict.

    A "chain" run in LangSmith represents a high‑level composition of
    sub‑runs (for example, a LangGraph node). Unlike pure LLM or tool
    runs, these objects encapsulate their own token usage and cost
    information. To align with the unified `steps` schema we explode
    those metrics into the same `llm_*` columns used for LLM calls and
    additionally expose chain‑specific metadata in dedicated columns.
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
    # Normalise token counts into the llm_* fields
    result['llm_input_tokens'] = to_int(run.get('prompt_tokens'))
    result['llm_output_tokens'] = to_int(run.get('completion_tokens'))
    result['llm_total_tokens'] = to_int(run.get('total_tokens'))
    # Normalise cost into llm_* cost fields
    result['llm_prompt_cost'] = to_float(run.get('prompt_cost'))
    result['llm_completion_cost'] = to_float(run.get('completion_cost'))
    result['llm_total_cost'] = to_float(run.get('total_cost'))
    # Chain runs have no explicit prompt or output text, nor a finish reason
    result['prompt_text'] = None
    result['llm_output_text'] = None
    result['finish_reason'] = None
    # Model metadata – reuse any available inner model identifiers
    meta = safe_get(run, ['extra', 'metadata'], {}) or {}
    result['model_name'] = meta.get('ls_model_name')
    result['model_provider'] = meta.get('ls_provider')
    # No direct tool call requests for chain runs
    result['tool_call_requests'] = None
    # Explode chain‑specific fields
    result['chain_name'] = run.get('name')
    result['chain_status'] = run.get('status')
    result['chain_input_messages'] = safe_get(run, ['inputs', 'messages'])
    result['chain_output_messages'] = safe_get(run, ['outputs', 'messages'])
    result['chain_prompt_tokens'] = to_int(run.get('prompt_tokens'))
    result['chain_completion_tokens'] = to_int(run.get('completion_tokens'))
    result['chain_total_tokens'] = to_int(run.get('total_tokens'))
    result['chain_prompt_cost'] = to_float(run.get('prompt_cost'))
    result['chain_completion_cost'] = to_float(run.get('completion_cost'))
    result['chain_total_cost'] = to_float(run.get('total_cost'))
    return result


def ingest_session(runs: List[Dict[str, Any]], root_id: str) -> None:
    """Ingest a list of LangSmith run dicts belonging to the same trace/root.

    This function aggregates the runs into a single agent_runs row identified
    by `root_id` and inserts one steps row per run in chronological order.
    The original session_id from the runs is preserved in the agent_runs table.
    """
    if not runs:
        return
    # Sort runs chronologically by start_time for ordering
    sorted_runs = sorted(runs, key=lambda r: r.get('start_time'))
    start_time = sorted_runs[0].get('start_time')
    end_time = sorted_runs[-1].get('end_time')
    # Determine session_id from first run for reference
    session_id = sorted_runs[0].get('session_id') or sorted_runs[0].get('trace_id')
    # Determine status and collect error messages across runs
    status = 'success'
    error_messages: List[str] = []
    for run in sorted_runs:
        if run.get('status') == 'error' or run.get('error'):
            status = 'error'
            if run.get('error'):
                error_messages.append(str(run['error']))
    error = '\n'.join(error_messages) if error_messages else None
    # Gather input and output messages from first and last LLM runs
    first_llm = next((r for r in sorted_runs if r.get('run_type') == 'llm'), None)
    last_llm = next((r for r in reversed(sorted_runs) if r.get('run_type') == 'llm'), None)
    input_messages = safe_get(first_llm or sorted_runs[0], ['inputs', 'messages'])
    output_messages = safe_get(last_llm or sorted_runs[-1], ['outputs', 'generations'])
    # Metadata and runtime from the root run (first run in sorted list)
    meta = safe_get(sorted_runs[0], ['extra', 'metadata'], {})
    runtime_info = safe_get(sorted_runs[0], ['extra', 'runtime'], {})
    model_name = meta.get('ls_model_name')
    tags = sorted_runs[0].get('tags')
    langgraph_metadata = meta
    # Aggregate total tokens and cost across runs
    def parse_int(x: Any) -> int:
        try:
            return int(x)
        except Exception:
            return 0
    total_tokens = sum(parse_int(run.get('total_tokens')) for run in sorted_runs)
    def parse_cost(x: Any) -> float:
        try:
            return float(x)
        except Exception:
            return 0.0
    total_cost = sum(parse_cost(run.get('total_cost')) for run in sorted_runs)
    # Insert or replace the agent run row with run_id = root_id
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
            root_id,
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
    # Build and insert step rows
    previous_step_id: str = None
    for idx, run in enumerate(sorted_runs):
        step_id = run.get('id') or str(uuid.uuid4())
        run_type = run.get('run_type')
        is_llm = 1 if run_type == 'llm' else 0
        is_tool = 1 if run_type == 'tool' else 0
        is_chain = 1 if run_type == 'chain' else 0
        # Initialise base step data with defaults
        step_data: Dict[str, Any] = {
            'step_id': step_id,
            'run_id': root_id,
            'step_index': idx,
            'is_llm_call': is_llm,
            'is_tool_call': is_tool,
            'is_chain_call': is_chain,
            # LLM fields
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
            # Tool fields
            'tool_name': None,
            'tool_args': None,
            'tool_status': None,
            'tool_response': None,
            'tool_message_content': None,
            'tool_cost': None,
            'tool_latency_ms': None,
            # Chain fields
            'chain_name': None,
            'chain_status': None,
            'chain_input_messages': None,
            'chain_output_messages': None,
            'chain_prompt_tokens': None,
            'chain_completion_tokens': None,
            'chain_total_tokens': None,
            'chain_prompt_cost': None,
            'chain_completion_cost': None,
            'chain_total_cost': None,
            # Link to previous step
            'previous_step_id': previous_step_id,
        }
        # Populate fields based on step type
        if is_llm:
            llm_fields = parse_llm_step(run)
            step_data.update(llm_fields)
        if is_tool:
            tool_fields = parse_tool_step(run)
            step_data.update(tool_fields)
        if is_chain:
            chain_fields = parse_chain_step(run)
            step_data.update(chain_fields)
        # Insert step into the database
        cur.execute(
            """INSERT OR REPLACE INTO steps (
                step_id, run_id, step_index,
                is_llm_call, is_tool_call, is_chain_call,
                prompt_text, llm_output_text,
                llm_input_tokens, llm_output_tokens, llm_total_tokens,
                llm_prompt_cost, llm_completion_cost, llm_total_cost,
                finish_reason, model_name, model_provider,
                tool_call_requests,
                tool_name, tool_args, tool_status,
                tool_response, tool_message_content,
                tool_cost, tool_latency_ms,
                chain_name, chain_status, chain_input_messages, chain_output_messages,
                chain_prompt_tokens, chain_completion_tokens, chain_total_tokens,
                chain_prompt_cost, chain_completion_cost, chain_total_cost,
                previous_step_id
            ) VALUES (
                ?, ?, ?,
                ?, ?, ?,
                ?, ?,
                ?, ?, ?,
                ?, ?, ?,
                ?, ?, ?,
                ?,
                ?, ?, ?,
                ?, ?,
                ?, ?,
                ?, ?, ?, ?,
                ?, ?, ?,
                ?, ?, ?,
                ?
            )""",
            (
                step_data['step_id'],
                step_data['run_id'],
                step_data['step_index'],
                step_data['is_llm_call'],
                step_data['is_tool_call'],
                step_data['is_chain_call'],
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
                step_data['chain_name'],
                step_data['chain_status'],
                json.dumps(step_data['chain_input_messages']) if step_data['chain_input_messages'] is not None else None,
                json.dumps(step_data['chain_output_messages']) if step_data['chain_output_messages'] is not None else None,
                step_data['chain_prompt_tokens'],
                step_data['chain_completion_tokens'],
                step_data['chain_total_tokens'],
                step_data['chain_prompt_cost'],
                step_data['chain_completion_cost'],
                step_data['chain_total_cost'],
                step_data['previous_step_id'],
            ),
        )
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
    # Normalise to list
    if isinstance(data, dict):
        data = [data]
    # Build a mapping from run id to root id for grouping
    root_map = build_root_id_map(data)
    groups: Dict[str, List[Dict[str, Any]]] = {}
    for run in data:
        run_id = run.get('id')
        # Determine the root id for this run. If no id present, fall back to session or trace.
        root_id = None
        if run_id and run_id in root_map:
            root_id = root_map[run_id]
        else:
            # If run lacks id or mapping, fall back to session_id/trace_id or new UUID
            root_id = run.get('session_id') or run.get('trace_id') or str(uuid.uuid4())
        groups.setdefault(root_id, []).append(run)
    # Ingest each group using its root id
    for root_id, group_runs in groups.items():
        ingest_session(group_runs, root_id)

if __name__ == '__main__':
    import sys
    if len(sys.argv) < 2:
        print('Usage: python ingestion.py <json_file>')
    else:
        ingest_file(sys.argv[1])