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

  const fgRef = useRef<ForceGraphMethods>();
  const [hovered, setHovered] = useState<string | null>(null);
  const [size, setSize] = useState({ w: window.innerWidth, h: window.innerHeight });

  useEffect(() => {
    const onResize = () => setSize({ w: window.innerWidth, h: window.innerHeight });
    window.addEventListener('resize', onResize);
    return () => window.removeEventListener('resize', onResize);
  }, []);

  // Clone the graph data once for ForceGraph2D — it mutates nodes (adds x/y/vx/vy).
  const data = useMemo(() => ({
    nodes: graph.nodes.map(n => ({ ...n })),
    links: graph.links.map(l => ({ ...l })),
  }), [graph]);

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
    </div>
  );
}
