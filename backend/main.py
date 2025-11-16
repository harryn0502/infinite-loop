import json
import os
import sqlite3
from fastapi import FastAPI, HTTPException
from datetime import datetime
from scripts.ingestion import ingest_dict
from scripts.create_db import DB_PATH  # Import the DB_PATH

# 1. Initialize the FastAPI app
app = FastAPI()


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
                # Keep as-is if it's not valid JSON
                pass
    return row_dict


# 2. Define the webhook endpoint
@app.post("/langsmith-webhook")
async def handle_langsmith_trace(payload: dict):
    """
    Receives a trace from a LangSmith automation webhook
    and ingest the dict to database
    """

    # 4. Ingest the received payload
    try:
        ingest_dict(payload)
        print(f"✅ Successfully ingested trace to the database")

        # 5. Return a success response
        return {"status": "success", "message": "Trace ingested successfully"}

    except Exception as e:
        print(f"❌ Error ingesting trace: {e}")
        # Return a 500 internal server error
        raise HTTPException(status_code=500, detail=str(e))


# 3. --- NEW: Endpoint to retrieve a reconstructed trace ---
@app.get("/trace/{trace_id}")
async def get_trace(trace_id: str):
    """
    Retrieves a main agent run and all its child steps (model, tool, chain)
    from the database to reconstruct the full trace.
    """
    if not os.path.exists(DB_PATH):
        raise HTTPException(status_code=500, detail=f"Database file not found at {DB_PATH}")

    conn = None
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()

        # 1. Fetch the main agent run
        cur.execute("SELECT * FROM agent_runs WHERE run_id = ?", (trace_id,))
        agent_run_row = cur.fetchone()

        if not agent_run_row:
            raise HTTPException(
                status_code=404, detail=f"Agent run with run_id '{trace_id}' not found."
            )

        # Convert to dict and parse JSON fields
        agent_run = _load_json_fields(
            dict(agent_run_row),
            ["input_messages", "output_messages", "tags", "langgraph_metadata", "runtime"],
        )

        all_steps = []

        # 2. Fetch all child steps
        # (call_model)
        cur.execute("SELECT * FROM call_model WHERE run_id = ?", (trace_id,))
        for row in cur.fetchall():
            step = _load_json_fields(dict(row), ["tool_call_requests"])
            step["step_type"] = "model"
            all_steps.append(step)

        # (call_tool)
        cur.execute("SELECT * FROM call_tool WHERE run_id = ?", (trace_id,))
        for row in cur.fetchall():
            step = _load_json_fields(dict(row), ["tool_args"])
            step["step_type"] = "tool"
            all_steps.append(step)

        # (call_chain)
        cur.execute("SELECT * FROM call_chain WHERE run_id = ?", (trace_id,))
        for row in cur.fetchall():
            step = _load_json_fields(dict(row), ["chain_input_messages", "chain_output_messages"])
            step["step_type"] = "chain"
            all_steps.append(step)

        # 3. Sort all steps by their execution index
        all_steps.sort(key=lambda x: x["step_index"])

        # 4. Assemble the final reconstructed JSON
        return {"agent_run": agent_run, "steps": all_steps}

    except HTTPException as http_exc:
        # Re-raise HTTP exceptions directly
        raise http_exc
    except Exception as e:
        print(f"❌ Error retrieving trace: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if conn:
            conn.close()


# Optional: A simple root endpoint to check if the server is running
@app.get("/")
def read_root():
    return {"message": "FastAPI server is running. POST to /langsmith-webhook to send traces."}
