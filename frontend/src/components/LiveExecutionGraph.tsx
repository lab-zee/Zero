import { useMemo, useRef, useEffect } from 'react';
import ReactECharts from 'echarts-for-react';
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

/**
 * Compact left-to-right DAG of the execution trace.
 * Deterministic layered layout (no force simulation) so it stays readable
 * while nodes/edges appear during streaming.
 */
const LiveExecutionGraph = ({
  trace,
  isStreaming = false,
  onNodeClick,
  height = 220,
}: LiveExecutionGraphProps) => {
  const chartRef = useRef<ReactECharts>(null);
  const labelColor = useColorModeValue('#2D3748', '#E2E8F0');
  const edgeColor = useColorModeValue('#A0AEC0', '#718096');
  const bgHint = useColorModeValue('white', 'transparent');

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

  const option = useMemo(() => {
    const nodes = Array.from(nodeById.values());
    if (nodes.length === 0) return null;

    // Build adjacency for BFS depth
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
    const queue = [...roots.map((r) => r.id)];
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

    const xGap = 160;
    const yGap = 56;
    const positions = new Map<string, { x: number; y: number }>();
    const maxDepth = Math.max(...Array.from(depth.values()), 0);

    for (let d = 0; d <= maxDepth; d++) {
      const layer = byDepth.get(d) || [];
      // Prefer: query/context/agent/tool/response ordering within a layer
      const rank = (t: string) =>
        ({ query: 0, context: 1, agent: 2, tool: 3, response: 4 }[t] ?? 5);
      layer.sort((a, b) => rank(a.type) - rank(b.type) || a.name.localeCompare(b.name));
      layer.forEach((n, i) => {
        positions.set(n.id, {
          x: d * xGap,
          y: (i - (layer.length - 1) / 2) * yGap,
        });
      });
    }

    const newestId = nodes[nodes.length - 1]?.id;

    const graphNodes = nodes.map((n) => {
      const pos = positions.get(n.id) || { x: 0, y: 0 };
      const isNew = n.id === newestId && isStreaming;
      const size =
        n.type === 'agent' ? 34 : n.type === 'tool' ? 22 : n.type === 'query' || n.type === 'response' ? 28 : 24;
      return {
        id: n.id,
        name: n.name,
        value: n.id,
        x: pos.x,
        y: pos.y,
        symbolSize: isNew ? size + 4 : size,
        itemStyle: {
          color: TYPE_COLOR[n.type] || '#718096',
          borderColor: isNew ? '#F6E05E' : 'transparent',
          borderWidth: isNew ? 2 : 0,
          shadowBlur: isNew ? 12 : 0,
          shadowColor: isNew ? 'rgba(246, 224, 94, 0.55)' : undefined,
        },
        label: {
          show: true,
          formatter: () => (n.name.length > 18 ? `${n.name.slice(0, 16)}…` : n.name),
          color: labelColor,
          fontSize: n.type === 'tool' ? 10 : 11,
          fontWeight: n.type === 'agent' ? 600 : 400,
          position: 'bottom',
          distance: 6,
        },
      };
    });

    const links = edges.map((e) => ({
      source: e.source,
      target: e.target,
      lineStyle: {
        color: edgeColor,
        width: 1.5,
        curveness: 0.15,
        opacity: 0.85,
      },
    }));

    return {
      backgroundColor: bgHint,
      animation: true,
      animationDuration: 280,
      animationDurationUpdate: 350,
      animationEasingUpdate: 'cubicOut',
      tooltip: {
        trigger: 'item',
        formatter: (params: any) => {
          if (params.dataType === 'edge') return '';
          const node = nodeById.get(params.data?.id);
          if (!node) return params.name;
          return `<b>${node.name}</b><br/><span style="opacity:.7">${node.type}</span>`;
        },
      },
      series: [
        {
          type: 'graph',
          layout: 'none',
          // No roam: wheel/trackpad zoom traps page scroll on this inline panel
          roam: false,
          draggable: false,
          zoom: 0.85,
          data: graphNodes,
          links,
          edgeSymbol: ['none', 'arrow'],
          edgeSymbolSize: [0, 8],
          emphasis: {
            focus: 'adjacency',
            lineStyle: { width: 3 },
          },
        },
      ],
    };
  }, [nodeById, edges, isStreaming, labelColor, edgeColor, bgHint]);

  // ECharts can still swallow wheel events even with roam:false — let the page scroll instead
  useEffect(() => {
    const chart = chartRef.current?.getEchartsInstance?.();
    if (!chart) return;
    const dom = chart.getDom();
    if (!dom) return;

    const onWheel = (e: WheelEvent) => {
      e.stopImmediatePropagation();
    };
    dom.addEventListener('wheel', onWheel, { capture: true, passive: true });
    return () => {
      dom.removeEventListener('wheel', onWheel, true);
    };
  }, [option, trace.nodes?.length]);

  // Fit view when the graph grows
  useEffect(() => {
    const chart = chartRef.current?.getEchartsInstance?.();
    if (!chart || !option) return;
    const t = window.setTimeout(() => {
      try {
        chart.resize();
      } catch {
        /* ignore */
      }
    }, 50);
    return () => window.clearTimeout(t);
  }, [option, trace.nodes?.length, trace.edges?.length]);

  if (!option) {
    return (
      <Text fontSize="xs" color="gray.500" px={3} py={4} textAlign="center">
        {isStreaming ? 'Waiting for the first agent step…' : 'No execution graph yet'}
      </Text>
    );
  }

  return (
    <Box h={`${height}px`} w="100%" overflow="hidden">
      <ReactECharts
        ref={chartRef as any}
        option={option}
        style={{ height: '100%', width: '100%' }}
        notMerge
        lazyUpdate
        opts={{ renderer: 'canvas' }}
        onEvents={
          onNodeClick
            ? {
                click: (params: any) => {
                  if (params?.dataType === 'node' || params?.data?.id) {
                    const node = nodeById.get(params.data.id);
                    if (node) onNodeClick(node);
                  }
                },
              }
            : undefined
        }
      />
    </Box>
  );
};

export default LiveExecutionGraph;
