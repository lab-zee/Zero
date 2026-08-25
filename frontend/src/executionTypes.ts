export interface AgentNode {
  id: string;
  type: string;
  name: string;
  metadata?: Record<string, unknown>;
}

export interface AgentEdge {
  source: string;
  target: string;
  label?: string;
}

export interface ExecutionTrace {
  nodes: AgentNode[];
  edges: AgentEdge[];
}
