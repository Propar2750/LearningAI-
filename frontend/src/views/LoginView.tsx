import { useState } from 'react';
import type { Provider } from '@supabase/supabase-js';
import { supabase } from '../lib/supabase';

async function signIn(provider: Provider) {
  // In the browser this redirects to the provider; after consent the user lands
  // back at the app origin and supabase-js picks up the session from the URL.
  await supabase.auth.signInWithOAuth({
    provider,
    options: { redirectTo: window.location.origin },
  });
}

export default function LoginView() {
  const [busy, setBusy] = useState<Provider | null>(null);

  const onClick = (provider: Provider) => async () => {
    setBusy(provider);
    try {
      await signIn(provider);
    } catch {
      setBusy(null); // redirect failed; re-enable so the user can retry
    }
  };

  return (
    <div className="flex h-full w-full items-center justify-center">
      <div className="w-full max-w-xs space-y-6 px-6 text-center">
        <div>
          <h1 className="text-2xl font-semibold text-white">Learning.AI</h1>
          <p className="mt-1 text-sm text-neutral-400">Sign in to open your graph.</p>
        </div>
        <div className="space-y-3">
          <button
            onClick={onClick('github')}
            disabled={busy !== null}
            className="w-full rounded-lg border border-neutral-700 bg-neutral-900/80 px-4 py-2.5 text-sm text-neutral-100 hover:border-neutral-500 hover:text-white transition-colors disabled:opacity-50"
          >
            {busy === 'github' ? 'Redirecting…' : 'Continue with GitHub'}
          </button>
          <button
            onClick={onClick('google')}
            disabled={busy !== null}
            className="w-full rounded-lg border border-neutral-700 bg-neutral-900/80 px-4 py-2.5 text-sm text-neutral-100 hover:border-neutral-500 hover:text-white transition-colors disabled:opacity-50"
          >
            {busy === 'google' ? 'Redirecting…' : 'Continue with Google'}
          </button>
        </div>
      </div>
    </div>
  );
}
