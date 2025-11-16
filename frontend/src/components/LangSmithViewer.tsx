import { useState, useMemo, useEffect, useRef, useCallback } from "react";
import styled from "styled-components";

// --- IMPORT NEW HOOKS ---
import { useTraces, type TraceHeader } from "../hooks/useTraces";
// 👇 --- IMPORT NestedRunNode HERE ---
import { useNestedTrace } from "../hooks/useNestedTrace";

import { RunNode } from "./RunNode";
import { truncateJsonValues } from "../utils/format";
import { GraphView } from "./GraphView";
import { useFlowData } from "../hooks/useFlowData";
import { ReactFlowProvider } from "@xyflow/react";
// 👇 --- IMPORT NEW MODAL ---
import { NodeInspectorModal } from "./NodeInspectorModal";
import type { NestedRunNode } from "../types";

type ActiveTab = "graph" | "json";

// --- Styled Components (No Changes) ---
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
const TabHeader = styled.div`
  display: flex;
  border-bottom: 1px solid #e0e0e0;
  padding: 0 16px;
  background-color: #f9f9f9;
  flex-shrink: 0;
`;
const TabButton = styled.button<{ $active: boolean }>`
  padding: 10px 16px;
  font-size: 14px;
  font-weight: 600;
  border: none;
  background: transparent;
  cursor: pointer;
  color: ${(props) => (props.$active ? "#0d47a1" : "#555")};
  border-bottom: 2px solid ${(props) => (props.$active ? "#0d47a1" : "transparent")};
  margin-bottom: -1px;
`;
const TracerControls = styled.div`
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 8px 16px;
  border-bottom: 1px solid #e0e0e0;
  background-color: #f9f9f9;
  flex-shrink: 0;
  gap: 12px;
`;
const TracerButton = styled.button`
  padding: 4px 12px;
  font-size: 14px;
  font-weight: 600;
  border-radius: 4px;
  border: 1px solid #ccc;
  background-color: #fff;
  cursor: pointer;
  width: 40px;
  height: 30px;
  padding: 0;
  line-height: 30px;
  text-align: center;

  &:hover:not(:disabled) {
    background-color: #f5f5f5;
  }

  &:disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }
`;
const Slider = styled.input`
  flex-grow: 1;
  margin: 0 8px;
`;
const SequenceDisplay = styled.span`
  font-size: 14px;
  font-weight: 600;
  color: #333;
  min-width: 50px;
  text-align: right;
`;
const DetailContainer = styled.div`
  overflow: auto;
  flex-grow: 1;

  pre {
    padding: 16px;
    font-size: 13px;
    font-family: "Menlo", "Courier New", monospace;
    line-height: 1.6;
    white-space: pre-wrap;
    word-wrap: break-word;
  }
`;
const EmptyState = styled.div`
  padding-top: 16px;
  padding-left: 16px;
  color: #757575;
  font-style: italic;
`;
// --- End Styled Components ---

export const LangSmithViewer = () => {
  // --- 1. HOOKS & DEBUGGING ---
  const traceListData = useTraces();
  const { traces: rootNodes, isLoading: isListLoading } = traceListData;

  console.log("Data from useTraces():", traceListData);

  // State for the *ID* of the selected run
  const [selectedRunId, setSelectedRunId] = useState<string | null>(null);

  // Fetch the full nested data for the selected run
  const { trace: selectedRun, isLoading: isTraceLoading } = useNestedTrace(selectedRunId);

  // --- (All other state remains the same) ---
  const [activeTab, setActiveTab] = useState<ActiveTab>("graph");
  const { nodes, edges, maxSequence } = useFlowData(selectedRun ?? null); // Pass null if undefined
  const [currentSequence, setCurrentSequence] = useState(1);
  const [isPlaying, setIsPlaying] = useState(false);
  const timerRef = useRef<number | null>(null);

  // 👇 --- ADD NEW STATE ---
  const [inspectedNode, setInspectedNode] = useState<NestedRunNode | null>(null);
  // 👆 --- END ADDITION ---

  // --- (Playback logic remains the same) ---
  const pausePlayback = useCallback(() => {
    setIsPlaying(false);
    if (timerRef.current) {
      window.clearInterval(timerRef.current);
      timerRef.current = null;
    }
  }, [setIsPlaying]);

  useEffect(() => {
    if (isPlaying) {
      timerRef.current = window.setInterval(() => {
        setCurrentSequence((s) => {
          if (s < maxSequence) {
            return s + 1;
          } else {
            pausePlayback();
            return s;
          }
        });
      }, 1500);
    }
    return () => {
      if (timerRef.current) {
        window.clearInterval(timerRef.current);
        timerRef.current = null;
      }
    };
  }, [isPlaying, maxSequence, pausePlayback]);

  // --- 2. UPDATE HANDLERS ---

  const handleRunSelect = (run: TraceHeader) => {
    // Only update if it's a new run
    if (run.run_id === selectedRunId) return;

    setSelectedRunId(run.run_id);

    // --- !! ADDED RESET LOGIC HERE !! ---
    // This is the correct place to reset state
    // React will batch these updates with setSelectedRunId
    setCurrentSequence(1);
    pausePlayback();
    // --- !! END ADDITION !! ---
  };

  const handlePlay = () => {
    if (currentSequence === maxSequence) {
      setCurrentSequence(1);
    }
    setIsPlaying(true);
  };

  const handlePause = () => {
    pausePlayback();
  };

  const handleStop = () => {
    pausePlayback();
    setCurrentSequence(1);
  };

  const handleSliderChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    pausePlayback();
    setCurrentSequence(Number(e.target.value));
  };

  const truncatedJson = useMemo(() => {
    if (!selectedRun) return "";

    // No cast is needed because truncateJsonValues now accepts 'unknown'
    const truncatedObj = truncateJsonValues(selectedRun, 100);

    return JSON.stringify(truncatedObj, null, 2);
  }, [selectedRun]);

  return (
    <Wrapper>
      <TraceListColumn>
        <ColumnHeader>Traces</ColumnHeader>
        <ListContainer>
          {isListLoading && <EmptyState>Loading traces...</EmptyState>}

          {/* --- 3. ADDED DEFENSIVE CHECK --- */}
          {/* We now also check if rootNodes is *actually* an array */}
          {Array.isArray(rootNodes)
            ? rootNodes.map((run) => (
                <RunNode
                  key={run.run_id}
                  run={run}
                  onSelect={handleRunSelect}
                  selectedRunId={selectedRunId}
                />
              ))
            : !isListLoading && <EmptyState>No traces found.</EmptyState>}
          {/* --- END DEFENSIVE CHECK --- */}
        </ListContainer>
      </TraceListColumn>
      <DetailColumn>
        <TabHeader>
          <TabButton $active={activeTab === "graph"} onClick={() => setActiveTab("graph")}>
            Graph
          </TabButton>
          <TabButton $active={activeTab === "json"} onClick={() => setActiveTab("json")}>
            JSON
          </TabButton>
        </TabHeader>

        {activeTab === "graph" && maxSequence > 0 && (
          <TracerControls>
            {!isPlaying ? (
              <TracerButton
                onClick={handlePlay}
                disabled={currentSequence === maxSequence && !isPlaying}
                title="Play"
              >
                &#9654;
              </TracerButton>
            ) : (
              <TracerButton onClick={handlePause} title="Pause">
                &#9208;
              </TracerButton>
            )}
            <TracerButton onClick={handleStop} title="Stop (Reset)">
              &#x23EE;
            </TracerButton>
            <Slider
              type="range"
              min="1"
              max={maxSequence}
              value={currentSequence}
              onChange={handleSliderChange}
            />
            <SequenceDisplay>
              {currentSequence} / {maxSequence}
            </SequenceDisplay>
          </TracerControls>
        )}

        <DetailContainer>
          {isTraceLoading && <EmptyState>Loading trace details...</EmptyState>}

          {!isTraceLoading && activeTab === "graph" && (
            <ReactFlowProvider>
              <GraphView
                nodes={nodes}
                edges={edges}
                currentSequence={currentSequence}
                setCurrentSequence={setCurrentSequence}
                pausePlayback={pausePlayback}
                setInspectedNode={setInspectedNode} // 👈 --- PASS PROP ---
              />
            </ReactFlowProvider>
          )}

          {!isTraceLoading &&
            activeTab === "json" &&
            (selectedRun ? (
              <pre>{truncatedJson}</pre>
            ) : (
              <EmptyState>Select a run to see its details</EmptyState>
            ))}
        </DetailContainer>
      </DetailColumn>

      {/* 👇 --- ADD MODAL RENDER --- 👇 */}
      {inspectedNode && (
        <NodeInspectorModal run={inspectedNode} onClose={() => setInspectedNode(null)} />
      )}
      {/* 👆 --- END ADDITION --- 👆 */}
    </Wrapper>
  );
};
