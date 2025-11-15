import { useMemo } from "react";
import type { Edge, Node } from "@xyflow/react";
import type { NestedRunNode } from "../types";
import dagre from "dagre";

// REMOVE dagreGraph creation from here

const getLayoutedElements = (run: NestedRunNode) => {
  // --- ADD THESE LINES ---
  // Create a new graph instance *every time*
  const dagreGraph = new dagre.graphlib.Graph();
  dagreGraph.setDefaultEdgeLabel(() => ({}));

  // Set layout options
  const NODE_WIDTH = 280;
  const NODE_HEIGHT = 50;
  dagreGraph.setGraph({ rankdir: "LR", nodesep: 30, ranksep: 70 });
  // --- END ADDED LINES ---

  const nodes: Node[] = [];
  const edges: Edge[] = [];
  const nodeMap = new Map<string, NestedRunNode>();
  const allNodes: NestedRunNode[] = [];

  // Recursive function to collect all nodes for sorting
  const collectNodes = (runNode: NestedRunNode) => {
    allNodes.push(runNode);
    runNode.children.forEach(collectNodes);
  };
  // Collect all nodes starting from the root
  collectNodes(run);

  // Sort nodes by start time
  allNodes.sort((a, b) => new Date(a.start_time).getTime() - new Date(b.start_time).getTime());

  // Create a map of node ID to its sequence number
  const sequenceMap = new Map<string, number>();
  allNodes.forEach((node, index) => {
    sequenceMap.set(node.id, index + 1);
  });

  // Recursive function to add nodes and edges to Dagre
  const addNodesAndEdges = (runNode: NestedRunNode) => {
    // Add to map for later retrieval
    nodeMap.set(runNode.id, runNode);

    // Set the node in Dagre graph
    dagreGraph.setNode(runNode.id, {
      width: NODE_WIDTH,
      height: NODE_HEIGHT,
    });

    runNode.children.forEach((child) => {
      // Set the edge in Dagre graph
      dagreGraph.setEdge(runNode.id, child.id);
      // Recurse
      addNodesAndEdges(child);
    });
  };

  // Start building the graph from the root
  addNodesAndEdges(run);

  // Run the layout algorithm
  dagre.layout(dagreGraph);

  // Create React Flow nodes from Dagre layout
  dagreGraph.nodes().forEach((nodeId) => {
    const node = dagreGraph.node(nodeId);
    if (node) {
      nodes.push({
        id: nodeId,
        type: "traceNode", // This matches our custom node
        position: {
          x: node.x - NODE_WIDTH / 2, // Dagre's (x,y) is the center
          y: node.y - NODE_HEIGHT / 2,
        },
        data: {
          run: nodeMap.get(nodeId)!, // Get the original run data
          sequence: sequenceMap.get(nodeId)!, // Add the sequence number
        },
      });
    }
  });

  // Create React Flow edges
  dagreGraph.edges().forEach((edge) => {
    edges.push({
      id: `${edge.v}-${edge.w}`,
      source: edge.v,
      target: edge.w,
      animated: true,
      style: { stroke: "#777" },
    });
  });

  const maxSequence = allNodes.length;
  return { nodes, edges, maxSequence };
};

export const useFlowData = (
  run: NestedRunNode | null
): { nodes: Node[]; edges: Edge[]; maxSequence: number } => {
  return useMemo(() => {
    if (!run) {
      return { nodes: [], edges: [], maxSequence: 0 };
    }
    return getLayoutedElements(run);
  }, [run]);
};
