import { useStore } from './store';
import GraphView from './views/GraphView';
import ChatView from './views/ChatView';
import ModeToggle from './components/ModeToggle';
import LoginView from './views/LoginView';

export default function App() {
  const mode = useStore(s => s.mode);
  const session = useStore(s => s.session);
  const authReady = useStore(s => s.authReady);
  const signOut = useStore(s => s.signOut);

  return (
    <div className="relative w-screen h-screen overflow-hidden bg-neutral-950 text-neutral-100">
      {!authReady ? (
        <div className="flex h-full w-full items-center justify-center text-sm text-neutral-500">
          Loading…
        </div>
      ) : !session ? (
        <LoginView />
      ) : (
        <>
          {mode === 'graph' ? <GraphView /> : <ChatView />}
          <ModeToggle />
          <button
            onClick={signOut}
            className="absolute top-4 left-4 z-20 rounded-lg border border-neutral-700 bg-neutral-900/80 backdrop-blur px-3 py-1.5 text-sm text-neutral-400 hover:border-neutral-500 hover:text-white transition-colors"
          >
            Sign out
          </button>
        </>
      )}
    </div>
  );
}
