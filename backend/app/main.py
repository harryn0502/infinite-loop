import json
import os
import sqlite3
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware  # Import CORS
from pydantic import BaseModel
from typing import Optional, Any, List
from dotenv import load_dotenv

# --- Agent Imports ---
# Load environment variables (for HOLISTIC_AI_TEAM_ID, etc.)
load_dotenv()

try:
    # These imports are based on your simple_usage.py and file structure
    from app.scripts.ingestion import ingest_dict
    from app.scripts.create_db import DB_PATH
    from observability_agent import build_graph, run_obs_agent
    from observability_agent.holistic_ai_bedrock import get_chat_model
    from observability_agent.core.state import ObsState  # Assuming this is a TypedDict
    from langchain_core.messages import messages_to_dict, messages_from_dict

    AGENT_IMPORTS_SUCCESS = True
except ImportError as e:
    print(f"❌ Error: Failed to import agent modules: {e}")
    print("Agent endpoints will not be available.")
    AGENT_IMPORTS_SUCCESS = False


# --- Initialize Agent (run once on startup) ---
llm = None
agent_app = None
if AGENT_IMPORTS_SUCCESS:
    try:
        print("🚀 Initializing Holistic AI Bedrock model...")
        llm = get_chat_model()
        print("✅ Model initialized.")
        print("🚀 Building LangGraph agent...")
        agent_app = build_graph(llm)
        print("✅ Agent graph built and compiled.")
    except Exception as e:
        print(f"❌❌❌ FAILED TO INITIALIZE AGENT: {e}")
        print("Agent will not be available. Check .env file and dependencies.")
else:
    print("Skipping agent initialization due to import errors.")


# 1. Initialize the FastAPI app
app = FastAPI()

# --- Add CORS Middleware ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)


# --- NEW: Pydantic Model for Agent Query ---
class AgentQuery(BaseModel):
    user_message: str
    # prev_state will be a JSON-serializable dict
    prev_state: Optional[dict] = None


# --- NEW: State Serialization Helpers ---


def serialize_state(state: ObsState) -> Optional[dict]:
    """Converts ObsState (a TypedDict with BaseMessage) to a JSON-serializable dict."""
    if not state:
        return None
    try:
        serializable_state = state.copy()
        if "messages" in serializable_state:
            serializable_state["messages"] = messages_to_dict(state["messages"])
        return serializable_state
    except Exception as e:
        print(f"Error serializing state: {e}")
        return state  # Return best-effort


def deserialize_state(state_dict: Optional[dict]) -> Optional[ObsState]:
    """Converts a dict (from JSON) back to ObsState, re-inflating messages."""

    # If state_dict is None, empty, or *doesn't* have a 'messages' key,
    # treat it as a new session by returning None.
    # This protects runner.py from a KeyError.
    if not state_dict or "messages" not in state_dict:
        return None

    try:
        deserialized_state = state_dict.copy()

        # We know "messages" exists, so we deserialize it.
        deserialized_state["messages"] = messages_from_dict(state_dict["messages"])

        # We also know runner.py needs 'active_agent'.
        # If it's missing, add a default.
        if "active_agent" not in deserialized_state:
            deserialized_state["active_agent"] = "router"  # Default agent

        return deserialized_state
    except Exception as e:
        print(f"Error deserializing state messages: {e}")
        # Fallback: if deserialization fails, treat as new session
        return None


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
        print(f"Warning: Database file not found at {DB_PATH}. Agent queries may fail.")
        # raise HTTPException(status_code=500, detail=f"Database file not found at {DB_PATH}")
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


# --- NEW: Agent Query Endpoint ---
@app.post("/query_agent")
async def query_agent(query: AgentQuery):
    """
    Runs the observability agent with a user's query,
    supporting multi-turn conversations.
    """
    if not agent_app or not AGENT_IMPORTS_SUCCESS:
        raise HTTPException(
            status_code=503, detail="Agent is not initialized. Check server logs for errors."
        )

    try:
        # 1. Deserialize the previous state from JSON
        deserialized_prev_state = deserialize_state(query.prev_state)

        # 2. Run the agent
        print(f"Running agent with message: {query.user_message}")
        final_state: ObsState = run_obs_agent(
            user_message=query.user_message, app=agent_app, prev_state=deserialized_prev_state
        )

        # 3. Serialize the final state before returning as JSON
        serializable_final_state = serialize_state(final_state)

        return serializable_final_state

    except Exception as e:
        import traceback

        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Error processing agent query: {e}")


# 2. Webhook endpoint
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


# 3. Endpoint to retrieve all trace headers
@app.get("/traces")
async def get_all_traces():
    """
    Retrieves a list of all agent runs (trace headers) for the sidebar.
    """
    conn = None
    try:
        conn = get_db_conn()
        cur = conn.cursor()

        # --- MODIFIED QUERY ---
        # Added end_time to the SELECT statement
        cur.execute(
            "SELECT run_id, name, start_time, end_time, status, total_cost, total_tokens, input_messages, output_messages FROM agent_runs ORDER BY start_time DESC"
        )
        # --- END MODIFICATION ---

        rows = cur.fetchall()

        traces = []
        for row in rows:
            trace = dict(row)
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
    """
    Retrieves a list of all agent runs (trace headers) for the sidebar.
    """
    conn = None
    try:
        conn = get_db_conn()
        cur = conn.cursor()

        cur.execute(
            "SELECT run_id, name, start_time, status, total_cost, total_tokens FROM agent_runs ORDER BY start_time DESC"
        )
        rows = cur.fetchall()

        traces = []
        for row in rows:
            trace = dict(row)
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


# 4. Endpoint to retrieve a FULLY NESTED trace
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

        cur.execute("SELECT * FROM agent_runs WHERE run_id = ?", (trace_id,))
        agent_run_row = cur.fetchone()

        if not agent_run_row:
            raise HTTPException(
                status_code=404, detail=f"Agent run with run_id '{trace_id}' not found."
            )

        root = _load_json_fields(
            dict(agent_run_row),
            ["input_messages", "output_messages", "tags", "langgraph_metadata", "runtime"],
        )
        root["id"] = root["run_id"]
        root["run_type"] = "agent_run"
        root["children"] = []

        all_steps = []
        cur.execute(
            "SELECT * FROM call_model WHERE run_id = ? AND step_id != ?", (trace_id, trace_id)
        )
        for row in cur.fetchall():
            step = _load_json_fields(dict(row), ["tool_call_requests"])
            step["run_type"] = "llm"
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
            return root

        all_steps.sort(key=lambda x: x["step_index"])
        node_map = {}

        for step in all_steps:
            node = dict(step)
            node["id"] = node["step_id"]
            node["children"] = []
            node_map[node["id"]] = node

        root_children = []
        for node in node_map.values():
            parent_id = node.get("previous_step_id")
            if parent_id and parent_id in node_map:
                parent = node_map[parent_id]
                parent["children"].append(node)
            else:
                root_children.append(node)

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


# 5. Original /trace/{trace_id} endpoint
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
    """A simple endpoint for the Docker healthcheck."""
    return {"status": "ok"}
