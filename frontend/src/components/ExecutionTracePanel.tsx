import {
  Box,
  HStack,
  Text,
  IconButton,
  Badge,
  Collapse,
  VStack,
  useColorModeValue,
  Button,
} from '@chakra-ui/react';
import { FiChevronDown, FiChevronUp, FiActivity, FiGitBranch } from 'react-icons/fi';
import { useEffect, useState } from 'react';
import ProgressTimeline, { ProgressUpdate } from './ProgressTimeline';
import LLMPromptsViewer, { LLMPromptRecord } from './LLMPromptsViewer';
import LiveExecutionGraph from './LiveExecutionGraph';
import type { AgentNode, ExecutionTrace } from '../executionTypes';

interface ExecutionTracePanelProps {
  trace: ExecutionTrace;
  progressUpdates?: ProgressUpdate[];
  llmPrompts?: LLMPromptRecord[];
  isStreaming?: boolean;
  onNodeClick?: (node: AgentNode) => void;
}

/**
 * Agent run inspector: live DAG graph (selling visual) + optional timeline / steps / prompts.
 */
const ExecutionTracePanel = ({
  trace,
  progressUpdates = [],
  llmPrompts = [],
  isStreaming = false,
  onNodeClick,
}: ExecutionTracePanelProps) => {
  const hasGraph = (trace.nodes?.length || 0) > 0;
  // Expand by default when streaming or when a graph already exists (demo-friendly).
  const [expanded, setExpanded] = useState(isStreaming || hasGraph);
  const [showTimeline, setShowTimeline] = useState(false);
  const [showSteps, setShowSteps] = useState(false);
  const [showPrompts, setShowPrompts] = useState(false);
  const border = useColorModeValue('gray.200', 'whiteAlpha.150');
  const bg = useColorModeValue('gray.50', 'surface.800');
  const muted = useColorModeValue('gray.500', 'gray.400');

  // Keep expanded while streaming so the live DAG stays in view as it grows
  useEffect(() => {
    if (isStreaming || hasGraph) setExpanded(true);
  }, [isStreaming, hasGraph]);

  const agents = trace.nodes.filter((n) => n.type === 'agent');
  const tools = trace.nodes.filter((n) => n.type === 'tool');

  return (
    <Box borderWidth="1px" borderColor={border} borderRadius="md" bg={bg} mb={3} overflow="hidden">
      <HStack px={3} py={2} justify="space-between">
        <HStack spacing={2}>
          <Box as={FiActivity} color="brand.400" />
          <Text fontSize="sm" fontWeight="600">
            Agent run
          </Text>
          {isStreaming && (
            <Badge colorScheme="green" variant="subtle" fontSize="2xs">
              live
            </Badge>
          )}
          <Text fontSize="xs" color={muted}>
            {agents.length} agents · {tools.length} tools
          </Text>
        </HStack>
        <HStack>
          {progressUpdates.length > 0 && (
            <Button size="xs" variant="ghost" onClick={() => setShowTimeline(!showTimeline)}>
              {showTimeline ? 'Hide timeline' : 'Timeline'}
            </Button>
          )}
          {llmPrompts.length > 0 && (
            <Button size="xs" variant="ghost" onClick={() => setShowPrompts(!showPrompts)}>
              {showPrompts ? 'Hide prompts' : 'LLM prompts'}
            </Button>
          )}
          <Button size="xs" variant="ghost" onClick={() => setShowSteps(!showSteps)}>
            {showSteps ? 'Hide steps' : 'Raw steps'}
          </Button>
          <IconButton
            aria-label={expanded ? 'Collapse' : 'Expand'}
            icon={expanded ? <FiChevronUp /> : <FiChevronDown />}
            size="xs"
            variant="ghost"
            onClick={() => setExpanded(!expanded)}
          />
        </HStack>
      </HStack>

      <Collapse in={expanded}>
        {hasGraph && (
          <Box px={1} pb={1} borderBottomWidth={showTimeline || showSteps || showPrompts ? '1px' : 0} borderColor={border}>
            <LiveExecutionGraph
              trace={trace}
              isStreaming={isStreaming}
              onNodeClick={onNodeClick}
              height={isStreaming ? 260 : 220}
            />
          </Box>
        )}

        <Collapse in={showTimeline}>
          {progressUpdates.length > 0 && (
            <Box px={2} pb={2} pt={2}>
              <ProgressTimeline updates={progressUpdates} isStreaming={isStreaming} />
            </Box>
          )}
        </Collapse>

        <Collapse in={showPrompts}>
          <Box px={2} pb={2} maxH="320px" overflowY="auto">
            {llmPrompts.length > 0 ? (
              <LLMPromptsViewer prompts={llmPrompts} />
            ) : (
              <Text fontSize="xs" color={muted} px={2} pb={2}>
                Prompt data available after the run completes.
              </Text>
            )}
          </Box>
        </Collapse>

        <Collapse in={showSteps}>
          <VStack align="stretch" spacing={0} px={3} pb={3} maxH="240px" overflowY="auto">
            {trace.nodes.map((node) => (
              <HStack
                key={node.id}
                py={1.5}
                spacing={2}
                cursor={onNodeClick ? 'pointer' : 'default'}
                _hover={onNodeClick ? { bg: 'whiteAlpha.100' } : undefined}
                onClick={() => onNodeClick?.(node)}
              >
                <Box as={FiGitBranch} boxSize="12px" color={muted} />
                <Badge variant="subtle" fontSize="2xs" textTransform="capitalize">
                  {node.type}
                </Badge>
                <Text fontSize="xs" noOfLines={1}>
                  {node.name}
                </Text>
              </HStack>
            ))}
          </VStack>
        </Collapse>
      </Collapse>
    </Box>
  );
};

export default ExecutionTracePanel;
