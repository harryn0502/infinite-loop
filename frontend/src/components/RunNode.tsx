import { useState } from "react";
import styled from "styled-components";
import { type NestedRunNode } from "../types";
import { calculateDuration, getRunIcon } from "../utils/format";

interface RunNodeProps {
  run: NestedRunNode;
  onSelect: (run: NestedRunNode) => void;
  selectedRunId?: string | null;
}

export const RunNode: React.FC<RunNodeProps> = ({ run, onSelect, selectedRunId }) => {
  const [isExpanded, setIsExpanded] = useState(true); // Default to expanded
  const hasChildren = run.children.length > 0;
  const isSelected = run.id === selectedRunId;

  const handleToggle = (e: React.MouseEvent) => {
    e.stopPropagation(); // Prevent selection when toggling
    setIsExpanded(!isExpanded);
  };

  const handleSelect = () => {
    onSelect(run);
  };

  return (
    <NodeWrapper>
      <NodeRow $active={isSelected} onClick={handleSelect}>
        <Toggle onClick={handleToggle}>{hasChildren ? (isExpanded ? "▼" : "►") : ""}</Toggle>
        <Icon>{getRunIcon(run.run_type)}</Icon>
        <Name>{run.name}</Name>
        <Duration>{calculateDuration(run.start_time, run.end_time)}</Duration>
      </NodeRow>
      {isExpanded && hasChildren && (
        <ChildrenContainer>
          {run.children.map((child) => (
            <RunNode key={child.id} run={child} onSelect={onSelect} selectedRunId={selectedRunId} />
          ))}
        </ChildrenContainer>
      )}
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
  cursor: pointer;
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

const Duration = styled.span`
  font-size: 13px;
  color: #757575;
  margin-left: auto;
  padding-right: 8px;
`;

const ChildrenContainer = styled.div`
  padding-left: 20px; // This creates the nesting effect
`;
