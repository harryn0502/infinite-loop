LangSmith Debug Database Schema (Root‑run version)

This document describes the structure of the SQLite database used to ingest and analyse LangSmith run traces. The schema reflects the latest design with the following key properties:

Two‑level hierarchy: A single agent_runs record groups all runs that share the same root run (the top‑level run whose parent_run_id is None). All descendant runs (LLM calls, tool invocations, chain executions, etc.) become individual steps linked to that root via run_id.

Exploded chain data: Metrics from chain runs are normalised into dedicated columns rather than stored in a JSON blob. This makes chain runs queryable alongside LLM and tool steps.

Token/cost normalisation: Input/output/total token counts and cost values are extracted into numeric columns for both LLM and chain runs. Tool costs and latencies are also captured where provided.

Sequence reconstruction: Each step contains a previous_step_id pointer to the prior step, enabling linear traversal of the execution history.

Binary type flags: is_llm_call, is_tool_call and is_chain_call indicate the step category. These flags are mutually exclusive per row.

Tables and fields
agent_runs
Column	Type	Description
run_id	TEXT (PK)	The root run ID (the id of the top‑level run whose parent_run_id is None). All steps sharing this root belong to this row.
start_time, end_time	TEXT	ISO timestamps for the earliest start and latest end among all runs in the trace.
status	TEXT	"success" if all runs completed without error, else "error".
error	TEXT	Aggregated error messages from any run in the trace.
user_id	TEXT	Reserved (not present in current JSON).
session_id	TEXT	The session_id from the first run (preserved for reference).
thread_id	TEXT	Reserved (unused; always NULL in current traces).
input_messages	JSON	The inputs.messages from the first LLM run or the first run in the sequence.
output_messages	JSON	The outputs.generations from the last LLM run or the last run.
model_name	TEXT	The base model name extracted from extra.metadata.ls_model_name.
tags	JSON	The list of LangSmith tags attached to the root run.
langgraph_metadata	JSON	The extra.metadata of the root run.
runtime	JSON	Runtime environment information from extra.runtime (Python version, OS, SDK version, etc.).
total_tokens	INTEGER	Sum of total_tokens across all descendant runs (LLM and chain).
total_cost	REAL	Sum of total_cost across all descendant runs (LLM, chain, tool).
steps

Each row in steps represents a single run (llm, tool or chain) and captures both common and type‑specific data.

Column	Type	Description
step_id	TEXT (PK)	The original run id.
run_id	TEXT (FK)	The root id from agent_runs linking this step to its parent trace.
step_index	INTEGER	The chronological order of this step within its run_id.
is_llm_call	INTEGER	1 if this step is an LLM call, else 0.
is_tool_call	INTEGER	1 if this step is a tool invocation, else 0.
is_chain_call	INTEGER	1 if this step is a chain run, else 0.
LLM fields		
prompt_text	TEXT	Raw prompt text (unused in current traces).
llm_output_text	TEXT	The generated text (outputs.generations[..].text).
llm_input_tokens	INTEGER	Number of input tokens (prompt_tokens).
llm_output_tokens	INTEGER	Number of output tokens (completion_tokens).
llm_total_tokens	INTEGER	Total tokens (total_tokens).
llm_prompt_cost	REAL	Cost attributed to input tokens (prompt_cost).
llm_completion_cost	REAL	Cost attributed to output tokens (completion_cost).
llm_total_cost	REAL	Total cost (total_cost).
finish_reason	TEXT	Finish reason from response_metadata.finish_reason (e.g. "stop", "tool_calls").
model_name	TEXT	Model name used for this call (from extra.metadata.ls_model_name).
model_provider	TEXT	LLM provider (e.g. "openai", "anthropic") from extra.metadata.ls_provider.
tool_call_requests	JSON	List of tool call requests returned by the LLM (outputs.generations[..].message.kwargs.tool_calls).
Tool fields		
tool_name	TEXT	Name of the tool invoked (run.name).
tool_args	JSON	Parsed tool arguments from inputs.input (stringified JSON or raw string).
tool_status	TEXT	Status from outputs.output.status.
tool_response	TEXT	The result returned by the tool (outputs.output.content).
tool_message_content	TEXT	Echo of tool_response for convenience.
tool_cost	REAL	Cost of the tool call (total_cost on tool runs).
tool_latency_ms	INTEGER	Latency computed from end_time - start_time in milliseconds.
Chain fields		
chain_name	TEXT	Name of the chain (run.name).
chain_status	TEXT	Status of the chain (run.status).
chain_input_messages	JSON	The input messages passed to the chain (inputs.messages).
chain_output_messages	JSON	The messages output by the chain (outputs.messages).
chain_prompt_tokens	INTEGER	Number of prompt tokens for the chain run (prompt_tokens).
chain_completion_tokens	INTEGER	Number of completion tokens for the chain run (completion_tokens).
chain_total_tokens	INTEGER	Total tokens used by the chain (total_tokens).
chain_prompt_cost	REAL	Cost of prompt tokens for the chain (prompt_cost).
chain_completion_cost	REAL	Cost of completion tokens for the chain (completion_cost).
chain_total_cost	REAL	Total cost of the chain run (total_cost).
Navigation		
previous_step_id	TEXT	ID of the previous step within the same run_id; NULL for the first step.
Differences between the raw JSON and the database schema

The raw LangSmith run JSON contains a wide array of fields. The database schema extracts and normalises only those needed for analysis while omitting, renaming or flattening others. Here is a summary of the key differences:

Root run grouping: In the JSON each run has an id and a parent_run_id. The schema groups all runs with the same ultimate ancestor into one agent_runs record. The column run_id in agent_runs and steps is therefore the ID of the top‑level run (where parent_run_id is None). The original session_id is preserved in the agent_runs.session_id column.

Dropped/ignored fields: Many JSON fields are omitted, including internal LangSmith fields (child_run_ids, child_runs, events, serialized, reference_example_id, feedback_stats, attachments, app_path, etc.), detailed prompt formatting options (structured_output, schema), runtime service headers (headers, status_code, request_id, etc.) and debug information. These are either not useful for high‑level analysis or redundant.

Renamed / flattened fields:

prompt_tokens, completion_tokens, total_tokens → llm_input_tokens, llm_output_tokens, llm_total_tokens (also repeated for chain runs as chain_*).

prompt_cost, completion_cost, total_cost → llm_prompt_cost, llm_completion_cost, llm_total_cost (and similarly for chain and tool costs).

outputs.output.status and outputs.output.content → tool_status and tool_response.

name and status on tool runs → tool_name and tool_status; on chain runs → chain_name and chain_status.

inputs.input → parsed JSON into tool_args.

extra.metadata.ls_model_name and extra.metadata.ls_provider → model_name and model_provider in LLM steps.

extra.metadata → langgraph_metadata at the agent level.

extra.runtime → runtime column in agent_runs.

New database‑only fields:

is_llm_call, is_tool_call, is_chain_call — binary flags for quick filtering of step types.

step_index and previous_step_id — to preserve the chronological order and allow reconstruction of the execution chain.

llm_output_text — extracted from nested generation structures.

tool_latency_ms — computed from timestamps, not provided directly.

Overall, the schema is designed to provide a concise yet comprehensive view of agent execution, enabling easy querying and analysis without the overhead of the raw JSON’s nested and verbose structure.