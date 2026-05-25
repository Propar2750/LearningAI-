import { createClient } from '@supabase/supabase-js';

// Plain SPA: @supabase/ssr is only for server-rendered frameworks. supabase-js
// auto-detects the session in the OAuth redirect URL and persists it to
// localStorage, so the session survives reloads.
const url = import.meta.env.VITE_SUPABASE_URL;
const publishableKey = import.meta.env.VITE_SUPABASE_PUBLISHABLE_KEY;

if (!url || !publishableKey) {
  throw new Error(
    'Missing VITE_SUPABASE_URL or VITE_SUPABASE_PUBLISHABLE_KEY — copy .env.example to .env.local.',
  );
}

export const supabase = createClient(url, publishableKey);
