// The raw data structure from the JSON file
export interface RawLangSmithRun {
  id: string;
  name: string;
  start_time: string;
  run_type: string;
  end_time: string;
  parent_run_id: string | null; // This is key
  inputs: Record<string, unknown>;
  outputs: Record<string, unknown> | null;
  error: string | null;
  session_id: string;
}

// The nested structure we will create for the UI
export interface NestedRunNode extends RawLangSmithRun {
  children: NestedRunNode[];
}
