import { useStore } from '../store';

export default function ModeToggle() {
  const mode = useStore(s => s.mode);
  const toggle = useStore(s => s.toggleMode);

  const label = mode === 'chat' ? '✕  Graph' : '◉  Chat';

  return (
    <button
      onClick={toggle}
      className="absolute top-4 right-4 z-20 rounded-lg border border-neutral-700 bg-neutral-900/80 backdrop-blur px-3 py-1.5 text-sm text-neutral-200 hover:border-neutral-500 hover:text-white transition-colors"
      aria-label={mode === 'chat' ? 'Return to graph' : 'Open chat'}
    >
      {label}
    </button>
  );
}
