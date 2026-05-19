import {
  forceCollide,
  forceLink,
  forceManyBody,
  forceSimulation,
  forceX,
  forceY,
  type SimulationLinkDatum,
  type SimulationNodeDatum,
} from 'd3-force';
import type { Graph } from '../types';

export interface Position {
  x: number;
  y: number;
}

export const NODE_W = 176;
export const NODE_H = 72;
export const PAD = 32;
export const TRUNK_X = 0;
export const TRUNK_ROW = 180;

interface SimNode extends SimulationNodeDatum {
  id: string;
  isTrunk: boolean;
  firstParentId: string | null;
  side: number;
}

// Cheap deterministic hash → [-1, 1) so jitter is stable across re-runs.
function hash01(s: string): number {
  let h = 2166136261;
  for (let i = 0; i < s.length; i++) {
    h ^= s.charCodeAt(i);
    h = Math.imul(h, 16777619);
  }
  return ((h >>> 0) / 0xffffffff) * 2 - 1;
}

// Hybrid pinned-trunk + force-directed layout with hard non-overlap guarantee.
// - Trunk nodes are pinned on a vertical spine at x=TRUNK_X.
// - Non-trunk nodes drift around their first parent via d3-force.
// - Warm-starts from prev positions so existing nodes barely move when one is added.
// - A deterministic sweep-and-prune post-pass guarantees no two nodes overlap.
export function recompute(graph: Graph, prev: Map<string, Position>): Map<string, Position> {
  const trunk = graph.nodes
    .filter((n) => n.isTrunk)
    .sort((a, b) => a.createdAt - b.createdAt);
  const trunkY = new Map<string, number>();
  trunk.forEach((n, i) => trunkY.set(n.id, i * TRUNK_ROW));

  // Count existing non-trunk descendants per (parent, side) to balance new spawns.
  const sideCount = new Map<string, { left: number; right: number }>();
  for (const n of graph.nodes) {
    if (n.isTrunk) continue;
    const pid = n.parentIds[0];
    if (!pid) continue;
    const p = prev.get(n.id);
    if (!p) continue;
    const bucket = sideCount.get(pid) ?? { left: 0, right: 0 };
    if (p.x < TRUNK_X) bucket.left++;
    else bucket.right++;
    sideCount.set(pid, bucket);
  }

  const simNodes: SimNode[] = graph.nodes.map((n) => {
    const firstParentId = n.parentIds[0] ?? null;
    const isTrunk = n.isTrunk;

    if (isTrunk) {
      const y = trunkY.get(n.id)!;
      const sn: SimNode = {
        id: n.id,
        isTrunk: true,
        firstParentId,
        side: 0,
        x: TRUNK_X,
        y,
        fx: TRUNK_X,
        fy: y,
      };
      return sn;
    }

    const warm = prev.get(n.id);
    if (warm) {
      return {
        id: n.id,
        isTrunk: false,
        firstParentId,
        side: warm.x < TRUNK_X ? -1 : 1,
        x: warm.x,
        y: warm.y,
      };
    }

    // Cold start near parent on the lighter side.
    const parentPos = firstParentId
      ? prev.get(firstParentId) ??
        (trunkY.has(firstParentId) ? { x: TRUNK_X, y: trunkY.get(firstParentId)! } : null)
      : null;
    const bucket = firstParentId ? sideCount.get(firstParentId) ?? { left: 0, right: 0 } : { left: 0, right: 0 };
    const side = bucket.left <= bucket.right ? -1 : 1;
    if (firstParentId) {
      const b = sideCount.get(firstParentId) ?? { left: 0, right: 0 };
      if (side < 0) b.left++;
      else b.right++;
      sideCount.set(firstParentId, b);
    }

    const jitter = hash01(n.id) * 24;
    const baseX = parentPos ? parentPos.x : TRUNK_X;
    const baseY = parentPos ? parentPos.y : 0;
    return {
      id: n.id,
      isTrunk: false,
      firstParentId,
      side,
      x: baseX + side * (NODE_W + PAD) + jitter,
      y: baseY + (NODE_H + PAD) * 0.6 + hash01(n.id + '_y') * 16,
    };
  });

  const byId = new Map(simNodes.map((s) => [s.id, s]));

  const links: SimulationLinkDatum<SimNode>[] = graph.edges
    .filter((e) => byId.has(e.from) && byId.has(e.to))
    .map((e) => ({ source: e.from, target: e.to }));

  const collideR = Math.sqrt(NODE_W * NODE_W + NODE_H * NODE_H) / 2 + PAD / 2;

  const sim = forceSimulation<SimNode>(simNodes)
    .force(
      'link',
      forceLink<SimNode, SimulationLinkDatum<SimNode>>(links)
        .id((d) => d.id)
        .distance(NODE_W + PAD)
        .strength(0.5),
    )
    .force('charge', forceManyBody<SimNode>().strength(-350))
    .force('collide', forceCollide<SimNode>(collideR).strength(1).iterations(4))
    .force(
      'x',
      forceX<SimNode>((d) => {
        if (d.isTrunk) return TRUNK_X;
        const parent = d.firstParentId ? byId.get(d.firstParentId) : null;
        const base = parent?.x ?? TRUNK_X;
        return base + d.side * (NODE_W + PAD);
      }).strength((d) => (d.isTrunk ? 0 : 0.04)),
    )
    .force(
      'y',
      forceY<SimNode>((d) => {
        if (d.isTrunk) return d.fy as number;
        const parent = d.firstParentId ? byId.get(d.firstParentId) : null;
        return (parent?.y ?? 0) + NODE_H + PAD;
      }).strength((d) => (d.isTrunk ? 0 : 0.08)),
    )
    .stop();

  const hasCold = simNodes.some((s) => !s.isTrunk && !prev.has(s.id));
  const ticks = hasCold ? 300 : 80;
  for (let i = 0; i < ticks; i++) sim.tick();

  const positions = new Map<string, Position>();
  for (const s of simNodes) positions.set(s.id, { x: s.x ?? 0, y: s.y ?? 0 });

  resolveOverlaps(positions, byId);

  // Convert from center coordinates to top-left for React Flow.
  const out = new Map<string, Position>();
  for (const [id, p] of positions) {
    out.set(id, { x: p.x - NODE_W / 2, y: p.y - NODE_H / 2 });
  }
  return out;
}

// Sweep-and-prune AABB overlap resolver. Trunk nodes are frozen — any
// overlap involving a trunk node moves only the non-trunk side. Iterates
// to fixed-point (caps at 12 passes to bound the worst case).
function resolveOverlaps(positions: Map<string, Position>, byId: Map<string, SimNode>): void {
  const W = NODE_W + PAD;
  const H = NODE_H + PAD;
  const ids = [...positions.keys()];

  for (let pass = 0; pass < 12; pass++) {
    ids.sort((a, b) => positions.get(a)!.x - positions.get(b)!.x);
    let moved = false;

    for (let i = 0; i < ids.length; i++) {
      const ai = ids[i];
      const a = positions.get(ai)!;
      for (let j = i + 1; j < ids.length; j++) {
        const bj = ids[j];
        const b = positions.get(bj)!;
        if (b.x - a.x >= W) break;
        if (Math.abs(b.y - a.y) >= H) continue;

        const dx = b.x - a.x;
        const dy = b.y - a.y;
        const overlapX = W - Math.abs(dx);
        const overlapY = H - Math.abs(dy);
        if (overlapX <= 0 || overlapY <= 0) continue;

        const aTrunk = byId.get(ai)?.isTrunk;
        const bTrunk = byId.get(bj)?.isTrunk;
        if (aTrunk && bTrunk) continue; // shouldn't happen — fixed spine

        // Push along the axis of smallest overlap (cheaper escape).
        let pushX = 0;
        let pushY = 0;
        if (overlapX < overlapY) {
          pushX = (dx >= 0 ? 1 : -1) * (overlapX + 1);
        } else {
          pushY = (dy >= 0 ? 1 : -1) * (overlapY + 1);
        }

        if (aTrunk) {
          positions.set(bj, { x: b.x + pushX, y: b.y + pushY });
        } else if (bTrunk) {
          positions.set(ai, { x: a.x - pushX, y: a.y - pushY });
        } else {
          positions.set(ai, { x: a.x - pushX / 2, y: a.y - pushY / 2 });
          positions.set(bj, { x: b.x + pushX / 2, y: b.y + pushY / 2 });
        }
        moved = true;
      }
    }

    if (!moved) return;
  }
}
