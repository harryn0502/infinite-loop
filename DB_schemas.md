# Database building (Tom)

Table 1: agent_runs
CREATE TABLE agent_runs (
    run_id TEXT PRIMARY KEY,
    start_time TEXT,
    end_time TEXT,
    user_id TEXT,
    session_id TEXT,
    agent_version TEXT,
    prompt_template_version TEXT,
    model_name TEXT,
    input_text TEXT,
    final_output TEXT,
    error_flag INTEGER,
    error_type TEXT,
    total_cost REAL,
    total_tokens INTEGER,
    extra_metadata JSON
);

Table 2: llm_calls
CREATE TABLE llm_calls (
    llm_call_id TEXT PRIMARY KEY,
    run_id TEXT,
    step_index INTEGER,
    model_name TEXT,
    prompt_text TEXT,
    prompt_diff_from_previous TEXT,
    temperature REAL,
    top_p REAL,
    stop_tokens TEXT,
    llm_output TEXT,
    llm_output_tokens INTEGER,
    latency_ms INTEGER,
    streaming_trace JSON,
    hidden_state_hash TEXT,
    error_flag INTEGER,
    error_type TEXT,
    metadata JSON,
    FOREIGN KEY (run_id) REFERENCES agent_runs(run_id)
);

Table 3: tool_calls
CREATE TABLE tool_calls (
    tool_call_id TEXT PRIMARY KEY,
    run_id TEXT,
    llm_call_id TEXT,
    step_index INTEGER,
    tool_name TEXT,
    tool_input TEXT,
    tool_output TEXT,
    tool_error_flag INTEGER,
    tool_error_type TEXT,
    execution_latency_ms INTEGER,
    streaming_logs JSON,
    retrieved_docs JSON,
    doc_similarity_scores JSON,
    intermediate_state JSON,
    cost_estimate REAL,
    metadata JSON,
    FOREIGN KEY (run_id) REFERENCES agent_runs(run_id),
    FOREIGN KEY (llm_call_id) REFERENCES llm_calls(llm_call_id)
);

## metadata
{
  "version": "1.0",
  "tables": [
    {
      "name": "agent_runs",
      "primary_key": "run_id",
      "foreign_keys": []
    },
    {
      "name": "llm_calls",
      "primary_key": "llm_call_id",
      "foreign_keys": [
        { "column": "run_id", "ref_table": "agent_runs", "ref_column": "run_id" }
      ]
    },
    {
      "name": "tool_calls",
      "primary_key": "tool_call_id",
      "foreign_keys": [
        { "column": "run_id", "ref_table": "agent_runs", "ref_column": "run_id" },
        { "column": "llm_call_id", "ref_table": "llm_calls", "ref_column": "llm_call_id" }
      ]
    }
  ]
}


## Checks
✅ Table: Features LangSmith Currently Covers
| Category                      | Feature                   | What LangSmith Provides                                              |
| ----------------------------- | ------------------------- | -------------------------------------------------------------------- |
| **Observability**             | Run Tracing               | Full trace of LLM calls, tools, agents, chains; view inputs/outputs. |
|                               | Nested Spans / Steps      | Visual tree showing sub-calls inside chains or agents.               |
|                               | Metadata Logging          | Attach custom metadata (env, model version, user ID, etc.) to runs.  |
|                               | Token & Cost Tracking     | Tokens & cost per run tracked automatically.                         |
|                               | Latency Monitoring        | End-to-end and per-step timing included.                             |
|                               | Error Capturing           | Exceptions and stack traces recorded.                                |
|                               | Run Search & Filtering    | Filter by tags, run type, metadata, error states.                    |
| **Monitoring**                | Dashboards                | High-level metrics: latency, cost, run volume, errors.               |
|                               | Custom Alerts             | Trigger alerts based on run failures or conditions.                  |
|                               | Performance Trends        | View model/prompt performance over time.                             |
| **Evaluations**               | Dataset Creation          | Create evaluation datasets from real or synthetic data.              |
|                               | Prompt Version Testing    | Compare different prompts on evaluation sets.                        |
|                               | LLM-as-Judge              | Use an LLM to score quality of responses.                            |
|                               | Human Feedback            | Collect user feedback and attach to runs.                            |
|                               | Leaderboards              | Compare models/prompts side-by-side.                                 |
| **Prompt & Model Management** | Prompt Versioning         | Store, version, and roll back prompts.                               |
|                               | Model Metadata Tracking   | Track which model/version used per run.                              |
|                               | Experiment Tracking       | Tag runs as experiments, compare results.                            |
| **Debugging Tools**           | Side-by-Side Compare      | Compare two runs or two versions of a prompt.                        |
|                               | Session/Chat Playback     | Replay multi-turn conversations in order.                            |
|                               | Clustering / Similar Runs | Detect similar runs for issue discovery.                             |
| **Development Tools**         | LangChain Integration     | Automatic tracing when using LangChain.                              |
|                               | Python/JS SDKs            | APIs for custom instrumentation.                                     |
|                               | LangGraph Integration     | Graph execution visualization.                                       |
|                               | Assistants / Studio UI    | Visual design, testing & debugging of agent flows.                   |
| **Production & Deployment**   | Environment Management    | Separate dev/staging/production runs.                                |
|                               | API Keys & Access Control | RBAC, org-level permissions.                                         |
|                               | Self-Hosting Option       | On-prem or hybrid deployment available.                              |
| **Data & Logs**               | Export & Query            | Export run logs, datasets, results.                                  |
|                               | Data Retention Policies   | Manage how long traces                                               |

