import json
import os
import sqlite3
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware  # Import CORS
from app.scripts.ingestion import ingest_dict
from app.scripts.create_db import DB_PATH

# 1. Initialize the FastAPI app
app = FastAPI()

# --- NEW: Add CORS Middleware ---
# This allows your React frontend (running on a different port)
# to make API calls to this server.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)

# --- Database Helper ---


def _load_json_fields(row_dict: dict, fields_to_parse: list) -> dict:
    """Helper to convert JSON text fields from DB into Python objects."""
    if not row_dict:
        return row_dict
    for field in fields_to_parse:
        if field in row_dict and isinstance(row_dict[field], str):
            try:
                row_dict[field] = json.loads(row_dict[field])
            except json.JSONDecodeError:
                pass
    return row_dict


# --- Database Connection Helper ---
def get_db_conn():
    """Establishes a connection to the SQLite database."""
    if not os.path.exists(DB_PATH):
        raise HTTPException(status_code=500, detail=f"Database file not found at {DB_PATH}")
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


# 2. Webhook endpoint (unchanged)
@app.post("/langsmith-webhook")
async def handle_langsmith_trace(payload: dict):
    """
    Receives a trace from a LangSmith automation webhook
    and ingest the dict to database
    """
    try:
        ingest_dict(payload)
        print(f"✅ Successfully ingested trace to the database")
        return {"status": "success", "message": "Trace ingested successfully"}
    except Exception as e:
        print(f"❌ Error ingesting trace: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# 3. --- NEW: Endpoint to retrieve all trace headers ---
@app.get("/traces")
async def get_all_traces():
    """
    Retrieves a list of all agent runs (trace headers) for the sidebar.
    """
    conn = None
    try:
        conn = get_db_conn()
        cur = conn.cursor()

        # Fetch key info for the list view
        cur.execute(
            "SELECT run_id, name, start_time, status, total_cost, total_tokens FROM agent_runs ORDER BY start_time DESC"
        )
        rows = cur.fetchall()

        traces = []
        for row in rows:
            trace = dict(row)
            # Fallback to run_id if name is missing from DB
            if not trace.get("name"):
                trace["name"] = trace["run_id"]
            traces.append(trace)

        return traces

    except Exception as e:
        print(f"❌ Error retrieving trace list: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if conn:
            conn.close()


# 4. --- NEW: Endpoint to retrieve a FULLY NESTED trace ---
@app.get("/trace_nested/{trace_id}")
async def get_nested_trace(trace_id: str):
    """
    Retrieves a main agent run and all its child steps,
    then reconstructs them into a nested tree structure
    that the frontend (useFlowData, RunNode) expects.
    """
    conn = None
    try:
        conn = get_db_conn()
        cur = conn.cursor()

        # 1. Fetch the main agent run (the root of the tree)
        cur.execute("SELECT * FROM agent_runs WHERE run_id = ?", (trace_id,))
        agent_run_row = cur.fetchone()

        if not agent_run_row:
            raise HTTPException(
                status_code=404, detail=f"Agent run with run_id '{trace_id}' not found."
            )

        # The root of our tree
        root = _load_json_fields(
            dict(agent_run_row),
            ["input_messages", "output_messages", "tags", "langgraph_metadata", "runtime"],
        )
        # Add 'id' and 'children' fields to match NestedRunNode structure
        root["id"] = root["run_id"]
        root["run_type"] = "agent_run"  # Add a type for the root
        root["children"] = []

        # 2. Fetch all child steps
        # --- MODIFIED: Added 'AND step_id != ?' to filter the duplicate root ---
        # --- MODIFIED: 'SELECT *' will now include start_time and end_time ---
        all_steps = []
        cur.execute(
            "SELECT * FROM call_model WHERE run_id = ? AND step_id != ?", (trace_id, trace_id)
        )
        for row in cur.fetchall():
            step = _load_json_fields(dict(row), ["tool_call_requests"])
            step["run_type"] = "llm"  # Use 'run_type' consistent with ingestion
            step["name"] = step.get("model_name") or "llm_step"
            all_steps.append(step)

        cur.execute(
            "SELECT * FROM call_tool WHERE run_id = ? AND step_id != ?", (trace_id, trace_id)
        )
        for row in cur.fetchall():
            step = _load_json_fields(dict(row), ["tool_args"])
            step["run_type"] = "tool"
            step["name"] = step.get("tool_name") or "tool_step"
            all_steps.append(step)

        cur.execute(
            "SELECT * FROM call_chain WHERE run_id = ? AND step_id != ?", (trace_id, trace_id)
        )
        for row in cur.fetchall():
            step = _load_json_fields(dict(row), ["chain_input_messages", "chain_output_messages"])
            step["run_type"] = "chain"
            step["name"] = step.get("chain_name") or "chain_step"
            all_steps.append(step)

        if not all_steps:
            return root  # Return just the root if there are no steps

        # 3. Sort steps by execution index to maintain order
        # This sort is now just a preliminary grouping.
        # The frontend will do the final, correct sort by start_time.
        all_steps.sort(key=lambda x: x["step_index"])

        # 4. Build the tree structure
        node_map = {}  # Map of step_id -> node object

        # First pass: create all node objects and add to map
        for step in all_steps:
            node = dict(step)
            node["id"] = node["step_id"]  # Add 'id' field
            node["children"] = []  # Add 'children' field
            node_map[node["id"]] = node

        # Second pass: link children to parents
        # We'll build a new list of top-level children for the root
        root_children = []

        for node in node_map.values():
            parent_id = node.get("previous_step_id")

            if parent_id and parent_id in node_map:
                # This node is a child of another step
                parent = node_map[parent_id]
                parent["children"].append(node)
            else:
                # This node is a direct child of the agent_run root
                root_children.append(node)

        # Add the correctly ordered top-level children to the root
        # Sort by step_index again just in case
        root["children"] = sorted(root_children, key=lambda x: x["step_index"])

        return root

    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        print(f"❌ Error retrieving nested trace: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if conn:
            conn.close()


# 5. Original /trace/{trace_id} endpoint (optional, can be removed)
# I'm leaving this here in case you need it for other debugging.
@app.get("/trace/{trace_id}")
async def get_trace(trace_id: str):
    """
    Retrieves a main agent run and all its child steps (flat list).
    """
    conn = None
    try:
        conn = get_db_conn()
        cur = conn.cursor()

        cur.execute("SELECT * FROM agent_runs WHERE run_id = ?", (trace_id,))
        agent_run_row = cur.fetchone()
        if not agent_run_row:
            raise HTTPException(status_code=404, detail="Agent run not found.")

        agent_run = _load_json_fields(
            dict(agent_run_row),
            ["input_messages", "output_messages", "tags", "langgraph_metadata", "runtime"],
        )
        all_steps = []

        cur.execute("SELECT * FROM call_model WHERE run_id = ?", (trace_id,))
        for row in cur.fetchall():
            all_steps.append(_load_json_fields(dict(row), ["tool_call_requests"]))
        cur.execute("SELECT * FROM call_tool WHERE run_id = ?", (trace_id,))
        for row in cur.fetchall():
            all_steps.append(_load_json_fields(dict(row), ["tool_args"]))
        cur.execute("SELECT * FROM call_chain WHERE run_id = ?", (trace_id,))
        for row in cur.fetchall():
            all_steps.append(
                _load_json_fields(dict(row), ["chain_input_messages", "chain_output_messages"])
            )

        all_steps.sort(key=lambda x: x["step_index"])
        return {"agent_run": agent_run, "steps": all_steps}

    except Exception as e:
        print(f"❌ Error retrieving trace: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if conn:
            conn.close()


# Optional: A simple root endpoint to check if the server is running
@app.get("/")
def read_root():
    return {"message": "FastAPI server is running."}
