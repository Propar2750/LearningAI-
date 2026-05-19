import { useState } from 'react';
import { useStore } from '../store';
import { trunkTip } from '../graph/trunk';

export function PromptInput() {
  const [value, setValue] = useState('');
  const [busy, setBusy] = useState(false);
  const mode = useStore((s) => s.mode);
  const graph = useStore((s) => s.graph);
  const focusedNodeId = useStore((s) => s.focusedNodeId);
  const submitPrompt = useStore((s) => s.submitPrompt);

  const focusedNode = focusedNodeId ? graph.nodes.find((n) => n.id === focusedNodeId) : undefined;
  const tip = trunkTip(graph);

  let target: string;
  if (mode === 'chat') {
    target = focusedNode ? `continuing: ${focusedNode.summary}` : tip ? `continuing: ${tip.summary}` : 'new conversation';
  } else {
    target = 'auto (router decides)';
  }

  async function submit() {
    const v = value.trim();
    if (!v || busy) return;
    setBusy(true);
    try {
      await submitPrompt(v);
      setValue('');
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="fixed bottom-0 left-0 right-0 z-20 px-4 pb-6 pt-3 bg-gradient-to-t from-neutral-950 via-neutral-950/95 to-transparent">
      <div className="max-w-3xl mx-auto">
        <div className="rounded-3xl border border-neutral-700 bg-neutral-900 shadow-lg focus-within:border-neutral-500 transition-colors">
          <textarea
            className="w-full bg-transparent resize-none px-5 pt-4 pb-2 text-[15px] text-neutral-100 placeholder-neutral-500 focus:outline-none"
            placeholder="Reply to Claude…"
            rows={1}
            value={value}
            onChange={(e) => {
              setValue(e.target.value);
              e.target.style.height = 'auto';
              e.target.style.height = Math.min(e.target.scrollHeight, 200) + 'px';
            }}
            onKeyDown={(e) => {
              if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                void submit();
              }
            }}
            disabled={busy}
          />
          <div className="flex items-center justify-between px-4 pb-3">
            <div className="text-[11px] text-neutral-500 truncate">{target}</div>
            <button
              className="rounded-full bg-neutral-100 hover:bg-white text-neutral-950 h-8 w-8 flex items-center justify-center disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
              onClick={() => void submit()}
              disabled={busy || !value.trim()}
              aria-label="Send"
            >
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                <line x1="12" y1="19" x2="12" y2="5" />
                <polyline points="5 12 12 5 19 12" />
              </svg>
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
