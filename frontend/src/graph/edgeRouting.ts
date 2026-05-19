import { NODE_H, NODE_W, type Position } from './layout';

export type HandleSide = 't-out' | 'b-out' | 'l-out' | 'r-out' | 't-in' | 'b-in' | 'l-in' | 'r-in';

// Pick which handle on the source card and which on the target card the edge
// should attach to. The choice is by geometry of the centers: if the target
// is mostly below/above we use top/bottom handles; if mostly left/right we
// use side handles. Uses card aspect ratio to bias the threshold so wide
// cards still prefer horizontal exits for near-horizontal links.
export function pickHandles(
  src: Position,
  tgt: Position,
): { sourceHandle: HandleSide; targetHandle: HandleSide } {
  const cx1 = src.x + NODE_W / 2;
  const cy1 = src.y + NODE_H / 2;
  const cx2 = tgt.x + NODE_W / 2;
  const cy2 = tgt.y + NODE_H / 2;
  const dx = cx2 - cx1;
  const dy = cy2 - cy1;

  // Normalize by node dimensions so the comparison is in "card units."
  const ndx = dx / NODE_W;
  const ndy = dy / NODE_H;

  if (Math.abs(ndy) >= Math.abs(ndx)) {
    return dy >= 0
      ? { sourceHandle: 'b-out', targetHandle: 't-in' }
      : { sourceHandle: 't-out', targetHandle: 'b-in' };
  }
  return dx >= 0
    ? { sourceHandle: 'r-out', targetHandle: 'l-in' }
    : { sourceHandle: 'l-out', targetHandle: 'r-in' };
}
