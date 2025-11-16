import styled from "styled-components";
// 👇 --- Import the TraceMessage type ---
import { type NestedRunNode, type TraceMessage } from "../types";
import { truncateJsonValues } from "../utils/format";

interface NodeInspectorModalProps {
  run: NestedRunNode;
  onClose: () => void;
}

// --- Helper Functions (No Changes) ---
const isDataEmpty = (data: unknown): boolean => {
  if (data === null || data === undefined || data === "") {
    return true;
  }
  if (typeof data === "object" && !Array.isArray(data) && Object.keys(data).length === 0) {
    return true;
  }
  if (Array.isArray(data) && data.length === 0) {
    return true;
  }
  return false;
};

const formatData = (data: unknown): string => {
  if (isDataEmpty(data)) {
    return "(Empty)";
  }

  if (typeof data === "string") {
    const stringData = data;
    try {
      const parsedJson = JSON.parse(stringData);
      data = parsedJson; // It's JSON, so we'll format it
    } catch {
      // It's just a plain string, return it as-is
      return stringData;
    }
  }

  try {
    const truncated = truncateJsonValues(data, 100);
    return JSON.stringify(truncated, null, 2);
  } catch {
    return "Could not stringify data.";
  }
};

// 👇 --- 1. ADD TYPE GUARD --- 👇
/**
 * Checks if the data is a valid array of TraceMessage objects.
 */
const isTraceMessageArray = (data: unknown): data is TraceMessage[] => {
  return (
    Array.isArray(data) &&
    data.length > 0 &&
    typeof data[0] === "object" &&
    data[0] !== null &&
    "content" in data[0] &&
    "type" in data[0]
  );
};

// 👇 --- 2. ADD NEW CHAT VIEWER COMPONENT --- 👇
/**
 * Renders an array of TraceMessages in a human-readable chat format.
 */
const ChatMessageViewer: React.FC<{ messages: TraceMessage[] }> = ({ messages }) => {
  return (
    <ChatViewerWrapper>
      {messages.map((msg, index) => (
        <MessageWrapper key={index} $type={msg.type}>
          <MessageHeader $type={msg.type}>{msg.type}</MessageHeader>
          <MessageContent>{String(msg.content)}</MessageContent>
        </MessageWrapper>
      ))}
    </ChatViewerWrapper>
  );
};
// 👆 --- END OF NEW COMPONENT --- 👆

export const NodeInspectorModal = ({ run, onClose }: NodeInspectorModalProps) => {
  const handleBackdropClick = (e: React.MouseEvent<HTMLDivElement>) => {
    if (e.target === e.currentTarget) {
      onClose();
    }
  };

  // Logic for finding inputs/outputs remains the same
  let inputs: unknown;
  let outputs: unknown;

  switch (run.run_type) {
    case "llm":
      inputs = run.prompt_text;
      outputs = run.llm_output_text;
      break;
    case "chain":
      inputs = run.chain_input_messages ?? run.inputs;
      outputs = run.chain_output_messages ?? run.outputs;
      break;
    case "tool":
      inputs = run.tool_args;
      outputs = run.tool_response;
      break;
    default:
      inputs = run.input_messages ?? run.inputs;
      outputs = run.output_messages ?? run.outputs;
      break;
  }

  return (
    <Backdrop onClick={handleBackdropClick}>
      <ModalBody>
        <Header>
          <Title>{run.name}</Title>
          <CloseButton onClick={onClose}>&times;</CloseButton>
        </Header>
        <Content>
          <Section>
            <SectionTitle>Inputs</SectionTitle>
            {/* 👇 --- 3. ADD CONDITIONAL RENDER LOGIC --- 👇 */}
            {isTraceMessageArray(inputs) ? (
              <ChatMessageViewer messages={inputs} />
            ) : (
              <JsonPre $isEmpty={isDataEmpty(inputs)}>{formatData(inputs)}</JsonPre>
            )}
            {/* 👆 --- END OF CHANGE --- 👆 */}
          </Section>

          {outputs !== undefined && (
            <Section>
              <SectionTitle>Outputs</SectionTitle>
              {/* 👇 --- 3. ADD CONDITIONAL RENDER LOGIC --- 👇 */}
              {isTraceMessageArray(outputs) ? (
                <ChatMessageViewer messages={outputs} />
              ) : (
                <JsonPre $isEmpty={isDataEmpty(outputs)}>{formatData(outputs)}</JsonPre>
              )}
              {/* 👆 --- END OF CHANGE --- 👆 */}
            </Section>
          )}

          {run.error && (
            <Section>
              <SectionTitle>Error</SectionTitle>
              <ErrorPre>{run.error}</ErrorPre>
            </Section>
          )}
        </Content>
      </ModalBody>
    </Backdrop>
  );
};

// --- Styled Components (Modal styles are unchanged) ---

const Backdrop = styled.div`
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
  padding: 20px;
`;

const ModalBody = styled.div`
  background: white;
  border-radius: 8px;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.2);
  width: 100%;
  max-width: 700px;
  max-height: 90vh;
  display: flex;
  flex-direction: column;
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
`;

const Header = styled.div`
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px 24px;
  border-bottom: 1px solid #e0e0e0;
`;

const Title = styled.h2`
  margin: 0;
  font-size: 18px;
  font-weight: 600;
`;

const CloseButton = styled.button`
  border: none;
  background: transparent;
  font-size: 28px;
  font-weight: 300;
  color: #777;
  cursor: pointer;
  padding: 0;
  line-height: 1;

  &:hover {
    color: #000;
  }
`;

const Content = styled.div`
  padding: 24px;
  overflow-y: auto;
`;

const Section = styled.div`
  margin-bottom: 20px;
  &:last-of-type {
    margin-bottom: 0;
  }
`;

const SectionTitle = styled.h3`
  font-size: 16px;
  font-weight: 600;
  margin-top: 0;
  margin-bottom: 8px;
  color: #333;
`;

const JsonPre = styled.pre<{ $isEmpty?: boolean }>`
  background: #f5f5f5;
  border: 1px solid #ddd;
  border-radius: 4px;
  padding: 12px;
  font-size: 13px;
  font-family: "Menlo", "Courier New", monospace;
  line-height: 1.6;
  white-space: pre-wrap;
  word-wrap: break-word;
  margin: 0;

  ${(props) =>
    props.$isEmpty &&
    `
    color: #757575;
    font-style: italic;
  `}
`;

const ErrorPre = styled(JsonPre)`
  background: #fff0f0;
  border-color: #c62828;
  color: #c62828;
  font-style: normal;
`;

// 👇 --- 4. ADD NEW STYLED COMPONENTS FOR CHAT --- 👇

const ChatViewerWrapper = styled.div`
  display: flex;
  flex-direction: column;
  gap: 12px;
  border: 1px solid #ddd;
  border-radius: 4px;
  background: #fdfdfd;
`;

const getMessageColors = (type: string) => {
  switch (type) {
    case "human":
      return { bg: "#e3f2fd", border: "#bbdefb", header: "#0d47a1" };
    case "ai":
      return { bg: "#e8f5e9", border: "#c8e6c9", header: "#1b5e20" };
    case "tool":
      return { bg: "#fff3e0", border: "#ffe0b2", header: "#e65100" };
    default:
      return { bg: "#f5f5f5", border: "#e0e0e0", header: "#333" };
  }
};

const MessageWrapper = styled.div<{ $type: string }>`
  background: ${(props) => getMessageColors(props.$type).bg};
  border: 1px solid ${(props) => getMessageColors(props.$type).border};
  border-radius: 4px;
  margin: -1px; // Allow borders to collapse
`;

const MessageHeader = styled.div<{ $type: string }>`
  padding: 6px 12px;
  font-size: 12px;
  font-weight: 600;
  text-transform: capitalize;
  color: ${(props) => getMessageColors(props.$type).header};
  border-bottom: 1px solid ${(props) => getMessageColors(props.$type).border};
`;

const MessageContent = styled.pre`
  padding: 12px;
  font-size: 14px;
  font-family: "Menlo", "Courier New", monospace;
  line-height: 1.6;
  white-space: pre-wrap;
  word-wrap: break-word;
  margin: 0;
  color: #222;
`;
// 👆 --- END OF NEW STYLED COMPONENTS --- 👆
