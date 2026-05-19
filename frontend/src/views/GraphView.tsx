import { useMemo } from 'react';
import ReactFlow, {
  Background,
  Controls,
  Handle,
  Position as HandlePosition,
  type Edge as RFEdge,
  type Node as RFNode,
  type NodeProps,
} from 'reactflow';
import { motion } from 'framer-motion';
import { useStore } from '../store';
import { getAllAncestors } from '../graph/ancestors';
import { NODE_H, NODE_W } from '../graph/layout';
import { pickHandles } from '../graph/edgeRouting';
import type { EdgeType, GraphNode } from '../types';

const EDGE_STYLE: Record<EdgeType, { stroke: string; strokeWidth: number; strokeDasharray?: string }> = {
  subtopic: { stroke: '#f59e0b', strokeWidth: 3 },
  'side-question': { stroke: '#60a5fa', strokeWidth: 1.5, strokeDasharray: '6 4' },
  prerequisite: { stroke: '#a78bfa', strokeWidth: 2 },
  'see-also': { stroke: '#34d399', strokeWidth: 1.5, strokeDasharray: '2 3' },
};

interface NodeData {
  node: GraphNode;
  dim: boolean;
}

function CardNode({ data }: NodeProps<NodeData>) {
  const { node, dim } = data;
  return (
    <motion.div
      layoutId={node.id}
      className={`relative rounded-lg border px-3 py-2 text-xs ${
        node.isTrunk ? 'border-trunk bg-neutral-900' : 'border-neutral-700 bg-neutral-900'
      }`}
      style={{ width: NODE_W, height: NODE_H }}
      animate={{ opacity: dim ? 0.3 : 1 }}
      transition={{ duration: 0.2 }}
    >
      <Handle id="t-in" type="target" position={HandlePosition.Top} style={{ opacity: 0 }} />
      <Handle id="l-in" type="target" position={HandlePosition.Left} style={{ opacity: 0 }} />
      <Handle id="r-in" type="target" position={HandlePosition.Right} style={{ opacity: 0 }} />
      <Handle id="b-in" type="target" position={HandlePosition.Bottom} style={{ opacity: 0 }} />
      <div className={`font-medium truncate ${node.isTrunk ? 'text-trunk' : 'text-neutral-100'}`}>
        {node.prompt}
      </div>
      <div className="text-neutral-500 truncate mt-0.5">{node.summary}</div>
      <Handle id="t-out" type="source" position={HandlePosition.Top} style={{ opacity: 0 }} />
      <Handle id="l-out" type="source" position={HandlePosition.Left} style={{ opacity: 0 }} />
      <Handle id="r-out" type="source" position={HandlePosition.Right} style={{ opacity: 0 }} />
      <Handle id="b-out" type="source" position={HandlePosition.Bottom} style={{ opacity: 0 }} />
    </motion.div>
  );
}

const nodeTypes = { card: CardNode };

export function GraphView() {
  const graph = useStore((s) => s.graph);
  const positions = useStore((s) => s.positions);
  const highlightedNodeId = useStore((s) => s.highlightedNodeId);
  const highlightNode = useStore((s) => s.highlightNode);
  const focusNode = useStore((s) => s.focusNode);
  const setMode = useStore((s) => s.setMode);

  const ancestorSet = useMemo(
    () => (highlightedNodeId ? getAllAncestors(graph, highlightedNodeId) : null),
    [graph, highlightedNodeId]
  );

  const rfNodes: RFNode<NodeData>[] = graph.nodes.map((n) => {
    const pos = positions.get(n.id) ?? { x: 0, y: 0 };
    const dim = ancestorSet ? !ancestorSet.has(n.id) : false;
    return {
      id: n.id,
      type: 'card',
      position: pos,
      data: { node: n, dim },
      draggable: false,
      width: NODE_W,
      height: NODE_H,
    };
  });

  const rfEdges: RFEdge[] = graph.edges.map((e) => {
    const src = positions.get(e.from) ?? { x: 0, y: 0 };
    const tgt = positions.get(e.to) ?? { x: 0, y: 0 };
    const { sourceHandle, targetHandle } = pickHandles(src, tgt);
    return {
      id: `${e.from}->${e.to}`,
      source: e.from,
      target: e.to,
      sourceHandle,
      targetHandle,
      style: EDGE_STYLE[e.type],
      type: 'smoothstep',
    };
  });

  return (
    <div className="absolute inset-0 pt-14 pb-24">
      <ReactFlow
        nodes={rfNodes}
        edges={rfEdges}
        nodeTypes={nodeTypes}
        onNodeClick={(_, n) => highlightNode(n.id)}
        onNodeDoubleClick={(_, n) => {
          focusNode(n.id);
          setMode('chat');
        }}
        onPaneClick={() => highlightNode(null)}
        fitView
        proOptions={{ hideAttribution: true }}
      >
        <Background color="#262626" gap={24} />
        <Controls showInteractive={false} />
      </ReactFlow>
    </div>
  );
}
