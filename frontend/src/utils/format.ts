/**
 * Calculates the duration between two ISO 8601-like timestamps.
 */
export const calculateDuration = (startTime: string, endTime: string): string => {
  try {
    const start = new Date(startTime).getTime();
    const end = new Date(endTime).getTime();
    const durationMs = end - start;

    if (isNaN(durationMs)) {
      return "...";
    }

    return (durationMs / 1000).toFixed(2) + "s";
  } catch (e) {
    return "...";
  }
};

/**
 * Returns an emoji icon based on the run type.
 */
export const getRunIcon = (runType: string): string => {
  switch (runType) {
    case "llm":
      return "🧠"; // Brain for LLM
    case "chain":
      return "⛓️"; // Chain
    case "tool":
      return "🛠️"; // Tool
    default:
      return "▶️"; // Default
  }
};
