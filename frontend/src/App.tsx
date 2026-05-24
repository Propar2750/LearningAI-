import { useStore } from './store';
import GraphView from './views/GraphView';
import ChatView from './views/ChatView';
import ModeToggle from './components/ModeToggle';

export default function App() {
  const mode = useStore(s => s.mode);
  return (
    <div className="relative w-screen h-screen overflow-hidden bg-neutral-950 text-neutral-100">
      {mode === 'graph' ? <GraphView /> : <ChatView />}
      <ModeToggle />
    </div>
  );
}
