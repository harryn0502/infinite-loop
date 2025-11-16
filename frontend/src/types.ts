// A type for the message structure
export interface TraceMessage {
  content: string;
  type: "human" | "ai" | "system" | "tool";
  [key: string]: unknown; // Allow for other keys
}

// The raw data structure, updated to match the new JSON
export interface RawLangSmithRun {
  id: string;
  name: string;
  start_time: string;
  run_type: string;
  end_time: string;
  parent_run_id: string | null;
  error: string | null;
  session_id: string;
  status?: string;

  // --- Root Node Fields ---
  input_messages?: TraceMessage[];
  output_messages?: TraceMessage[] | null;
  total_cost?: number | null;
  total_tokens?: number | null;

  // --- Generic/Fallback Fields ---
  inputs?: Record<string, unknown>;
  outputs?: Record<string, unknown> | null;

  // --- Specific Child Fields from JSON ---
  // run_type: "chain"
  chain_input_messages?: TraceMessage[] | Record<string, unknown>;
  chain_output_messages?: TraceMessage[] | Record<string, unknown> | null;
  chain_total_cost?: number | null;
  chain_total_tokens?: number | null;
  chain_prompt_cost?: number | null; // 👈 --- ADDED
  chain_completion_cost?: number | null; // 👈 --- ADDED
  chain_prompt_tokens?: number | null; // 👈 --- ADDED
  chain_completion_tokens?: number | null; // 👈 --- ADDED

  // run_type: "llm"
  prompt_text?: string | null;
  llm_output_text?: string | null;
  llm_total_cost?: number | null;
  llm_total_tokens?: number | null;
  llm_prompt_cost?: number | null; // 👈 --- ADDED
  llm_completion_cost?: number | null; // 👈 --- ADDED
  llm_input_tokens?: number | null; // 👈 --- ADDED
  llm_output_tokens?: number | null; // 👈 --- ADDED

  // run_type: "tool"
  tool_args?: Record<string, unknown> | string;
  tool_response?: Record<string, unknown> | string;
}

// The nested structure we will create for the UI
export interface NestedRunNode extends RawLangSmithRun {
  children: NestedRunNode[];
}
