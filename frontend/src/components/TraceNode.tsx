import { Handle, Position } from "@xyflow/react";
import styled, { keyframes } from "styled-components";
import { type NestedRunNode } from "../types";
import { calculateDuration, getRunIcon } from "../utils/format";

// The data prop will be injected by React Flow
type TraceNodeData = {
  data: {
    run: NestedRunNode;
    sequence: number;
    isFocused?: boolean; // isFocused prop
  };
};

// Helper to format cost
const formatCost = (cost: number) => {
  if (cost === 0) return "$0.00";
  if (cost < 0.00001) {
    return `$${cost.toExponential(2)}`;
  }
  return `$${cost.toFixed(5)}`;
};

// Helper to format tokens
const formatTokens = (tokens: number) => {
  return tokens.toLocaleString();
};

export const TraceNode = ({ data: { run, sequence, isFocused } }: TraceNodeData) => {
  const status = run.error != null ? "error" : "success";

  // 👇 --- THIS IS THE FIX --- 👇
  // Extract all possible cost and token values
  let totalCost: number | null | undefined = null;
  let promptCost: number | null | undefined = null;
  let completionCost: number | null | undefined = null;

  let totalTokens: number | null | undefined = null;
  let inputTokens: number | null | undefined = null;
  let outputTokens: number | null | undefined = null;

  switch (run.run_type) {
    case "llm":
      totalCost = run.llm_total_cost;
      promptCost = run.llm_prompt_cost;
      completionCost = run.llm_completion_cost;
      totalTokens = run.llm_total_tokens;
      inputTokens = run.llm_input_tokens;
      outputTokens = run.llm_output_tokens;
      break;
    case "chain":
      totalCost = run.chain_total_cost;
      promptCost = run.chain_prompt_cost;
      completionCost = run.chain_completion_cost;
      totalTokens = run.chain_total_tokens;
      inputTokens = run.chain_prompt_tokens;
      outputTokens = run.chain_completion_tokens;
      break;
    default:
      // This will catch the root node ("agent_run")
      totalCost = run.total_cost;
      totalTokens = run.total_tokens;
      break;
  }

  // Check if we have any valid data to show in the footer
  const hasTokens = totalTokens != null && totalTokens > 0;
  const hasCost = totalCost != null && totalCost > 0;
  const showFooter = isFocused && (hasTokens || hasCost);
  // 👆 --- END OF FIX --- 👆

  return (
    <NodeBody $runType={run.run_type} $status={status}>
      {/* Handle for incoming edges (on the left) */}
      <Handle type="target" position={Position.Left} />

      <NodeHeader>
        <SequenceNumber>{sequence}</SequenceNumber>
        <Icon>{getRunIcon(run.run_type)}</Icon>
        <Name>{run.name}</Name>
        <Duration>{calculateDuration(run.start_time, run.end_time)}</Duration>
      </NodeHeader>

      {/* 👇 --- UPDATED FOOTER RENDERING --- 👇 */}
      {showFooter && (
        <NodeFooter>
          {hasTokens && (
            <InfoColumn>
              <InfoTitle>Tokens 🪙</InfoTitle>
              {inputTokens != null && <InfoItem>In: {formatTokens(inputTokens)}</InfoItem>}
              {outputTokens != null && <InfoItem>Out: {formatTokens(outputTokens)}</InfoItem>}
              <InfoItem $total>Total: {formatTokens(totalTokens!)}</InfoItem>
            </InfoColumn>
          )}
          {hasCost && (
            <InfoColumn>
              <InfoTitle>Cost 💲</InfoTitle>
              {promptCost != null && <InfoItem>In: {formatCost(promptCost)}</InfoItem>}
              {completionCost != null && <InfoItem>Out: {formatCost(completionCost)}</InfoItem>}
              <InfoItem $total>Total: {formatCost(totalCost!)}</InfoItem>
            </InfoColumn>
          )}
        </NodeFooter>
      )}
      {/* 👆 --- END OF UPDATED FOOTER --- 👆 */}

      {/* Handle for outgoing edges (on the right) */}
      <Handle type="source" position={Position.Right} />
    </NodeBody>
  );
};

// --- Styled Components ---

const getNodeColor = (runType: string) => {
  switch (runType) {
    case "llm":
      return "#e3f2fd"; // Light Blue
    case "chain":
      return "#e8f5e9"; // Light Green
    case "tool":
      return "#fff3e0"; // Light Orange
    default:
      return "#f5f5f5"; // Grey
  }
};

// ... (glow and redGlow keyframes remain the same) ...
const glow = keyframes`
  0% { box-shadow: 0 0 5px #0d47a1; }
  50% { box-shadow: 0 0 15px 5px #0d47a1; }
  100% { box-shadow: 0 0 5px #0d47a1; }
`;

const redGlow = keyframes`
  0% { box-shadow: 0 0 5px #c62828; }
  50% { box-shadow: 0 0 15px 5px #c62828; }
  100% { box-shadow: 0 0 5px #c62828; }
`;

const NodeBody = styled.div<{ $runType: string; $status: string }>`
  min-width: 250px;
  max-width: 350px;
  border-radius: 6px;
  background: ${(props) => getNodeColor(props.$runType)};
  border: 1px solid ${(props) => (props.$status === "success" ? "#ddd" : "#c62828")};
  border-width: ${(props) => (props.$status === "success" ? "1px" : "2px")};
  padding: 8px 12px;
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
  transition: box-shadow 0.3s ease, border-color 0.3s ease;

  .react-flow__node.glowing & {
    border-color: #0d47a1;
    animation: ${glow} 1.5s infinite;

    ${(props) =>
      props.$status !== "success" &&
      `
      border-color: #c62828;
      animation: ${redGlow} 1.5s infinite;
    `}
  }
`;

// ... (NodeHeader, SequenceNumber, Icon, Name, Duration remain the same) ...
const NodeHeader = styled.div`
  display: flex;
  align-items: center;
  font-size: 14px;
`;

const SequenceNumber = styled.span`
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 10px;
  font-weight: 600;
  color: #555;
  background: #fff;
  border: 1px solid #ccc;
  border-radius: 50%;
  width: 20px;
  height: 20px;
  margin-right: 8px;
  flex-shrink: 0;
`;

const Icon = styled.span`
  margin-right: 8px;
  font-size: 16px;
`;

const Name = styled.span`
  font-weight: 600;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
`;

const Duration = styled.span`
  font-size: 13px;
  color: #555;
  margin-left: auto;
  padding-left: 8px;
`;

// 👇 --- UPDATED & NEW STYLED COMPONENTS FOR FOOTER --- 👇

const NodeFooter = styled.div`
  display: grid;
  /* Create two columns of equal size */
  grid-template-columns: 1fr 1fr;
  gap: 12px;
  padding-top: 8px;
  margin-top: 8px;
  border-top: 1px solid #ddd;
`;

const InfoColumn = styled.div`
  display: flex;
  flex-direction: column;
  gap: 2px;
`;

const InfoTitle = styled.div`
  font-size: 13px;
  font-weight: 600;
  color: #333;
  margin-bottom: 2px;
`;

const InfoItem = styled.div<{ $total?: boolean }>`
  display: flex;
  align-items: center;
  font-size: 13px;
  color: #333;
  font-family: "Menlo", "Courier New", monospace;
  font-weight: ${(props) => (props.$total ? "600" : "normal")};
  margin-top: ${(props) => (props.$total ? "2px" : "0")};
`;

// InfoIcon is no longer used, so it can be removed
// const InfoIcon = styled.span`
//   margin-right: 5px;
//   font-size: 12px;
// `;
// 👆 --- END OF UPDATED STYLED COMPONENTS --- 👆
