import { useState } from "react";
import styled from "styled-components";
import { useTraceTree } from "../hooks/useTraceTree";
import { type NestedRunNode } from "../types";
import { RunNode } from "./RunNode";

export const LangSmithViewer = () => {
  const rootNodes = useTraceTree();
  const [selectedRun, setSelectedRun] = useState<NestedRunNode | null>(null);

  return (
    <Wrapper>
      <TraceListColumn>
        <ColumnHeader>Traces</ColumnHeader>
        <ListContainer>
          {rootNodes.map((run) => (
            <RunNode
              key={run.id}
              run={run}
              onSelect={setSelectedRun}
              selectedRunId={selectedRun?.id}
            />
          ))}
        </ListContainer>
      </TraceListColumn>
      <DetailColumn>
        <ColumnHeader>Run Details</ColumnHeader>
        <DetailContainer>
          {selectedRun ? (
            <pre>{JSON.stringify(selectedRun, null, 2)}</pre>
          ) : (
            <EmptyState>Select a run to see its details</EmptyState>
          )}
        </DetailContainer>
      </DetailColumn>
    </Wrapper>
  );
};

// --- Styled Components ---

const Wrapper = styled.div`
  display: flex;
  flex-direction: row;
  height: 100vh;
  width: 100vw;
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
  box-sizing: border-box;
`;

const BaseColumn = styled.div`
  height: 100%;
  display: flex;
  flex-direction: column;
  overflow: hidden;
`;

const TraceListColumn = styled(BaseColumn)`
  flex: 1;
  min-width: 300px;
  border-right: 1px solid #e0e0e0;
`;

const DetailColumn = styled(BaseColumn)`
  flex: 2;
  min-width: 400px;
`;

const ColumnHeader = styled.div`
  padding: 12px 16px;
  font-weight: 600;
  font-size: 16px;
  border-bottom: 1px solid #e0e0e0;
  background-color: #f9f9f9;
  flex-shrink: 0;
`;

const ListContainer = styled.div`
  overflow-y: auto;
  flex-grow: 1;
  padding: 8px;
`;

const DetailContainer = styled.div`
  overflow-y: auto;
  flex-grow: 1;
  padding: 16px;
  font-size: 13px;
  font-family: "Menlo", "Courier New", monospace;
  line-height: 1.6;

  pre {
    white-space: pre-wrap;
    word-wrap: break-word;
  }
`;

const EmptyState = styled.div`
  padding-top: 16px;
  color: #757575;
  font-style: italic;
`;
