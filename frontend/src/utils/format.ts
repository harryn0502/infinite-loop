// Define a recursive type for JSON-compatible values
type JsonValue = string | number | boolean | null | JsonValue[] | { [key: string]: JsonValue };

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
  } catch {
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
export const truncateJsonValues = (
  obj: unknown, // <-- THIS IS THE FIX (was JsonValue)
  maxLength: number = 100
): JsonValue => {
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
    const newObj: Record<string, JsonValue> = {};

    // Cast obj to iterate over its keys
    const objAsRecord = obj as Record<string, unknown>;

    for (const key in objAsRecord) {
      if (Object.prototype.hasOwnProperty.call(objAsRecord, key)) {
        newObj[key] = truncateJsonValues(objAsRecord[key], maxLength);
      }
    }
    return newObj;
  }

  // 4. Return numbers, booleans, null, etc. as-is
  // We've ruled out string, array, and object, so what's left
  // (number, boolean, null) is a valid JsonValue.
  return obj as JsonValue;
};
