import { useState, useMemo, useEffect, useRef, useCallback } from "react"; // Import useCallback
import styled from "styled-components";
import { useTraceTree } from "../hooks/useTraceTree";
import { type NestedRunNode } from "../types";
import { RunNode } from "./RunNode";
import { truncateJsonValues } from "../utils/format";
import { GraphView } from "./GraphView";
import { useFlowData } from "../hooks/useFlowData";
import { ReactFlowProvider } from "@xyflow/react";

type ActiveTab = "graph" | "json";

// --- Styled Components (Moved Up) ---
const Wrapper = styled.div`
  display: flex;
  flex-direction: row;
  height: 100vh;
  width: 100vw;
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
  box-sizing: border-box;
`;
// ... (all other styled components) ...
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

export const LangSmithViewer = () => {
  const rootNodes = useTraceTree();
  const [selectedRun, setSelectedRun] = useState<NestedRunNode | null>(null);
  const [activeTab, setActiveTab] = useState<ActiveTab>("graph");

  const { nodes, edges, maxSequence } = useFlowData(selectedRun);
  const [currentSequence, setCurrentSequence] = useState(1);
  const [isPlaying, setIsPlaying] = useState(false);
  const timerRef = useRef<number | null>(null);

  // --- FIX 1: Wrap pausePlayback in useCallback ---
  // We memoize it so it can be safely used in the useEffect dependency array.
  const pausePlayback = useCallback(() => {
    setIsPlaying(false);
    if (timerRef.current) {
      window.clearInterval(timerRef.current);
      timerRef.current = null;
    }
  }, [setIsPlaying]); // setIsPlaying is a stable function

  // Main playback logic
  useEffect(() => {
    // This logic now *only* runs when isPlaying is true
    if (isPlaying) {
      // Set up new timer
      timerRef.current = window.setInterval(() => {
        setCurrentSequence((s) => {
          if (s < maxSequence) {
            return s + 1;
          } else {
            // Auto-pause at the end
            pausePlayback();
            return s;
          }
        });
      }, 800);
    }
    // --- FIX 1: The 'else' block that called pausePlayback() is removed ---

    // The cleanup function handles *all* timer clearing.
    // It runs when isPlaying becomes false OR when the component unmounts.
    return () => {
      if (timerRef.current) {
        window.clearInterval(timerRef.current);
        timerRef.current = null;
      }
    };
  }, [isPlaying, maxSequence, pausePlayback]); // Add pausePlayback as a dependency

  // --- FIX 2: This useEffect is REMOVED ---
  // useEffect(() => {
  //   setCurrentSequence(1);
  //   pausePlayback(); // Stop playback
  // }, [selectedRun]);

  // --- FIX 2: Create a new event handler ---
  // This function batches all state updates into one, avoiding the 2-render problem
  const handleRunSelect = (run: NestedRunNode) => {
    setSelectedRun(run);
    setCurrentSequence(1);
    pausePlayback(); // This resets the player state
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
    const truncatedObj = truncateJsonValues(selectedRun, 100);
    return JSON.stringify(truncatedObj, null, 2);
  }, [selectedRun]);

  return (
    <Wrapper>
      <TraceListColumn>
        <ColumnHeader>Traces</ColumnHeader>
        <ListContainer>
          {rootNodes.map((run) => (
            <RunNode
              key={run.id}
              run={run}
              // --- FIX 2: Use the new handler ---
              onSelect={handleRunSelect}
              selectedRunId={selectedRun?.id}
            />
          ))}
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
              &#9632;
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
          {activeTab === "graph" && (
            <ReactFlowProvider>
              <GraphView nodes={nodes} edges={edges} currentSequence={currentSequence} />
            </ReactFlowProvider>
          )}

          {activeTab === "json" &&
            (selectedRun ? (
              <pre>{truncatedJson}</pre>
            ) : (
              <EmptyState>Select a run to see its details</EmptyState>
            ))}
        </DetailContainer>
      </DetailColumn>
    </Wrapper>
  );
};
