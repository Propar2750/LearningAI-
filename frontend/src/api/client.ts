import type { Graph, GraphEdge, GraphNode } from '../types';
import { mockGraph } from '../mock/graph';
import { trunkTip } from '../graph/trunk';

// In-memory copy that mutates across calls — simulates a backend.
let state: Graph = structuredClone(mockGraph);

export async function getGraph(): Promise<Graph> {
  return structuredClone(state);
}

export interface PostPromptInput {
  prompt: string;
  focusedNodeId: string | null;
}

export interface PostPromptResult {
  node: GraphNode;
  edge: GraphEdge;
}

// Stub router: if the user is focused on a node, extend from there as a
// side-question (unless they're on the trunk tip, in which case continue the
// trunk). With no focus, extend the trunk tip. The real backend will own this.
export async function postPrompt({ prompt, focusedNodeId }: PostPromptInput): Promise<PostPromptResult> {
  const tip = trunkTip(state);
  const parentId = focusedNodeId ?? tip?.id ?? state.nodes[0]?.id;
  if (!parentId) throw new Error('Graph has no nodes');

  const parent = state.nodes.find((n) => n.id === parentId)!;
  const extendingTrunk = parent.isTrunk && parent.id === tip?.id;

  const newNode: GraphNode = {
    id: `m${Date.now()}`,
    prompt,
    reply: `(stub reply) You asked: "${prompt}". A real backend will answer this using the graph context around node ${parentId}.`,
    summary: prompt.slice(0, 60),
    parentIds: [parentId],
    createdAt: Date.now(),
    isTrunk: extendingTrunk,
  };

  const newEdge: GraphEdge = {
    from: parentId,
    to: newNode.id,
    type: extendingTrunk ? 'subtopic' : 'side-question',
  };

  state = {
    ...state,
    nodes: [...state.nodes, newNode],
    edges: [...state.edges, newEdge],
  };

  return { node: newNode, edge: newEdge };
}
