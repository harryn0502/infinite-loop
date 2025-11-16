import useSWR from "swr";

// This shape must match the data from your /traces endpoint
export interface TraceHeader {
  run_id: string;
  name: string;
  start_time: string;
  status: string;
  total_cost: number | null;
  total_tokens: number | null;
}

const fetcher = (url: string) => fetch(url).then((res) => res.json());

/**
 * Fetches the list of all trace headers from the backend.
 */
export const useTraces = () => {
  const { data, error, isLoading } = useSWR<TraceHeader[]>(
    "http://localhost:8000/traces", // Your FastAPI endpoint
    fetcher,
    {
      refreshInterval: 10000,
    }
  );

  // This MUST return an object with the 'traces' key
  return {
    traces: data,
    isLoading,
    isError: error,
  };
};
