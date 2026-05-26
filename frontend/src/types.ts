export type NodeKind = 'trunk' | 'side' | 'prereq';

export interface Turn {
  user: string;
  assistant: string;
}

export interface GNode {
  id: string;
  label: string;
  kind: NodeKind;
  graphId: string;
  turn: Turn;
}

export interface GLink {
  source: string;
  target: string;
}

export interface Graph {
  nodes: GNode[];
  links: GLink[];
}

export interface GraphSummary {
  id: string;
  goal: string;
}

export type ViewMode = 'graph' | 'chat';
