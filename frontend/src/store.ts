import { create } from 'zustand';
import type { Graph, ViewMode } from './types';
import { mockGraph } from './mock/graph';
import * as api from './api/client';
import { recompute, type Position } from './graph/layout';

interface State {
  graph: Graph;
  positions: Map<string, Position>;
  mode: ViewMode;
  focusedNodeId: string | null;
  highlightedNodeId: string | null;
  setMode: (m: ViewMode) => void;
  focusNode: (id: string | null) => void;
  highlightNode: (id: string | null) => void;
  submitPrompt: (prompt: string) => Promise<void>;
  loadGraph: () => Promise<void>;
}

const initialPositions = recompute(mockGraph, new Map());

export const useStore = create<State>((set, get) => ({
  graph: mockGraph,
  positions: initialPositions,
  mode: 'chat',
  focusedNodeId: null,
  highlightedNodeId: null,

  setMode: (mode) => set({ mode }),
  focusNode: (focusedNodeId) => set({ focusedNodeId, highlightedNodeId: null }),
  highlightNode: (highlightedNodeId) => set({ highlightedNodeId }),

  loadGraph: async () => {
    const graph = await api.getGraph();
    set({ graph, positions: recompute(graph, get().positions) });
  },

  submitPrompt: async (prompt) => {
    const { focusedNodeId, mode } = get();
    await api.postPrompt({ prompt, focusedNodeId });
    const graph = await api.getGraph();
    const positions = recompute(graph, get().positions);
    const latest = graph.nodes[graph.nodes.length - 1];
    set({
      graph,
      positions,
      focusedNodeId: mode === 'chat' ? latest.id : focusedNodeId,
    });
  },
}));
