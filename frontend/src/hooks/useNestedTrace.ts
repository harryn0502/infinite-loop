import useSWR from "swr";
import type { NestedRunNode } from "../types"; // Import your existing type

const fetcher = (url: string) => fetch(url).then((res) => res.json());

/**
 * Fetches a single, fully nested trace run by its ID.
 * If traceId is null, no fetch will be attempted.
 */
export const useNestedTrace = (traceId: string | null) => {
  // SWR automatically fetches when traceId is not null
  const { data, error, isLoading } = useSWR<NestedRunNode>(
    traceId ? `/api/trace_nested/${traceId}` : null,
    fetcher
  );

  return {
    trace: data,
    isLoading,
    isError: error,
  };
};
