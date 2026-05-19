import { useStore } from '../store';

export function GoalBanner() {
  const goal = useStore((s) => s.graph.goal);
  return (
    <div className="fixed top-0 left-0 right-0 z-20 border-b border-neutral-800 bg-neutral-950/90 backdrop-blur px-4 py-2 text-sm">
      <span className="text-neutral-500 mr-2">Goal:</span>
      <span className="text-neutral-100">{goal.text}</span>
    </div>
  );
}
