import { Graph, GNode } from '../types';
import { supabase } from '../lib/supabase';

const BASE_URL = import.meta.env.VITE_API_BASE_URL;

async function authedFetch<T>(path: string): Promise<T> {
  const { data } = await supabase.auth.getSession();
  const token = data.session?.access_token;
  if (!token) throw new Error('not authenticated');

  const res = await fetch(`${BASE_URL}${path}`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!res.ok) {
    throw new Error(`${path} failed: ${res.status} ${res.statusText}`);
  }
  return res.json() as Promise<T>;
}

export function getGraph(): Promise<Graph> {
  return authedFetch<Graph>('/api/graph');
}

export function selectNode(id: string): Promise<GNode> {
  return authedFetch<GNode>(`/api/nodes/${encodeURIComponent(id)}`);
}
