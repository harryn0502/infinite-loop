import { Handle, Position } from "@xyflow/react";
import styled, { keyframes } from "styled-components";
import { type NestedRunNode } from "../types";
import { calculateDuration, getRunIcon } from "../utils/format";

// The data prop will be injected by React Flow
type TraceNodeData = {
  data: {
    run: NestedRunNode;
    sequence: number; // Add sequence to the type
  };
};

export const TraceNode = ({ data: { run, sequence } }: TraceNodeData) => {
  return (
    <NodeBody $runType={run.run_type}>
      {/* Handle for incoming edges (on the left) */}
      <Handle type="target" position={Position.Left} />

      <NodeHeader>
        <SequenceNumber>{sequence}</SequenceNumber>
        <Icon>{getRunIcon(run.run_type)}</Icon>
        <Name>{run.name}</Name>
        <Duration>{calculateDuration(run.start_time, run.end_time)}</Duration>
      </NodeHeader>

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

// Define the glow keyframes
const glow = keyframes`
  0% {
    box-shadow: 0 0 5px #0d47a1;
  }
  50% {
    box-shadow: 0 0 15px 5px #0d47a1;
  }
  100% {
    box-shadow: 0 0 5px #0d47a1;
  }
`;

const NodeBody = styled.div<{ $runType: string }>`
  min-width: 250px;
  max-width: 350px;
  border-radius: 6px;
  background: ${(props) => getNodeColor(props.$runType)};
  border: 1px solid #ddd;
  padding: 8px 12px;
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
  transition: box-shadow 0.3s ease; // Add a transition for smoothness

  // React Flow applies the class to the parent wrapper
  .react-flow__node.glowing & {
    border-color: #0d47a1;
    animation: ${glow} 1.5s infinite;
  }
`;

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
