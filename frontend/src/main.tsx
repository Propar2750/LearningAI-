import React from 'react';
import ReactDOM from 'react-dom/client';
import App from './App';
import { supabase } from './lib/supabase';
import { useStore } from './store';
import './index.css';

// Auth bootstrap (runs once). getSession() resolves authReady and the initial
// session; onAuthStateChange keeps it current (sign-in/out, token refresh).
// loadGraph() runs only on the transition into an authenticated state, so a
// token refresh doesn't refetch the graph.
function syncSession(session: Awaited<ReturnType<typeof supabase.auth.getSession>>['data']['session']) {
  const prev = useStore.getState().session;
  useStore.getState().setSession(session);
  if (session && !prev) {
    useStore.getState().loadGraph().catch((e) => console.error('loadGraph failed', e));
  }
}

supabase.auth.getSession().then(({ data }) => syncSession(data.session));
supabase.auth.onAuthStateChange((_event, session) => syncSession(session));

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);
