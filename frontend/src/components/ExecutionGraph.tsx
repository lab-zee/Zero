import React, { useEffect, useRef, useMemo, useState } from 'react';
import ReactECharts from 'echarts-for-react';
import { Box, HStack, IconButton } from '@chakra-ui/react';
import { AddIcon, MinusIcon } from '@chakra-ui/icons';

export interface AgentNode {
  id: string;
  type: string; // "agent" | "tool" | "context" | "query" | "response"
  name: string;
  metadata?: Record<string, any>;
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

interface ExecutionGraphProps {
  trace: ExecutionTrace;
  onNodeClick?: (node: AgentNode) => void;
}

const DEFAULT_LEGEND_SELECTED: Record<string, boolean> = {
  'Query': true,
  'Context': true,
  'Agent': true,
  'Tool': false, // Hidden by default
  'Final Response': true,
};

const ExecutionGraph: React.FC<ExecutionGraphProps> = ({ trace, onNodeClick }) => {
  const chartRef = useRef<ReactECharts>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const isMountedRef = useRef(true);
  const previousTraceHashRef = useRef<string>('');
  const [zoomLevel, setZoomLevel] = useState(0.8); // Start slightly zoomed out to fit the graph
  const legendSelectedRef = useRef<Record<string, boolean>>({ ...DEFAULT_LEGEND_SELECTED });

  // Handle component lifecycle
  useEffect(() => {
    isMountedRef.current = true;
    return () => {
      isMountedRef.current = false;
      // Don't manually dispose - let echarts-for-react handle cleanup automatically
      // Manual disposal interferes with the library's internal ResizeObserver cleanup
    };
  }, []);

  // Color mapping based on node type
  const getNodeColor = (type: string): string => {
    switch (type) {
      case 'query':
        return '#63b3ed'; // blue
      case 'context':
        return '#a0aec0'; // gray
      case 'agent':
        return '#68d391'; // green
      case 'tool':
        return '#f6ad55'; // orange
      case 'response':
        return '#b794f4'; // purple
      default:
        return '#718096'; // gray
    }
  };

  if (!trace) {
    return (
      <Box p={4} textAlign="center" color="gray.400">
        No execution trace available
      </Box>
    );
  }
  
  if (!trace.nodes || !Array.isArray(trace.nodes) || trace.nodes.length === 0) {
    return (
      <Box p={4} textAlign="center" color="gray.400">
        No execution trace available
      </Box>
    );
  }


  // Deduplicate nodes by ID (keep first occurrence)
  // Also validate that nodes have required fields
  const nodeMap = new Map<string, AgentNode>();
  trace.nodes.forEach((node) => {
    if (!node.id || !node.name) {
      return;
    }
    if (!nodeMap.has(node.id)) {
      nodeMap.set(node.id, node);
    } else {
      // Merge metadata if node already exists
      const existing = nodeMap.get(node.id)!;
      if (node.metadata && existing.metadata) {
        existing.metadata = { ...existing.metadata, ...node.metadata };
      }
    }
  });
  const uniqueNodes = Array.from(nodeMap.values());
  
  if (uniqueNodes.length === 0) {
    return (
      <Box p={4} textAlign="center" color="gray.400">
        No valid nodes in execution trace
      </Box>
    );
  }

  // Define categories and create a mapping from type to index (must be before nodes mapping)
  // Categories array - defined once at the top level with colors matching node colors
  const graphCategories = [
    { name: 'Query', itemStyle: { color: '#63b3ed' } }, // blue
    { name: 'Context', itemStyle: { color: '#a0aec0' } }, // gray
    { name: 'Agent', itemStyle: { color: '#68d391' } }, // green
    { name: 'Tool', itemStyle: { color: '#f6ad55' } }, // orange
    { name: 'Final Response', itemStyle: { color: '#b794f4' } }, // purple
  ];
  
  const categoryMap: Record<string, number> = {
    'query': 0,
    'context': 1,
    'agent': 2,
    'tool': 3,
    'response': 4,
  };

  // Create set of valid node IDs for edge validation
  const validNodeIds = new Set(uniqueNodes.map((n) => n.id));

  // Filter edges to only include those with valid source and target nodes
  const validEdges = trace.edges.filter(
    (edge) => validNodeIds.has(edge.source) && validNodeIds.has(edge.target)
  );

  // Find query and response nodes to position them
  const queryNode = uniqueNodes.find(n => n.type.toLowerCase() === 'query');
  const responseNode = uniqueNodes.find(n => n.type.toLowerCase() === 'response');
  
  // Calculate node depths/layers for better horizontal positioning
  // This creates a clear left-to-right flow using BFS from query node
  const nodeDepths = new Map<string, number>();
  const visited = new Set<string>();
  
  // BFS to calculate depth from query node
  if (queryNode) {
    const queue: Array<{ id: string; depth: number }> = [{ id: queryNode.id, depth: 0 }];
    nodeDepths.set(queryNode.id, 0);
    visited.add(queryNode.id);
    
    while (queue.length > 0) {
      const current = queue.shift()!;
      const outgoingEdges = validEdges.filter(e => e.source === current.id);
      
      for (const edge of outgoingEdges) {
        if (!visited.has(edge.target)) {
          const newDepth = current.depth + 1;
          nodeDepths.set(edge.target, newDepth);
          visited.add(edge.target);
          queue.push({ id: edge.target, depth: newDepth });
        } else {
          // Update depth if we found a shorter path
          const existingDepth = nodeDepths.get(edge.target) || Infinity;
          if (current.depth + 1 < existingDepth) {
            nodeDepths.set(edge.target, current.depth + 1);
          }
        }
      }
    }
  }
  
  // Set response node to maximum depth + 1 to ensure it's on the right
  const maxDepth = Math.max(...Array.from(nodeDepths.values()), 0);
  if (responseNode) {
    nodeDepths.set(responseNode.id, maxDepth + 2);
  }
  
  // Prepare graph data with unique nodes
  // Ensure names are unique by appending ID if needed
  const nodeNameMap = new Map<string, number>();

  // Build a map of tool nodes to their parent agent node for clustered positioning
  const toolParentMap = new Map<string, string>(); // tool node id -> parent node id
  const parentToolChildren = new Map<string, string[]>(); // parent node id -> [tool node ids]
  for (const node of uniqueNodes) {
    if (node.type.toLowerCase() === 'tool') {
      // Find the edge pointing to this tool (parent -> tool)
      const parentEdge = validEdges.find(e => e.target === node.id);
      if (parentEdge) {
        toolParentMap.set(node.id, parentEdge.source);
        const children = parentToolChildren.get(parentEdge.source) || [];
        children.push(node.id);
        parentToolChildren.set(parentEdge.source, children);
      }
    }
  }

  // First pass: position non-tool nodes using BFS depth layout
  const nonToolNodes = uniqueNodes.filter(n => n.type.toLowerCase() !== 'tool');
  const layerWidth = 800;

  // Count non-tool nodes per depth layer for vertical spacing
  const nonToolByDepth = new Map<number, string[]>();
  for (const node of nonToolNodes) {
    const depth = nodeDepths.get(node.id) ?? 1;
    const list = nonToolByDepth.get(depth) || [];
    list.push(node.id);
    nonToolByDepth.set(depth, list);
  }

  // Store computed positions so tool nodes can reference their parent's position
  const nodePositions = new Map<string, { x: number; y: number }>();

  // Position non-tool nodes
  for (const node of nonToolNodes) {
    const depth = nodeDepths.get(node.id) ?? 1;
    if (node.id === queryNode?.id) {
      nodePositions.set(node.id, { x: 0, y: 0 });
    } else if (node.id === responseNode?.id) {
      nodePositions.set(node.id, { x: (maxDepth + 2) * layerWidth, y: 0 });
    } else {
      const nodesInLayer = nonToolByDepth.get(depth)?.length || 1;
      const layerIndex = nonToolByDepth.get(depth)?.indexOf(node.id) || 0;
      const verticalSpacing = Math.max(120, 400 / Math.max(nodesInLayer - 1, 1) * 3);
      nodePositions.set(node.id, {
        x: depth * layerWidth,
        y: (layerIndex - (nodesInLayer - 1) / 2) * verticalSpacing,
      });
    }
  }

  // Position tool nodes clustered near their parent
  for (const node of uniqueNodes) {
    if (node.type.toLowerCase() !== 'tool') continue;
    const parentId = toolParentMap.get(node.id);
    const parentPos = parentId ? nodePositions.get(parentId) : undefined;
    if (parentPos && parentId) {
      const siblings = parentToolChildren.get(parentId) || [node.id];
      const toolIndex = siblings.indexOf(node.id);
      const toolCount = siblings.length;
      // Offset tools to the right of their parent, fanned out vertically
      const toolSpacing = 60;
      nodePositions.set(node.id, {
        x: parentPos.x + layerWidth * 0.5, // Halfway between parent layer and next layer
        y: parentPos.y + (toolIndex - (toolCount - 1) / 2) * toolSpacing,
      });
    } else {
      // Fallback: use BFS depth position
      const depth = nodeDepths.get(node.id) ?? 2;
      nodePositions.set(node.id, { x: depth * layerWidth, y: 0 });
    }
  }

  const nodes = uniqueNodes.map((node) => {
    // Make name unique if there are duplicates
    let displayName = node.name;
    const nameCount = nodeNameMap.get(node.name) || 0;
    if (nameCount > 0) {
      displayName = `${node.name} (${node.id.slice(-4)})`;
    }
    nodeNameMap.set(node.name, nameCount + 1);

    // Map node type to category index (ECharts requires index, not name)
    const categoryIndex = categoryMap[node.type.toLowerCase()] ?? 2; // Default to agent
    const pos = nodePositions.get(node.id) || { x: 0, y: 0 };

    return {
      id: node.id,
      name: displayName,
      value: node.id, // Use ID as value to ensure uniqueness
      category: categoryIndex, // Must be index, not string
      symbolSize: node.type === 'agent' ? 35 : node.type === 'tool' ? 20 : 28,
      itemStyle: {
        color: getNodeColor(node.type),
      },
      label: {
        show: true,
        fontSize: node.type === 'tool' ? 10 : 12,
        fontWeight: node.type === 'agent' ? 'bold' : 'normal',
      },
      x: pos.x,
      y: pos.y,
    };
  });

  // Deduplicate edges as well
  const edgeSet = new Set<string>();
  const links = validEdges
    .filter((edge) => {
      const edgeKey = `${edge.source}->${edge.target}`;
      if (edgeSet.has(edgeKey)) {
        return false;
      }
      edgeSet.add(edgeKey);
      return true;
    })
    .map((edge) => ({
      source: edge.source,
      target: edge.target,
      label: {
        show: false, // Hide edge labels by default to reduce clutter
        // Show on hover via tooltip instead
        formatter: edge.label || '',
        fontSize: 9,
        position: 'middle',
      },
      lineStyle: {
        color: '#4a5568',
        width: 2,
        curveness: 0.2,
      },
    }));

  // Track trace changes for reference
  const traceHash = useMemo(() => {
    // Only hash the essential parts to avoid unnecessary re-renders
    return JSON.stringify({ nodes: trace.nodes?.map(n => n.id), edges: trace.edges?.map(e => `${e.source}-${e.target}`) });
  }, [trace.nodes, trace.edges]);
  
  // Update previous hash ref and ensure chart updates when trace changes
  useEffect(() => {
    const prevHash = previousTraceHashRef.current;
    previousTraceHashRef.current = traceHash;
    
    // Only update if trace actually changed
    if (prevHash === traceHash) {
      return;
    }
    
    // Ensure chart resizes when trace changes (option updates automatically via prop)
    if (chartRef.current && isMountedRef.current) {
      try {
        const chartInstance = (chartRef.current as any).getEchartsInstance?.();
        if (chartInstance && typeof chartInstance.resize === 'function') {
          // The option prop will update automatically, we just need to resize
          setTimeout(() => {
            if (chartInstance && isMountedRef.current) {
              try {
                chartInstance.resize();
              } catch (error) {
                // Ignore resize errors
              }
            }
          }, 100);
        }
      } catch (error) {
        // Ignore chart update errors
      }
    }
  }, [traceHash]);

  const option = useMemo(() => {
    return {
    tooltip: {
      trigger: 'item',
      formatter: (params: any) => {
        if (params.dataType === 'node') {
          const node = uniqueNodes.find((n) => n.id === params.data.id || n.id === params.data.value);
          const nodeName = params.data.name || node?.name || 'Unknown';
          return `
            <div style="padding: 8px;">
              <strong>${nodeName}</strong><br/>
              Type: ${params.data.category !== undefined ? graphCategories[params.data.category]?.name : node?.type || 'unknown'}<br/>
              ${node?.metadata ? `Details: ${JSON.stringify(node.metadata, null, 2).substring(0, 100)}` : ''}
            </div>
          `;
        } else {
          // Show edge label in tooltip since we're hiding them by default
          const edge = validEdges.find(e => e.source === params.data.source && e.target === params.data.target);
          return `${params.data.source} → ${params.data.target}${edge?.label ? ` (${edge.label})` : ''}`;
        }
      },
    },
    legend: {
      data: graphCategories.map((c) => ({
        name: c.name,
        itemStyle: c.itemStyle,
      })),
      orient: 'vertical',
      left: 'left',
      top: 'middle',
      textStyle: {
        color: '#e2e8f0',
      },
      // Enable toggling categories
      selectedMode: 'multiple', // Allow toggling multiple categories
      // Use persisted legend selection so toggling survives trace updates
      selected: { ...legendSelectedRef.current },
      tooltip: {
        show: true,
        formatter: (params: any) => {
          if (params.name === 'Tool') {
            return 'Click to toggle tool node visibility';
          }
          return `Click to toggle ${params.name} nodes`;
        },
      },
    },
    series: [
      {
        type: 'graph',
        layout: 'none', // Use our custom BFS-based positions directly
        data: nodes,
        links: links,
        categories: graphCategories,
        roam: true, // Allow both zoom and pan
        draggable: true,
        zoom: zoomLevel,
        id: 'execution-flow',
        label: {
          show: true,
          position: 'right',
          formatter: (params: any) => {
            const name = params.data.name || '';
            return name.length > 20 ? name.substring(0, 20) + '...' : name;
          },
          distance: 10,
          fontSize: 11,
          width: 160,
          overflow: 'truncate',
          color: '#e2e8f0',
          backgroundColor: 'rgba(26, 32, 44, 0.85)',
          borderRadius: 3,
          padding: [2, 4],
          textBorderColor: 'transparent',
          textBorderWidth: 0,
          textShadowColor: 'transparent',
          textShadowBlur: 0,
        },
        lineStyle: {
          color: '#a0aec0',
          width: 1.5,
          curveness: 0.3,
          opacity: 0.8,
        },
        emphasis: {
          focus: 'adjacency',
          lineStyle: {
            width: 4,
          },
        },
        animation: false,
      },
    ],
  };
  }, [nodes, links, zoomLevel]); // Simplified dependencies to reduce unnecessary re-renders

  const handleZoomIn = () => {
    if (chartRef.current) {
      const chartInstance = (chartRef.current as any).getEchartsInstance?.();
      if (chartInstance) {
        const newZoom = Math.min(zoomLevel * 1.2, 5); // Max zoom 5x
        setZoomLevel(newZoom);
        // For graph type, we need to use a different approach
        // Try using the chart's internal zoom if available
        try {
          const option = chartInstance.getOption();
          if (option && option.series && option.series[0]) {
            // Update the series zoom through option update
            chartInstance.setOption({
              series: [{
                ...option.series[0],
                zoom: newZoom
              }]
            }, false);
          }
        } catch (e) {
          // If direct zoom doesn't work, we'll rely on the roam setting
          console.log('Zoom update attempted');
        }
      }
    }
  };

  const handleZoomOut = () => {
    if (chartRef.current) {
      const chartInstance = (chartRef.current as any).getEchartsInstance?.();
      if (chartInstance) {
        const newZoom = Math.max(zoomLevel / 1.2, 0.2); // Min zoom 0.2x
        setZoomLevel(newZoom);
        try {
          const option = chartInstance.getOption();
          if (option && option.series && option.series[0]) {
            chartInstance.setOption({
              series: [{
                ...option.series[0],
                zoom: newZoom
              }]
            }, false);
          }
        } catch (e) {
          console.log('Zoom update attempted');
        }
      }
    }
  };

  const handleResetZoom = () => {
    setZoomLevel(1);
    if (chartRef.current) {
      const chartInstance = (chartRef.current as any).getEchartsInstance?.();
      if (chartInstance) {
        try {
          const option = chartInstance.getOption();
          if (option && option.series && option.series[0]) {
            chartInstance.setOption({
              series: [{
                ...option.series[0],
                zoom: 1
              }]
            }, false);
          }
          // Reset pan position
          chartInstance.dispatchAction({
            type: 'restore'
          });
        } catch (e) {
          console.log('Reset zoom attempted');
        }
      }
    }
  };

  return (
      <Box
      ref={containerRef}
      w="100%"
      h="100%"
      minH="200px"
      borderWidth={1}
      borderRadius="md"
      p={2}
      position="relative"
      bg="surface.800"
      overflow="hidden"
      display="flex"
      flexDirection="column"
    >
      {/* Zoom Controls */}
      <HStack
        position="absolute"
        top={2}
        right={2}
        zIndex={10}
        bg="surface.800"
        borderRadius="md"
        p={1}
        boxShadow="md"
        spacing={1}
      >
        <IconButton
          aria-label="Zoom in"
          icon={<AddIcon />}
          size="sm"
          onClick={handleZoomIn}
          variant="ghost"
        />
        <IconButton
          aria-label="Zoom out"
          icon={<MinusIcon />}
          size="sm"
          onClick={handleZoomOut}
          variant="ghost"
        />
        <IconButton
          aria-label="Reset zoom"
          size="sm"
          onClick={handleResetZoom}
          variant="ghost"
          fontSize="xs"
        >
          1:1
        </IconButton>
      </HStack>
      <ReactECharts
        ref={chartRef}
        option={option}
        style={{ height: '100%', width: '100%', display: 'block', flex: 1 }}
        opts={{
          renderer: 'canvas',
          locale: 'EN'
        }}
        notMerge={false}
        lazyUpdate={false}
        onEvents={{
          click: (params: any) => {
            if (params.dataType === 'node' && onNodeClick) {
              const node = uniqueNodes.find((n) => n.id === params.data.id || n.id === params.data.value);
              if (node) {
                onNodeClick(node);
              }
            }
          },
          legendselectchanged: (params: any) => {
            // Persist legend selection so it survives trace data updates
            legendSelectedRef.current = { ...params.selected };
          },
        }}
        onChartReady={(chart) => {
          // Chart is ready - ensure it's properly sized
          if (chart && isMountedRef.current) {
            try {
              // Force initial render and resize
              setTimeout(() => {
                if (chart && isMountedRef.current && typeof chart.resize === 'function') {
                  try {
                    chart.resize();
                  } catch (error) {
                    // Ignore resize errors if chart is disposed
                  }
                }
              }, 100);
            } catch (error) {
              // Ignore chart initialization errors
            }
          }
        }}
      />
    </Box>
  );
};

// Don't memoize - we need updates to flow through for real-time streaming
export default ExecutionGraph;
