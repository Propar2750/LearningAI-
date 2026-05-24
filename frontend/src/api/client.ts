import { Graph, GNode } from '../types';
import { mockGraph } from '../mock/graph';

// Deep clone so callers can't mutate the source of truth.
function clone<T>(x: T): T {
  return JSON.parse(JSON.stringify(x));
}

let state: Graph = clone(mockGraph);

export async function getGraph(): Promise<Graph> {
  return clone(state);
}

export async function selectNode(id: string): Promise<GNode> {
  const n = state.nodes.find(n => n.id === id);
  if (!n) throw new Error(`unknown node: ${id}`);
  return clone(n);
}
