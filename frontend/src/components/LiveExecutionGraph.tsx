import { useMemo, useRef, useEffect } from 'react';
import { Box, Text, useColorModeValue } from '@chakra-ui/react';
import type { ExecutionTrace, AgentNode } from './ExecutionGraph';

interface LiveExecutionGraphProps {
  trace: ExecutionTrace;
  isStreaming?: boolean;
  onNodeClick?: (node: AgentNode) => void;
  height?: number;
}

const TYPE_COLOR: Record<string, string> = {
  query: '#63B3ED',
  context: '#A0AEC0',
  agent: '#48BB78',
  tool: '#ED8936',
  response: '#9F7AEA',
};

const X_GAP = 150;
const Y_GAP = 58;
const PAD_X = 28;
const PAD_Y = 36;
const NODE_R: Record<string, number> = {
  agent: 14,
  tool: 9,
  query: 12,
  response: 12,
  context: 10,
};

/**
 * Lightweight SVG DAG — no ECharts roam/wheel handling, so page scroll works.
 */
const LiveExecutionGraph = ({
  trace,
  isStreaming = false,
  onNodeClick,
  height = 220,
}: LiveExecutionGraphProps) => {
  const wrapRef = useRef<HTMLDivElement>(null);
  const labelColor = useColorModeValue('#2D3748', '#E2E8F0');
  const edgeColor = useColorModeValue('#A0AEC0', '#718096');
  const muted = useColorModeValue('gray.500', 'gray.400');

  // Mac trackpad pinch = wheel + ctrlKey → browser page zoom. Block that over the graph.
  useEffect(() => {
    const el = wrapRef.current;
    if (!el) return;
    const onWheel = (e: WheelEvent) => {
      if (e.ctrlKey || e.metaKey) {
        e.preventDefault();
      }
    };
    el.addEventListener('wheel', onWheel, { passive: false });
    return () => el.removeEventListener('wheel', onWheel);
  }, []);

  const nodeById = useMemo(() => {
    const map = new Map<string, AgentNode>();
    for (const n of trace.nodes || []) {
      if (n?.id && !map.has(n.id)) map.set(n.id, n);
    }
    return map;
  }, [trace.nodes]);

  const edges = useMemo(() => {
    const ids = new Set(nodeById.keys());
    const seen = new Set<string>();
    return (trace.edges || []).filter((e) => {
      if (!ids.has(e.source) || !ids.has(e.target)) return false;
      const key = `${e.source}->${e.target}`;
      if (seen.has(key)) return false;
      seen.add(key);
      return true;
    });
  }, [trace.edges, nodeById]);

  const layout = useMemo(() => {
    const nodes = Array.from(nodeById.values());
    if (nodes.length === 0) return null;

    const children = new Map<string, string[]>();
    const indegree = new Map<string, number>();
    for (const n of nodes) indegree.set(n.id, 0);
    for (const e of edges) {
      const list = children.get(e.source) || [];
      list.push(e.target);
      children.set(e.source, list);
      indegree.set(e.target, (indegree.get(e.target) || 0) + 1);
    }

    const roots = nodes.filter((n) => (indegree.get(n.id) || 0) === 0);
    const depth = new Map<string, number>();
    const queue = roots.map((r) => r.id);
    for (const r of roots) depth.set(r.id, 0);
    while (queue.length) {
      const id = queue.shift()!;
      const d = depth.get(id) || 0;
      for (const child of children.get(id) || []) {
        const next = d + 1;
        if (!depth.has(child) || next > (depth.get(child) || 0)) {
          depth.set(child, next);
          queue.push(child);
        }
      }
    }
    for (const n of nodes) {
      if (!depth.has(n.id)) depth.set(n.id, 0);
    }

    const byDepth = new Map<number, AgentNode[]>();
    for (const n of nodes) {
      const d = depth.get(n.id) || 0;
      const list = byDepth.get(d) || [];
      list.push(n);
      byDepth.set(d, list);
    }

    const maxDepth = Math.max(...Array.from(depth.values()), 0);
    const rank = (t: string) =>
      ({ query: 0, context: 1, agent: 2, tool: 3, response: 4 }[t] ?? 5);

    const positions = new Map<string, { x: number; y: number }>();
    let maxLayerSize = 1;
    for (let d = 0; d <= maxDepth; d++) {
      const layer = byDepth.get(d) || [];
      layer.sort((a, b) => rank(a.type) - rank(b.type) || a.name.localeCompare(b.name));
      maxLayerSize = Math.max(maxLayerSize, layer.length);
      layer.forEach((n, i) => {
        positions.set(n.id, {
          x: PAD_X + d * X_GAP,
          y: PAD_Y + i * Y_GAP,
        });
      });
    }

    const newestId = nodes[nodes.length - 1]?.id;
    const contentW = PAD_X * 2 + maxDepth * X_GAP;
    const contentH = PAD_Y * 2 + (maxLayerSize - 1) * Y_GAP;

    return { nodes, positions, newestId, contentW, contentH };
  }, [nodeById, edges]);

  if (!layout) {
    return (
      <Text fontSize="xs" color={muted} px={3} py={4} textAlign="center">
        {isStreaming ? 'Waiting for the first agent step…' : 'No execution graph yet'}
      </Text>
    );
  }

  const { nodes, positions, newestId, contentW, contentH } = layout;
  const viewH = Math.max(height, Math.min(contentH + 8, 360));

  return (
    <Box
      ref={wrapRef}
      h={`${viewH}px`}
      w="100%"
      overflowX="auto"
      overflowY="hidden"
      // pan only — blocks browser pinch-zoom over this region
      sx={{ touchAction: 'pan-x pan-y' }}
    >
      <svg
        width="100%"
        height={viewH}
        viewBox={`0 0 ${Math.max(contentW, 1)} ${Math.max(contentH, 1)}`}
        preserveAspectRatio="xMidYMid meet"
        style={{ display: 'block', minWidth: Math.min(contentW, 640) }}
      >
        <defs>
          <marker
            id="live-graph-arrow"
            viewBox="0 0 10 10"
            refX="9"
            refY="5"
            markerWidth="6"
            markerHeight="6"
            orient="auto-start-reverse"
          >
            <path d="M 0 0 L 10 5 L 0 10 z" fill={edgeColor} />
          </marker>
        </defs>

        {edges.map((e) => {
          const from = positions.get(e.source);
          const to = positions.get(e.target);
          if (!from || !to) return null;
          const dx = to.x - from.x;
          const midX = from.x + dx * 0.5;
          return (
            <path
              key={`${e.source}->${e.target}`}
              d={`M ${from.x} ${from.y} C ${midX} ${from.y}, ${midX} ${to.y}, ${to.x} ${to.y}`}
              fill="none"
              stroke={edgeColor}
              strokeWidth={1.5}
              opacity={0.85}
              markerEnd="url(#live-graph-arrow)"
            />
          );
        })}

        {nodes.map((n) => {
          const pos = positions.get(n.id);
          if (!pos) return null;
          const r = NODE_R[n.type] ?? 10;
          const isNew = n.id === newestId && isStreaming;
          const label =
            n.name.length > 18 ? `${n.name.slice(0, 16)}…` : n.name;
          return (
            <g
              key={n.id}
              transform={`translate(${pos.x}, ${pos.y})`}
              style={{ cursor: onNodeClick ? 'pointer' : 'default' }}
              onClick={() => onNodeClick?.(n)}
            >
              {isNew && (
                <circle
                  r={r + 5}
                  fill="none"
                  stroke="#F6E05E"
                  strokeWidth={2}
                  opacity={0.9}
                >
                  <animate
                    attributeName="opacity"
                    values="0.9;0.35;0.9"
                    dur="1.2s"
                    repeatCount="indefinite"
                  />
                </circle>
              )}
              <circle
                r={r}
                fill={TYPE_COLOR[n.type] || '#718096'}
                stroke={isNew ? '#F6E05E' : 'transparent'}
                strokeWidth={isNew ? 2 : 0}
              />
              <text
                y={r + 14}
                textAnchor="middle"
                fill={labelColor}
                fontSize={n.type === 'tool' ? 10 : 11}
                fontWeight={n.type === 'agent' ? 600 : 400}
                style={{ userSelect: 'none', pointerEvents: 'none' }}
              >
                {label}
              </text>
            </g>
          );
        })}
      </svg>
    </Box>
  );
};

export default LiveExecutionGraph;
