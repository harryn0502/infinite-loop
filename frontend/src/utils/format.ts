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

/**
 * Recursively truncates all string values in a JSON object/array.
 * @param obj The object/array/value to process.
 * @param maxLength The max length for string values.
 * @returns The processed object/array/value.
 */
export const truncateJsonValues = (obj: any, maxLength: number = 100): any => {
  // 1. If it's a string, truncate it
  if (typeof obj === "string") {
    return obj.length > maxLength ? obj.slice(0, maxLength) + "..." : obj;
  }

  // 2. If it's an array, map over its items and recurse
  if (Array.isArray(obj)) {
    return obj.map((item) => truncateJsonValues(item, maxLength));
  }

  // 3. If it's an object, create a new object and recurse on its values
  if (obj !== null && typeof obj === "object") {
    const newObj: Record<string, any> = {};
    for (const key in obj) {
      if (Object.prototype.hasOwnProperty.call(obj, key)) {
        newObj[key] = truncateJsonValues(obj[key], maxLength);
      }
    }
    return newObj;
  }

  // 4. Return numbers, booleans, null, etc. as-is
  return obj;
};
