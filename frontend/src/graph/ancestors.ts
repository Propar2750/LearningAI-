import type { Graph } from '../types';

// Returns the ordered ancestor chain root -> node. With multiple parents,
// follows the first parent (good enough for v0 chat view).
export function getAncestorChain(graph: Graph, nodeId: string): string[] {
  const byId = new Map(graph.nodes.map((n) => [n.id, n]));
  const chain: string[] = [];
  let cur: string | undefined = nodeId;
  const seen = new Set<string>();
  while (cur && !seen.has(cur)) {
    seen.add(cur);
    chain.unshift(cur);
    const node = byId.get(cur);
    cur = node?.parentIds[0];
  }
  return chain;
}

// All ancestors of nodeId (inclusive), across every parent path. Used to
// dim non-ancestors in graph view on single-click.
export function getAllAncestors(graph: Graph, nodeId: string): Set<string> {
  const byId = new Map(graph.nodes.map((n) => [n.id, n]));
  const out = new Set<string>();
  const stack = [nodeId];
  while (stack.length) {
    const id = stack.pop()!;
    if (out.has(id)) continue;
    out.add(id);
    const node = byId.get(id);
    if (node) stack.push(...node.parentIds);
  }
  return out;
}
