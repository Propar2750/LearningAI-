import type { Graph, GraphNode } from '../types';

export function trunkNodes(graph: Graph): GraphNode[] {
  return graph.nodes
    .filter((n) => n.isTrunk)
    .sort((a, b) => a.createdAt - b.createdAt);
}

export function trunkTip(graph: Graph): GraphNode | undefined {
  const trunk = trunkNodes(graph);
  return trunk[trunk.length - 1];
}

export function isTrunkEdge(graph: Graph, from: string, to: string): boolean {
  const a = graph.nodes.find((n) => n.id === from);
  const b = graph.nodes.find((n) => n.id === to);
  return !!a?.isTrunk && !!b?.isTrunk;
}
