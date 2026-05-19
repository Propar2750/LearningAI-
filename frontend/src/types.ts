export type EdgeType = 'subtopic' | 'prerequisite' | 'see-also' | 'side-question';

export interface GraphNode {
  id: string;
  prompt: string;
  reply: string;
  summary: string;
  parentIds: string[];
  createdAt: number;
  isTrunk: boolean;
}

export interface GraphEdge {
  from: string;
  to: string;
  type: EdgeType;
}

export interface Goal {
  text: string;
}

export interface Graph {
  goal: Goal;
  nodes: GraphNode[];
  edges: GraphEdge[];
}

export type ViewMode = 'chat' | 'graph';
