import { useState, useEffect } from "react";

// In useTraces.ts
export interface TraceHeader {
  run_id: string;
  name: string;
  start_time: string;
  end_time: string | null;
  status: string;
  total_cost: number | null;
  total_tokens: number | null;
  // 👇 NEW FIELDS
  input_messages: string | null; // Raw JSON string from DB
  output_messages: string | null; // Raw JSON string from DB
}

export const useTraces = () => {
  const [traces, setTraces] = useState<TraceHeader[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);

  useEffect(() => {
    const fetchTraces = async () => {
      setIsLoading(true);
      try {
        // Ensure this points to your backend
        const response = await fetch("/api/traces");
        if (!response.ok) {
          throw new Error("Failed to fetch traces");
        }
        const data: TraceHeader[] = await response.json();
        setTraces(data);
      } catch (e) {
        setError(e as Error);
      } finally {
        setIsLoading(false);
      }
    };

    fetchTraces();
  }, []);

  return { traces, isLoading, error };
};
