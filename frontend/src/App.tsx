import { useEffect } from 'react';
import { AnimatePresence, motion } from 'framer-motion';
import { useStore } from './store';
import { ChatView } from './views/ChatView';
import { GraphView } from './views/GraphView';
import { PromptInput } from './components/PromptInput';
import { GoalBanner } from './components/GoalBanner';

export default function App() {
  const mode = useStore((s) => s.mode);
  const setMode = useStore((s) => s.setMode);

  useEffect(() => {
    function onKey(e: KeyboardEvent) {
      // cmd/ctrl + ` toggles mode
      if ((e.metaKey || e.ctrlKey) && e.key === '`') {
        e.preventDefault();
        setMode(mode === 'chat' ? 'graph' : 'chat');
      } else if (e.key === 'Escape' && mode === 'chat') {
        setMode('graph');
      }
    }
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [mode, setMode]);

  return (
    <div className="relative h-full w-full overflow-hidden">
      <GoalBanner />

      <button
        className="fixed top-2 right-4 z-30 text-xs rounded bg-neutral-800 hover:bg-neutral-700 px-3 py-1.5 border border-neutral-700"
        onClick={() => setMode(mode === 'chat' ? 'graph' : 'chat')}
      >
        {mode === 'chat' ? 'Graph view' : 'Chat view'} <span className="text-neutral-500 ml-1">⌘`</span>
      </button>

      <AnimatePresence mode="wait">
        {mode === 'chat' ? (
          <motion.div
            key="chat"
            className="absolute inset-0 overflow-y-auto"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.15 }}
          >
            <ChatView />
          </motion.div>
        ) : (
          <motion.div
            key="graph"
            className="absolute inset-0"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.15 }}
          >
            <GraphView />
          </motion.div>
        )}
      </AnimatePresence>

      <PromptInput />
    </div>
  );
}
