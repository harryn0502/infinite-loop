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
