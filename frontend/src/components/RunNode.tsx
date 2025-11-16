import styled from "styled-components";
// Import the new hook's type
import { type TraceHeader } from "../hooks/useTraces";
import { getRunIcon } from "../utils/format";

interface RunNodeProps {
  run: TraceHeader; // Use the new type
  onSelect: (run: TraceHeader) => void; // Use the new type
  selectedRunId?: string | null;
}

export const RunNode: React.FC<RunNodeProps> = ({ run, onSelect, selectedRunId }) => {
  // Removed all logic for expansion and children
  const isSelected = run.run_id === selectedRunId;

  const handleSelect = () => {
    onSelect(run);
  };

  return (
    <NodeWrapper>
      <NodeRow $active={isSelected} onClick={handleSelect}>
        <Toggle /> {/* Kept for alignment, but empty */}
        {/* Assume 'chain' icon for all root runs */}
        <Icon>{getRunIcon("chain")}</Icon>
        <Name>{run.name}</Name>
        {/* Use the status from the API */}
        <Status $status={run.status}>{run.status}</Status>
      </NodeRow>
    </NodeWrapper>
  );
};

// --- Styled Components ---

const NodeWrapper = styled.div`
  width: 100%;
`;

const NodeRow = styled.div<{ $active: boolean }>`
  display: flex;
  align-items: center;
  padding: 6px 4px;
  border-radius: 4px;
  cursor: pointer;
  background-color: ${(props) => (props.$active ? "#e3f2fd" : "transparent")};

  &:hover {
    background-color: ${(props) => (props.$active ? "#e3f2fd" : "#f5f5f5")};
  }
`;

const Toggle = styled.span`
  width: 20px;
  text-align: center;
  font-size: 10px;
  color: #757575;
`;

const Icon = styled.span`
  margin-right: 6px;
  font-size: 14px;
`;

const Name = styled.span`
  font-size: 14px;
  font-family: "Menlo", "Courier New", monospace;
  white-space: nowrap;
`;

// Replaced Duration with Status, as end_time isn't in the /traces response
const Status = styled.span<{ $status: string }>`
  font-size: 13px;
  color: ${(props) => (props.$status === "success" ? "#2e7d32" : "#c62828")};
  margin-left: auto;
  padding-right: 8px;
  font-weight: 600;
  text-transform: capitalize;
`;

// ChildrenContainer is no longer needed
