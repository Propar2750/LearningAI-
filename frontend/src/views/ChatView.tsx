import { motion } from 'framer-motion';
import { useStore } from '../store';
import { getAncestorChain } from '../graph/ancestors';
import { trunkTip } from '../graph/trunk';

export function ChatView() {
  const graph = useStore((s) => s.graph);
  const focusedNodeId = useStore((s) => s.focusedNodeId);

  const anchor = focusedNodeId ?? trunkTip(graph)?.id ?? graph.nodes[0]?.id;
  const chain = anchor ? getAncestorChain(graph, anchor) : [];
  const byId = new Map(graph.nodes.map((n) => [n.id, n]));

  return (
    <div className="min-h-full pt-16 pb-40 px-6">
      <div className="max-w-3xl mx-auto">
        {chain.length === 0 && (
          <div className="text-neutral-500 text-sm mt-24 text-center">
            How can I help you today?
          </div>
        )}

        <div className="flex flex-col gap-8">
          {chain.map((id) => {
            const n = byId.get(id);
            if (!n) return null;
            return (
              <motion.div
                key={n.id}
                layoutId={n.id}
                className="flex flex-col gap-6"
              >
                {/* User message — right-aligned bubble */}
                <div className="flex justify-end">
                  <div className="max-w-[80%] rounded-2xl bg-neutral-800 text-neutral-100 px-4 py-3 text-[15px] leading-relaxed whitespace-pre-wrap">
                    {n.prompt}
                  </div>
                </div>

                {/* Assistant message — full width, no bubble */}
                <div className="flex gap-3 items-start">
                  <div className="mt-1 h-7 w-7 rounded-full bg-gradient-to-br from-orange-400 to-amber-600 flex items-center justify-center text-[11px] font-semibold text-neutral-950 shrink-0">
                    C
                  </div>
                  <div className="flex-1 text-neutral-100 text-[15px] leading-relaxed whitespace-pre-wrap">
                    {n.reply}
                  </div>
                </div>
              </motion.div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
