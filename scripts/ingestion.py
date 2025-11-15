# ingestion.py
import sqlite3
import json
from typing import Any, Dict, List
from create_db import ensure_schema, DB_PATH
import os
DB_PATH = "../db_as_files/agent_debug_db.sqlite"


def safe_get(d: Dict, path: List[str], default=None):
    cur = d
    for p in path:
        if not isinstance(cur, dict):
            return default
        cur = cur.get(p)
        if cur is None:
            return default
    return cur


def get_conn():

    if not os.path.exists(DB_PATH):
        ensure_schema(DB_PATH)

    # If DB exists but schema might be incomplete or outdated → also ensure
    else:
        ensure_schema(DB_PATH)

    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn

def parse_agent_run(trace: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "run_id": trace.get("run_id"),
        "start_time": trace.get("start_time"),
        "end_time": trace.get("end_time"),
        "status": trace.get("status"),
        "error": trace.get("error"),
        "user_id": trace.get("user_id"),
        "session_id": trace.get("session_id"),
        "thread_id": trace.get("thread_id"),
        "input_messages": safe_get(trace, ["inputs", "messages"], []),
        "output_messages": safe_get(trace, ["outputs", "generations"], []),
        "model_name": safe_get(trace, ["extra", "metadata", "ls_model_name"]),
        "tags": trace.get("tags", []),
        "langgraph_metadata": safe_get(trace, ["extra", "metadata"], {}),
        "total_tokens": trace.get("total_tokens"),
        "total_cost": trace.get("total_cost"),
    }


def parse_llm_calls(trace: Dict[str, Any]):
    gens = safe_get(trace, ["outputs", "generations"], []) or []
    llm_calls = []
    idx = 0
    for batch in gens:
        for gen in batch:
            msg = safe_get(gen, ["message", "kwargs"], {}) or {}
            llm_calls.append({
                "llm_call_id": msg.get("id"),
                "run_id": trace.get("run_id"),
                "step_index": idx,
                "prompt_text": None,
                "finish_reason": safe_get(msg, ["response_metadata", "finish_reason"]),
                "model_name": safe_get(msg, ["response_metadata", "model_name"]),
                "model_provider": safe_get(msg, ["response_metadata", "model_provider"]),
                "usage_metadata": msg.get("usage_metadata", {}),
                "tool_call_requests": msg.get("tool_calls", []),
                "llm_output_text": gen.get("text"),
                "error_flag": 1 if safe_get(msg, ["response_metadata", "body", "error"]) else 0,
            })
            idx += 1
    return llm_calls


def parse_tool_calls(trace: Dict[str, Any]):
    gens = safe_get(trace, ["outputs", "generations"], []) or []
    tool_calls = []
    for batch in gens:
        for gen in batch:
            msg = safe_get(gen, ["message", "kwargs"], {})
            # ToolMessage case
            if isinstance(msg, dict) and msg.get("type") == "tool":
                tool_calls.append({
                    "tool_call_id": msg.get("tool_call_id"),
                    "run_id": trace.get("run_id"),
                    "llm_call_id": msg.get("id"),
                    "tool_name": msg.get("name"),
                    "tool_args": {},  # call args live in tool_call_requests on the LLM side
                    "tool_status": msg.get("status"),
                    "tool_response": msg.get("content"),
                    "tool_message_content": msg.get("content"),
                    "execution_latency_ms": None,
                    "is_tool_error": 1 if msg.get("status") == "error" else 0,
                    "error_type": None,
                })
    return tool_calls


def insert_agent_run(cur, run):
    cur.execute("""
        INSERT OR REPLACE INTO agent_runs (
            run_id, start_time, end_time, status, error,
            user_id, session_id, thread_id,
            input_messages, output_messages,
            model_name, tags, langgraph_metadata,
            total_tokens, total_cost
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        run["run_id"],
        run["start_time"],
        run["end_time"],
        run["status"],
        run["error"],
        run["user_id"],
        run["session_id"],
        run["thread_id"],
        json.dumps(run["input_messages"]),
        json.dumps(run["output_messages"]),
        run["model_name"],
        json.dumps(run["tags"]),
        json.dumps(run["langgraph_metadata"]),
        run["total_tokens"],
        run["total_cost"],
    ))


def insert_llm_call(cur, call):
    cur.execute("""
        INSERT OR REPLACE INTO llm_calls (
            llm_call_id, run_id, step_index,
            prompt_text, finish_reason,
            model_name, model_provider,
            usage_metadata, tool_call_requests,
            llm_output_text, error_flag
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        call["llm_call_id"],
        call["run_id"],
        call["step_index"],
        call["prompt_text"],
        call["finish_reason"],
        call["model_name"],
        call["model_provider"],
        json.dumps(call["usage_metadata"]),
        json.dumps(call["tool_call_requests"]),
        call["llm_output_text"],
        call["error_flag"],
    ))


def insert_tool_call(cur, call):
    cur.execute("""
        INSERT OR REPLACE INTO tool_calls (
            tool_call_id, run_id, llm_call_id,
            tool_name, tool_args, tool_status,
            tool_response, tool_message_content,
            execution_latency_ms,
            is_tool_error, error_type
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        call["tool_call_id"],
        call["run_id"],
        call["llm_call_id"],
        call["tool_name"],
        json.dumps(call["tool_args"]),
        call["tool_status"],
        call["tool_response"],
        call["tool_message_content"],
        call["execution_latency_ms"],
        call["is_tool_error"],
        call["error_type"],
    ))


def ingest_trace(trace: Dict[str, Any]):
    """Ingest a single LangSmith trace dict into SQLite."""
    conn = get_conn()
    cur = conn.cursor()

    agent = parse_agent_run(trace)
    llm_calls = parse_llm_calls(trace)
    tool_calls = parse_tool_calls(trace)

    insert_agent_run(cur, agent)
    for c in llm_calls:
        insert_llm_call(cur, c)
    for t in tool_calls:
        insert_tool_call(cur, t)

    conn.commit()
    conn.close()
