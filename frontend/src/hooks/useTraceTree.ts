import { useMemo } from "react";
import rawTraces from "../data/langsmith_traces.json";
import type { NestedRunNode, RawLangSmithRun } from "../types";

export const useTraceTree = (): NestedRunNode[] => {
  const rootNodes = useMemo(() => {
    const traces = rawTraces as RawLangSmithRun[];

    // 1. Create a map for easy lookup and to add the 'children' property
    const nodeMap: Map<string, NestedRunNode> = new Map();
    for (const run of traces) {
      nodeMap.set(run.id, {
        ...run,
        children: [],
      });
    }

    // 2. Build the tree structure
    const roots: NestedRunNode[] = [];
    for (const node of nodeMap.values()) {
      const parentId = node.parent_run_id;

      if (parentId && nodeMap.has(parentId)) {
        // This is a child node
        nodeMap.get(parentId)!.children.push(node);
      } else {
        // This is a root node
        roots.push(node);
      }
    }

    // Optional: Sort children by start_time
    const sortNodes = (node: NestedRunNode) => {
      node.children.sort(
        (a, b) => new Date(a.start_time).getTime() - new Date(b.start_time).getTime()
      );
      node.children.forEach(sortNodes);
    };
    roots.forEach(sortNodes);

    return roots;
  }, []);

  return rootNodes;
};
