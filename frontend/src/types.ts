export type NodeKind = 'trunk' | 'side' | 'prereq';

export interface Turn {
  user: string;
  assistant: string;
}

export interface GNode {
  id: string;
  label: string;
  kind: NodeKind;
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

export type ViewMode = 'graph' | 'chat';
