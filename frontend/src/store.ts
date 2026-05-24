import { create } from 'zustand';
import { Graph, ViewMode } from './types';
import { mockGraph } from './mock/graph';

interface State {
  mode: ViewMode;
  selectedNodeId: string | null;
  graph: Graph;
  setMode: (m: ViewMode) => void;
  toggleMode: () => void;
  selectNode: (id: string) => void;
  clearSelection: () => void;
}

// Seeded synchronously from mockGraph so first render has data.
// Replace with `await getGraph()` once a real backend exists.
export const useStore = create<State>((set) => ({
  mode: 'graph',
  selectedNodeId: null,
  graph: JSON.parse(JSON.stringify(mockGraph)),
  setMode: (mode) => set({ mode }),
  toggleMode: () => set((s) => ({ mode: s.mode === 'graph' ? 'chat' : 'graph' })),
  selectNode: (id) => set({ selectedNodeId: id, mode: 'chat' }),
  clearSelection: () => set({ selectedNodeId: null }),
}));
