import { useStore } from '../store';
import { NodeKind } from '../types';

const KIND_LABEL: Record<NodeKind, string> = {
  trunk: 'main path',
  side: 'side question',
  prereq: 'prerequisite',
};

const KIND_CHIP: Record<NodeKind, string> = {
  trunk: 'bg-neutral-700 text-neutral-100',
  side: 'bg-blue-900/60 text-blue-200',
  prereq: 'bg-amber-900/60 text-amber-200',
};

export default function ChatView() {
  const selectedNodeId = useStore(s => s.selectedNodeId);
  const graph = useStore(s => s.graph);
  const node = selectedNodeId
    ? graph.nodes.find(n => n.id === selectedNodeId) ?? null
    : null;

  if (!node) {
    return (
      <div className="absolute inset-0 flex items-center justify-center px-6">
        <div className="max-w-md text-center">
          <h2 className="text-lg font-semibold text-neutral-100 mb-2">
            Nothing selected yet
          </h2>
          <p className="text-sm text-neutral-400 leading-relaxed">
            Click a node in the graph to view its conversation.
            <br />
            Soon, the first prompt you send here will seed a new graph.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="absolute inset-0 flex flex-col">
      <header className="px-6 pt-6 pb-4 border-b border-neutral-800">
        <div className="flex items-center gap-2 mb-1">
          <span
            className={`text-[10px] uppercase tracking-wider px-2 py-0.5 rounded-full ${KIND_CHIP[node.kind]}`}
          >
            {KIND_LABEL[node.kind]}
          </span>
        </div>
        <h1 className="text-xl font-semibold text-neutral-100">{node.label}</h1>
      </header>

      <div className="flex-1 overflow-y-auto px-6 py-6">
        <div className="max-w-2xl mx-auto space-y-4">
          <div className="flex justify-end">
            <div className="max-w-[80%] rounded-2xl rounded-tr-md bg-blue-600 text-white px-4 py-3 text-sm leading-relaxed whitespace-pre-wrap">
              {node.turn.user}
            </div>
          </div>
          <div className="flex justify-start">
            <div className="max-w-[80%] rounded-2xl rounded-tl-md bg-neutral-800 text-neutral-100 px-4 py-3 text-sm leading-relaxed whitespace-pre-wrap">
              {node.turn.assistant}
            </div>
          </div>
        </div>
      </div>

      <footer className="px-6 py-4 border-t border-neutral-800">
        <div className="max-w-2xl mx-auto">
          <input
            type="text"
            disabled
            placeholder="Follow-up coming soon…"
            className="w-full rounded-lg bg-neutral-900 border border-neutral-800 px-4 py-3 text-sm text-neutral-100 placeholder-neutral-600 focus:outline-none disabled:cursor-not-allowed"
          />
        </div>
      </footer>
    </div>
  );
}
