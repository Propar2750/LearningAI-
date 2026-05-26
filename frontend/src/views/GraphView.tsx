import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import ForceGraph2D, { ForceGraphMethods } from 'react-force-graph-2d';
import { useStore } from '../store';
import { NodeKind } from '../types';

const KIND_COLOR: Record<NodeKind, string> = {
  trunk: '#e5e7eb',
  side: '#60a5fa',
  prereq: '#fbbf24',
};

export default function GraphView() {
  const graph = useStore(s => s.graph);
  const selectNode = useStore(s => s.selectNode);
  const selectedNodeId = useStore(s => s.selectedNodeId);
  const graphs = useStore(s => s.graphs);
  const selectedGraphId = useStore(s => s.selectedGraphId);
  const setSelectedGraphId = useStore(s => s.setSelectedGraphId);

  const fgRef = useRef<ForceGraphMethods>();
  const [hovered, setHovered] = useState<string | null>(null);
  const [input, setInput] = useState('');
  const [size, setSize] = useState({ w: window.innerWidth, h: window.innerHeight });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const text = input.trim();
    if (!text) return;
    // Stub — wire this to the backend later.
    console.log('graph chat submit:', text);
    setInput('');
  };

  useEffect(() => {
    const onResize = () => setSize({ w: window.innerWidth, h: window.innerHeight });
    window.addEventListener('resize', onResize);
    return () => window.removeEventListener('resize', onResize);
  }, []);

  // Filter to one graph (null = show all merged), then clone for ForceGraph2D —
  // it mutates nodes (adds x/y/vx/vy). Links survive only if both endpoints do.
  const data = useMemo(() => {
    const nodes = selectedGraphId
      ? graph.nodes.filter(n => n.graphId === selectedGraphId)
      : graph.nodes;
    const ids = new Set(nodes.map(n => n.id));
    const links = graph.links.filter(
      l => ids.has(l.source as string) && ids.has(l.target as string),
    );
    return {
      nodes: nodes.map(n => ({ ...n })),
      links: links.map(l => ({ ...l })),
    };
  }, [graph, selectedGraphId]);

  const adjacency = useMemo(() => {
    const m = new Map<string, Set<string>>();
    for (const n of data.nodes) m.set(n.id, new Set());
    for (const l of data.links) {
      m.get(l.source as string)!.add(l.target as string);
      m.get(l.target as string)!.add(l.source as string);
    }
    return m;
  }, [data]);

  const degree = useMemo(() => {
    const d = new Map<string, number>();
    for (const [k, v] of adjacency) d.set(k, v.size);
    return d;
  }, [adjacency]);

  const isLit = useCallback((id: string) => {
    if (!hovered) return true;
    if (id === hovered) return true;
    return adjacency.get(hovered)?.has(id) ?? false;
  }, [hovered, adjacency]);

  return (
    <div className="absolute inset-0">
      <ForceGraph2D
        ref={fgRef as any}
        graphData={data}
        width={size.w}
        height={size.h}
        backgroundColor="#0a0a0a"
        cooldownTicks={200}
        d3AlphaDecay={0.02}
        d3VelocityDecay={0.3}
        linkColor={(l: any) => {
          const s = typeof l.source === 'object' ? l.source.id : l.source;
          const t = typeof l.target === 'object' ? l.target.id : l.target;
          const lit = !hovered || s === hovered || t === hovered;
          return lit ? 'rgba(180,180,180,0.55)' : 'rgba(180,180,180,0.08)';
        }}
        linkWidth={1}
        onNodeHover={(n: any) => setHovered(n ? n.id : null)}
        onNodeClick={(n: any) => selectNode(n.id)}
        onNodeDrag={(n: any) => { n.fx = n.x; n.fy = n.y; }}
        onNodeDragEnd={(n: any) => { n.fx = undefined; n.fy = undefined; }}
        nodeCanvasObject={(node: any, ctx, globalScale) => {
          const id = node.id as string;
          const deg = degree.get(id) ?? 1;
          const r = 4 + Math.sqrt(deg) * 3;
          const lit = isLit(id);
          ctx.globalAlpha = lit ? 1 : 0.2;
          ctx.beginPath();
          ctx.arc(node.x, node.y, r, 0, 2 * Math.PI);
          ctx.fillStyle = KIND_COLOR[node.kind as NodeKind];
          ctx.fill();
          if (id === hovered || id === selectedNodeId) {
            ctx.lineWidth = 2 / globalScale;
            ctx.strokeStyle = '#ffffff';
            ctx.stroke();
          }
          if (globalScale > 0.9 || deg >= 3 || id === hovered) {
            const fontSize = 12 / globalScale;
            ctx.font = `${fontSize}px ui-sans-serif, system-ui`;
            ctx.fillStyle = lit ? '#e5e7eb' : 'rgba(229,231,235,0.25)';
            ctx.textAlign = 'center';
            ctx.textBaseline = 'top';
            ctx.fillText(node.label, node.x, node.y + r + 2);
          }
          ctx.globalAlpha = 1;
        }}
      />
      <div className="absolute top-4 left-4 text-sm text-neutral-400 pointer-events-none">
        <div className="font-semibold text-neutral-200">Learning.AI</div>
        <div>hover: highlight neighborhood · click a node to open its conversation</div>
      </div>
      {graphs.length > 1 && (
        <div className="absolute top-4 left-1/2 -translate-x-1/2 z-10">
          <select
            value={selectedGraphId ?? ''}
            onChange={(e) => setSelectedGraphId(e.target.value || null)}
            className="max-w-xs truncate rounded-lg border border-neutral-700 bg-neutral-900/80 backdrop-blur px-3 py-1.5 text-sm text-neutral-200 hover:border-neutral-500 focus:outline-none"
          >
            <option value="">All graphs</option>
            {graphs.map(g => (
              <option key={g.id} value={g.id}>{g.goal}</option>
            ))}
          </select>
        </div>
      )}
      <footer className="absolute bottom-0 inset-x-0 px-6 py-4 border-t border-neutral-800 bg-neutral-950/90 backdrop-blur">
        <form onSubmit={handleSubmit} className="max-w-2xl mx-auto">
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Ask a question…"
            className="w-full rounded-lg bg-neutral-900 border border-neutral-800 px-4 py-3 text-sm text-neutral-100 placeholder-neutral-600 focus:outline-none"
          />
        </form>
      </footer>
    </div>
  );
}
