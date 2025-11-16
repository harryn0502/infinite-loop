import {
  ReactFlow,
  Background,
  Controls,
  MiniMap,
  useNodesState,
  useEdgesState,
  useReactFlow,
  type Node,
  type Edge,
  type NodeMouseHandler,
} from "@xyflow/react";
import { useEffect, useCallback } from "react";
import { TraceNode } from "./TraceNode";
import { type NestedRunNode } from "../types";

// Pass our custom node to React Flow
const nodeTypes = {
  traceNode: TraceNode,
};

// --- TYPE ALIAS ---
type NodeData = {
  run: NestedRunNode;
  sequence: number;
  isFocused?: boolean; // 👈 --- ADD isFocused (optional) ---
};
// --- END TYPE ALIAS ---

interface GraphViewProps {
  nodes: Node[];
  edges: Edge[];
  currentSequence: number;
  setCurrentSequence: (seq: number) => void;
  pausePlayback: () => void;
  setInspectedNode: (run: NestedRunNode) => void;
}

// You can style this better if you like
const EmptyState = (props: { children: React.ReactNode }) => (
  <div style={{ padding: "20px", color: "#777", fontStyle: "italic" }}>{props.children}</div>
);

export const GraphView = ({
  nodes: layoutedNodes,
  edges: layoutedEdges,
  currentSequence,
  setCurrentSequence,
  pausePlayback,
  setInspectedNode,
}: GraphViewProps) => {
  // Get layouted data
  const { fitView, getNodes } = useReactFlow();

  // Set up React Flow state
  const [nodes, setNodes, onNodesChange] = useNodesState<Node>([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState<Edge>([]);

  // Update state AND fit view when the layout changes
  useEffect(() => {
    setNodes(layoutedNodes);
    setEdges(layoutedEdges);

    if (layoutedNodes.length > 0) {
      const timer = setTimeout(() => {
        fitView({ duration: 400, minZoom: 0.05 });
      }, 10); // 10ms delay

      return () => clearTimeout(timer);
    }
  }, [layoutedNodes, layoutedEdges, setNodes, setEdges, fitView]);

  // --- FOCUS EFFECT (Camera) ---
  useEffect(() => {
    const allNodes = getNodes();
    if (allNodes.length === 0) return;

    // Find the currently active node
    const targetNode = allNodes.find((n) => n.data.sequence === currentSequence);

    if (targetNode) {
      fitView({
        nodes: [{ id: targetNode.id }],
        duration: 400,
        maxZoom: 1.5,
        padding: 0.1,
      });
    }
  }, [currentSequence, fitView, getNodes, nodes]);
  // --- END FOCUS EFFECT ---

  // 👇 --- THIS EFFECT IS MODIFIED --- 👇
  // This effect applies a 'glowing' class AND the 'isFocused' prop
  useEffect(() => {
    setNodes((nds) =>
      nds.map((node) => {
        const isFocused = node.data.sequence === currentSequence;
        return {
          ...node,
          className: isFocused ? "glowing" : "",
          data: { ...node.data, isFocused: isFocused }, // Inject the prop
        };
      })
    );
  }, [currentSequence, setNodes]); // Rerun when sequence changes or nodes are set
  // 👆 --- END OF MODIFICATION --- 👆

  // --- CLICK HANDLER ---
  const handleNodeClick: NodeMouseHandler = useCallback(
    (_event, node) => {
      // Assert the type of node.data inside the function
      const data = node.data as NodeData;

      const clickedSequence = data.sequence;

      if (typeof clickedSequence === "number") {
        pausePlayback(); // Stop the animation
        setCurrentSequence(clickedSequence); // Set the active node
      }

      // Set the node for inspection
      if (data.run) {
        setInspectedNode(data.run);
      }
    },
    [pausePlayback, setCurrentSequence, setInspectedNode]
  );
  // --- END CLICK HANDLER ---

  if (layoutedNodes.length === 0) {
    return <EmptyState>Select a run to view its graph</EmptyState>;
  }

  return (
    <div style={{ height: "100%", width: "100%" }}>
      <ReactFlow
        nodes={nodes}
        edges={edges}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        nodeTypes={nodeTypes}
        onNodeClick={handleNodeClick}
        minZoom={0.05}
      >
        <Background />
        <Controls />
        <MiniMap />
      </ReactFlow>
    </div>
  );
};
