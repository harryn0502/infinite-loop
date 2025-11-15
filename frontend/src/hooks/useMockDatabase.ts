import { useMemo } from "react";
import rawTraces from "../data/langsmith_traces.json";
import type { RawLangSmithRun } from "../types";

// Define the shape of our mock "database"
export interface MockDatabase {
  agent_runs: RawLangSmithRun[];
  llm_calls: RawLangSmithRun[];
  tool_calls: RawLangSmithRun[];
}

export const useMockDatabase = (): MockDatabase => {
  // useMemo ensures this processing only runs once
  const db = useMemo(() => {
    const agent_runs: RawLangSmithRun[] = [];
    const llm_calls: RawLangSmithRun[] = [];
    const tool_calls: RawLangSmithRun[] = [];

    // Type assertion to help TypeScript
    const traces = rawTraces as RawLangSmithRun[];

    for (const run of traces) {
      // We categorize based on run_type, matching your DB schema tables
      switch (run.run_type) {
        case "chain":
          // We'll treat 'chain' runs as 'agent_runs' for this UI
          agent_runs.push(run);
          break;
        case "llm":
          llm_calls.push(run);
          break;
        case "tool":
          tool_calls.push(run);
          break;
        default:
          // You could also have a 'misc' or 'others' category
          // For now, we'll just log it
          console.warn(`Unknown run_type: ${run.run_type}`);
      }
    }

    // This handles the 'clarify_with_user' run from your sample,
    // which is a 'chain' but acts like a tool.
    // You can make this logic more robust as needed.
    const clarifyRun = agent_runs.find((run) => run.name === "clarify_with_user");
    if (clarifyRun) {
      tool_calls.push(clarifyRun);
      // Remove it from agent_runs
      agent_runs.splice(agent_runs.indexOf(clarifyRun), 1);
    }

    return { agent_runs, llm_calls, tool_calls };
  }, []); // Empty dependency array, so it runs once

  return db;
};
