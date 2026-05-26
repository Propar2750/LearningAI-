import { create } from 'zustand';
import type { Session, User } from '@supabase/supabase-js';
import { Graph, GraphSummary, ViewMode } from './types';
import { getGraph, getGraphs } from './api/client';
import { supabase } from './lib/supabase';

const EMPTY_GRAPH: Graph = { nodes: [], links: [] };

interface State {
  mode: ViewMode;
  selectedNodeId: string | null;
  graph: Graph;

  // Multiple graphs per user; null selection = show all merged.
  graphs: GraphSummary[];
  selectedGraphId: string | null;

  // Auth
  session: Session | null;
  user: User | null;
  authReady: boolean; // false until the first getSession() resolves

  setMode: (m: ViewMode) => void;
  toggleMode: () => void;
  selectNode: (id: string) => void;
  clearSelection: () => void;
  setSelectedGraphId: (id: string | null) => void;

  setSession: (session: Session | null) => void;
  signOut: () => Promise<void>;
  loadGraph: () => Promise<void>;
}

export const useStore = create<State>((set) => ({
  mode: 'graph',
  selectedNodeId: null,
  graph: EMPTY_GRAPH,

  graphs: [],
  selectedGraphId: null,

  session: null,
  user: null,
  authReady: false,

  setMode: (mode) => set({ mode }),
  toggleMode: () => set((s) => ({ mode: s.mode === 'graph' ? 'chat' : 'graph' })),
  selectNode: (id) => set({ selectedNodeId: id, mode: 'chat' }),
  clearSelection: () => set({ selectedNodeId: null }),
  setSelectedGraphId: (selectedGraphId) => set({ selectedGraphId }),

  setSession: (session) =>
    set({ session, user: session?.user ?? null, authReady: true }),

  signOut: async () => {
    await supabase.auth.signOut();
    // onAuthStateChange clears the session; reset graph/selection eagerly.
    set({
      graph: EMPTY_GRAPH,
      graphs: [],
      selectedGraphId: null,
      selectedNodeId: null,
      mode: 'graph',
    });
  },

  loadGraph: async () => {
    const [graph, graphs] = await Promise.all([getGraph(), getGraphs()]);
    set({ graph, graphs, selectedGraphId: null });
  },
}));
