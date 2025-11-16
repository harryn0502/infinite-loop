import styled from "styled-components";
import { type TraceHeader } from "../hooks/useTraces";
import { useState } from "react";
import { TraceContentModal } from "./TraceContentModal";

// --- NEW/REFINED TYPES ---

/**
 * Defines the expected structure of a message object inside the input_messages/output_messages JSON array.
 * This mirrors the SerializedMessage interface for content extraction.
 */
interface SerializedMessage {
  content?: string;
  data?: {
    content?: string;
    [key: string]: unknown;
  };
  [key: string]: unknown;
}

// --- CONSTANTS & UTILITY FUNCTIONS ---
const MAX_CHARS = 100;

const calculateDuration = (startTime: string, endTime: string | null): string => {
  if (!endTime) return "-";
  try {
    const start = new Date(startTime).getTime();
    const end = new Date(endTime).getTime();
    const duration = (end - start) / 1000; // in seconds

    if (duration < 60) {
      return `${duration.toFixed(2)}s`;
    }
    return `${(duration / 60).toFixed(2)}m`;
  } catch {
    return "Invalid Date";
  }
};

const formatCost = (cost: number | null): string => {
  if (cost == null) return "$0.00";
  if (cost === 0) return "$0.00";
  if (cost < 0.00001) {
    return `$${cost.toExponential(2)}`;
  }
  return `$${cost.toFixed(5)}`;
};

const formatDate = (dateString: string): string => {
  try {
    return new Date(dateString).toLocaleString();
  } catch {
    return "Invalid Date";
  }
};

/**
 * Extracts the content string from a single message object.
 * FIX: Use SerializedMessage type instead of 'any'.
 */
const extractMessageContent = (message: SerializedMessage): string => {
  // Priority 1: Top-level content (e.g., {"content": "..."})
  if (message.content) return message.content;
  // Priority 2: Nested LangChain/Legacy content (e.g., {"data": {"content": "..."}})
  if (message.data && message.data.content) return message.data.content;

  return "(No text content found)";
};

/**
 * Extracts and truncates content from the raw JSON string array.
 */
const extractAndTruncateContent = (jsonString: string | null, isInput: boolean): string => {
  if (!jsonString) return "(Empty)";

  let content = "";
  try {
    // FIX: Parse into an array of SerializedMessage
    const messages: SerializedMessage[] = JSON.parse(jsonString);
    if (!Array.isArray(messages) || messages.length === 0) {
      return "(Empty)";
    }

    // Determine the message object to read (first for input, last for output)
    const message = isInput ? messages[0] : messages[messages.length - 1];

    content = extractMessageContent(message);
  } catch {
    return "(Parse Error)";
  }

  return content.length > MAX_CHARS ? content.substring(0, MAX_CHARS) + "..." : content;
};

/**
 * Extracts the full, clean text content for the modal.
 * Returns the full content string, or null if the JSON is invalid.
 */
const extractFullContentText = (jsonString: string | null, isInput: boolean): string | null => {
  if (!jsonString) return null;
  try {
    // FIX: Parse into an array of SerializedMessage
    const messages: SerializedMessage[] = JSON.parse(jsonString);
    if (!Array.isArray(messages) || messages.length === 0) return null;

    const message = isInput ? messages[0] : messages[messages.length - 1];

    return extractMessageContent(message);
  } catch {
    return null;
  }
};

// --- COMPONENT ---

interface ExpandedTraceRowProps {
  trace: TraceHeader;
  onSelect: (run: TraceHeader) => void;
  isSelected: boolean;
}

interface ModalContent {
  title: string;
  content: string;
}

export const ExpandedTraceRow = ({ trace, onSelect, isSelected }: ExpandedTraceRowProps) => {
  const [modalContent, setModalContent] = useState<ModalContent | null>(null);

  const latency = calculateDuration(trace.start_time, trace.end_time);
  const cost = formatCost(trace.total_cost);
  const date = formatDate(trace.start_time);

  const inputContent = extractAndTruncateContent(trace.input_messages, true);
  const outputContent = extractAndTruncateContent(trace.output_messages, false);

  const handleContentClick = (title: string, rawJson: string | null, isInput: boolean) => {
    const fullText = extractFullContentText(rawJson, isInput);

    if (!fullText || fullText.startsWith("(No text content found)") || fullText.trim() === "") {
      setModalContent({
        title,
        content: "Content is empty or unavailable.",
      });
      return;
    }

    setModalContent({
      title,
      content: fullText,
    });
  };

  return (
    <>
      <RowWrapper $selected={isSelected} onClick={() => onSelect(trace)}>
        <NameRunIdCell $flex={3}>
          <TraceName>{trace.name}</TraceName>
          <RunId>{trace.run_id}</RunId>
        </NameRunIdCell>

        <Cell $flex={2}>{date}</Cell>
        <Cell $flex={1}>
          <Status $status={trace.status}>{trace.status}</Status>
        </Cell>
        <Cell $flex={1} $align="right">
          {cost}
        </Cell>
        <Cell $flex={1} $align="right">
          {latency}
        </Cell>

        {/* NEW INPUT COLUMN */}
        <ContentCell
          $flex={2}
          onClick={(e) => {
            e.stopPropagation();
            handleContentClick("First Input", trace.input_messages, true);
          }}
          $clickable={inputContent !== "(Empty)" && inputContent !== "(Parse Error)"}
        >
          {/* 燥 --- WRAPPER ADDED HERE --- 燥 */}
          <ContentWrapper>{inputContent}</ContentWrapper>
        </ContentCell>

        {/* NEW OUTPUT COLUMN */}
        <ContentCell
          $flex={2}
          onClick={(e) => {
            e.stopPropagation();
            handleContentClick("Final Output", trace.output_messages, false);
          }}
          $clickable={outputContent !== "(Empty)" && outputContent !== "(Parse Error)"}
        >
          {/* 燥 --- WRAPPER ADDED HERE --- 燥 */}
          <ContentWrapper>{outputContent}</ContentWrapper>
        </ContentCell>
      </RowWrapper>

      {modalContent && (
        <TraceContentModal
          title={modalContent.title}
          content={modalContent.content}
          onClose={() => setModalContent(null)}
        />
      )}
    </>
  );
};

// --- STYLED COMPONENTS ---

const RowWrapper = styled.div<{ $selected: boolean }>`
  display: flex;
  align-items: center;
  padding: 12px 10px;
  border-bottom: 1px solid #eee;
  cursor: pointer;
  /* Use conditional background based on selection state for content wrapper to hide leakage */
  background-color: ${(props) => (props.$selected ? "#e3f2fd" : "white")};
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;

  &:hover {
    background-color: ${(props) => (props.$selected ? "#e3f2fd" : "#f5f5f5")};
  }
`;

const ContentWrapper = styled.div`
  /* Inherit text styling from parent */
  white-space: pre-wrap;
  overflow: hidden;
  /* Ensure it has the row's background to mask over-rendered text */
  background-color: inherit;

  /* CRITICAL: Limit text to exactly two lines with ellipsis */
  display: -webkit-box;
  -webkit-line-clamp: 2; /* Limit to 2 lines */
  -webkit-box-orient: vertical;
  line-height: 1.4; /* Ensure consistent line height for clipping */
  max-height: 2.8em; /* 2 lines * 1.4 line-height * 1em font-size (approx) */
`;

const ContentCell = styled.div<{ $flex: number; $clickable: boolean }>`
  flex: ${(props) => props.$flex};
  font-size: 13px;
  padding: 0 6px;
  /* We remove max-height, white-space, and overflow from here, 
     and apply it to the ContentWrapper instead, 
     but we keep padding/flex/font-size */

  /* Critical change: The outer cell defines the viewport for the wrapper */
  max-height: 40px;
  overflow: hidden;

  color: ${(props) => (props.$clickable ? "#0d47a1" : "#555")};
  text-decoration: ${(props) => (props.$clickable ? "underline dotted" : "none")};
  cursor: ${(props) => (props.$clickable ? "pointer" : "default")};
`;

const NameRunIdCell = styled.div<{ $flex: number }>`
  flex: ${(props) => props.$flex};
  padding: 0 6px;
  display: flex;
  flex-direction: column;
  overflow: hidden;
`;

const TraceName = styled.span`
  font-size: 13px;
  font-family: "Menlo", "Courier New", monospace;
  font-weight: 500;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
`;

const RunId = styled.span`
  font-size: 10px;
  font-family: monospace;
  color: #757575;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
`;

const Cell = styled.div<{ $flex: number; $align?: string }>`
  flex: ${(props) => props.$flex};
  font-size: 13px;
  padding: 0 6px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  text-align: ${(props) => props.$align || "left"};
`;

const Status = styled.span<{ $status: string }>`
  font-size: 13px;
  color: ${(props) => (props.$status === "success" ? "#2e7d32" : "#c62828")};
  font-weight: 600;
  text-transform: capitalize;
`;
