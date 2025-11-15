import json
from fastapi import FastAPI
from datetime import datetime

# 1. Initialize the FastAPI app
app = FastAPI()


# 2. Define the webhook endpoint
@app.post("/langsmith-webhook")
async def handle_langsmith_trace(payload: dict):
    """
    Receives a trace from a LangSmith automation webhook
    and saves it as a JSON file.
    """

    # 3. Create a unique filename
    # We replace colons because they are not valid in Windows filenames
    timestamp = datetime.now().isoformat().replace(":", "-")
    filename = f"trace_{timestamp}.json"

    # 4. Save the received payload to a JSON file
    try:
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=4)

        print(f"✅ Successfully saved trace to {filename}")

        # 5. Return a success response
        return {"status": "success", "message": "Trace saved", "filename": filename}

    except Exception as e:
        print(f"❌ Error saving trace: {e}")
        return {"status": "error", "message": str(e)}


# Optional: A simple root endpoint to check if the server is running
@app.get("/")
def read_root():
    return {"message": "FastAPI server is running. POST to /langsmith-webhook to send traces."}
