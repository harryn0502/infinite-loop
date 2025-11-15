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
} from "@xyflow/react";
import { useEffect } from "react";
import { TraceNode } from "./TraceNode";

// Pass our custom node to React Flow
const nodeTypes = {
  traceNode: TraceNode,
};

interface GraphViewProps {
  nodes: Node[];
  edges: Edge[];
  currentSequence: number;
}

// You can style this better if you like
const EmptyState = (props: { children: React.ReactNode }) => (
  <div style={{ padding: "20px", color: "#777", fontStyle: "italic" }}>{props.children}</div>
);

export const GraphView = ({
  nodes: layoutedNodes,
  edges: layoutedEdges,
  currentSequence,
}: GraphViewProps) => {
  // Get layouted data
  const { fitView, getNodes } = useReactFlow();

  // Set up React Flow state
  // --- FIX: Provide explicit types to the hooks ---
  const [nodes, setNodes, onNodesChange] = useNodesState<Node>([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState<Edge>([]);
  // --- END FIX ---

  // Update state when the layout changes (i.e., new run selected)
  useEffect(() => {
    setNodes(layoutedNodes);
    setEdges(layoutedEdges);
  }, [layoutedNodes, layoutedEdges, setNodes, setEdges]);

  // --- FOCUS EFFECT (Camera) ---
  // This effect traces the sequence
  useEffect(() => {
    const allNodes = getNodes();
    if (allNodes.length === 0) return;

    const targetNode = allNodes.find((n) => n.data.sequence === currentSequence);

    if (targetNode) {
      fitView({
        nodes: [{ id: targetNode.id }],
        duration: 400,
        maxZoom: 1.2, // Zoom in a bit
      });
    }
  }, [currentSequence, fitView, getNodes, nodes]); // re-run when 'nodes' is populated

  // --- GLOW EFFECT (Styling) ---
  // This effect applies a 'glowing' class to the active node
  useEffect(() => {
    setNodes((nds) =>
      nds.map((node) => {
        if (node.data.sequence === currentSequence) {
          // set classname for the current node
          return { ...node, className: "glowing" };
        }
        // remove classname from all other nodes
        return { ...node, className: "" };
      })
    );
  }, [currentSequence, setNodes]); // Rerun when sequence changes or nodes are set

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
        fitView
      >
        <Background />
        <Controls />
        <MiniMap />
      </ReactFlow>
    </div>
  );
};
