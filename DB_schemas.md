# Database building (Tom)

1. agent_runs
| Column               | Type      | Description                                    |
| -------------------- | --------- | ---------------------------------------------- |
| `run_id`             | TEXT (PK) | Unique ID for entire agent run                 |
| `start_time`         | TEXT      | ISO timestamp of run start                     |
| `end_time`           | TEXT      | ISO timestamp of run end                       |
| `status`             | TEXT      | `"success"` or `"error"`                       |
| `error`              | TEXT      | Error message / traceback (if any)             |
| `user_id`            | TEXT      | LS/Studio user ID                              |
| `session_id`         | TEXT      | Session/thread grouping                        |
| `thread_id`          | TEXT      | LangGraph thread ID                            |
| `input_messages`     | JSON      | Original messages passed as inputs             |
| `output_messages`    | JSON      | LLM generations (raw outputs section)          |
| `model_name`         | TEXT      | Model used in the run (`ls_model_name`)        |
| `tags`               | JSON      | LangSmith tags (`["langsmith:nostream", ...]`) |
| `langgraph_metadata` | JSON      | Metadata from LangGraph (`node`, `step`, etc.) |
| `total_tokens`       | INTEGER   | Total tokens for run                           |
| `total_cost`         | REAL      | Total run cost                                 |


Table 2: llm_calls
| Column               | Type                   | Description                                                |
| -------------------- | ---------------------- | ---------------------------------------------------------- |
| `llm_call_id`        | TEXT (PK)              | ID of the generation (`message.kwargs.id`)                 |
| `run_id`             | TEXT (FK → agent_runs) | Parent run                                                 |
| `step_index`         | INTEGER                | Index of generation within run                             |
| `prompt_text`        | TEXT                   | Prompt (not always in LS payload)                          |
| `finish_reason`      | TEXT                   | `"stop"` or `"tool_calls"`                                 |
| `model_name`         | TEXT                   | Model used in this step                                    |
| `model_provider`     | TEXT                   | Vendor (openai, anthropic, etc.)                           |
| `usage_metadata`     | JSON                   | Token usage: `{input_tokens, output_tokens, total_tokens}` |
| `tool_call_requests` | JSON                   | List of tool-call instructions from LLM                    |
| `llm_output_text`    | TEXT                   | The generation’s `text` field                              |
| `error_flag`         | INTEGER                | 1 if the generation has LS/API errors                      |


Table 3: tool_calls
| Column                 | Type      | Description                                      |
| ---------------------- | --------- | ------------------------------------------------ |
| `tool_call_id`         | TEXT (PK) | Tool invocation ID                               |
| `run_id`               | TEXT (FK) | Parent run                                       |
| `llm_call_id`          | TEXT (FK) | LLM generation that triggered the tool           |
| `tool_name`            | TEXT      | Tool name (`"think_tool"`, `"ResearchComplete"`) |
| `tool_args`            | JSON      | Arguments the tool was called with               |
| `tool_status`          | TEXT      | `"success"` or `"error"`                         |
| `tool_response`        | TEXT      | Raw output returned by the tool                  |
| `tool_message_content` | TEXT      | Content of the ToolMessage                       |
| `execution_latency_ms` | INTEGER   | Synthetic timing field                           |
| `is_tool_error`        | INTEGER   | 1 if tool failed                                 |
| `error_type`           | TEXT      | Error classification                             |

# relations
agent_runs
    └── llm_calls (1-to-many)
            └── tool_calls (1-to-many)
## db_schema_diff

How LangSmith trace JSON fields map to the SQLite schema, and what is kept / renamed / dropped / added.

1. agent_runs vs JSON

Source JSON (top-level):

run_id, start_time, end_time, status, error

user_id, session_id, thread_id

inputs.messages

outputs.generations

extra.metadata, extra.runtime, extra.invocation_params

tags

total_tokens, total_cost

plus many others: attachments, app_path, prompt_cost, completion_cost, prompt_token_details, completion_token_details, parent_run_id, child_run_ids, feedback_stats, …

DB columns (agent_runs):

✅ Kept / renamed

run_id ← run_id

start_time ← start_time

end_time ← end_time

status ← status

error ← error

user_id ← user_id

session_id ← session_id

thread_id ← thread_id

input_messages ← inputs.messages (JSON)

output_messages ← outputs.generations (JSON)

model_name ← extra.metadata.ls_model_name

tags ← tags (JSON)

langgraph_metadata ← extra.metadata (JSON)

total_tokens ← total_tokens

total_cost ← total_cost

❌ Dropped

extra.runtime, extra.invocation_params

options.*

runtime.*

prompt_cost, completion_cost

prompt_token_details, completion_token_details

parent_run_id, child_runs, child_run_ids

attachments, app_path, feedback_stats, manifest_id, first_token_time

➕ No extra DB-only fields at agent level (only derived JSON fields).

2. llm_calls vs JSON

Source JSON (per generation):

From outputs.generations[*][*].message.kwargs and siblings:

id

content

tool_calls

invalid_tool_calls

response_metadata.finish_reason

response_metadata.model_name

response_metadata.model_provider

response_metadata.headers, response_metadata.status_code, response_metadata.request_id, …

usage_metadata (with input_tokens, output_tokens, total_tokens, plus *_token_details)

DB columns (llm_calls):

✅ Kept / renamed

llm_call_id ← message.kwargs.id

run_id ← parent run’s run_id

step_index ← derived index in generations list

prompt_text ← (currently None / not populated; reserved)

finish_reason ← response_metadata.finish_reason

model_name ← response_metadata.model_name

model_provider ← response_metadata.model_provider

usage_metadata ← usage_metadata (JSON)

tool_call_requests ← tool_calls (JSON)

llm_output_text ← gen.text

error_flag ← derived (1 if error info present, else 0)

❌ Dropped

invalid_tool_calls

response_metadata.headers, status_code, request_id, service_tier, etc.

usage_metadata.input_token_details, output_token_details

➕ DB-only fields

step_index (ordering)

error_flag (boolean indicator)

3. tool_calls vs JSON

Source JSON:

Tool call requests: inside message.kwargs.tool_calls[*]

Tool results: ToolMessage objects (messages.ToolMessage.kwargs):

id

name

status

tool_call_id

content

DB columns (tool_calls):

✅ Kept / renamed

tool_call_id ← tool_calls[*].id / ToolMessage.kwargs.tool_call_id

run_id ← parent run_id

llm_call_id ← parent LLM generation id

tool_name ← name

tool_args ← tool_calls[*].args (JSON)

tool_status ← status

tool_response ← content

tool_message_content ← content

is_tool_error ← derived from status

error_type ← (reserved; currently null)

❌ Dropped

ToolMessage internal id

Any tool-specific internal metadata beyond args/content

➕ DB-only fields

execution_latency_ms (synthetic / optional)

is_tool_error (boolean)

4. Overall

We keep:

core IDs, times, status, messages, model info, LangGraph metadata, tokens/cost

LLM usage + tool call requests

tool execution results

We drop:

HTTP headers, SDK/runtime info, fine-grained cost/token details, LS-internal navigation fields

We add:

step_index, error_flag, is_tool_error, execution_latency_ms

plus some future-proof placeholders (prompt_text, error_type)