import { useState, useRef, useCallback, useEffect } from 'react';
import { useSearchParams } from 'react-router-dom';
import { useQueryClient } from '@tanstack/react-query';
import { useToast } from '@chakra-ui/react';
import { chatAPI, ExecutionTrace, AgentNode, Citation, AnswerMode } from '../../../services/api';
import { ProgressUpdate } from '../../../components/ProgressTimeline';
import { FollowUpQuestion } from '../../../components/FollowUpSuggestions';

export interface FailedMessage {
  message: string;
  orgId: number;
  threadId: number;
  fileIds?: number[];
  mode: string;
  answerMode: AnswerMode;
  reaskOfQueryId?: number | null;
}

interface UseMessageStreamOptions {
  userId: number | undefined;
  selectedOrgId: number | null;
  selectedThreadId: number | null;
  onThreadCreated?: (threadId: number) => void;
  onClarificationNeeded?: (questions: string[], queryId: number) => void;
  onExecutionTraceUpdate?: (queryId: number, trace: ExecutionTrace) => void;
  onMessageSent?: () => void;
}

export function useMessageStream({
  userId,
  selectedOrgId,
  selectedThreadId,
  onThreadCreated,
  onClarificationNeeded,
  onExecutionTraceUpdate,
  onMessageSent,
}: UseMessageStreamOptions) {
  const queryClient = useQueryClient();
  const toast = useToast();
  const [searchParams, setSearchParams] = useSearchParams();

  // Streaming state
  const [isStreaming, setIsStreaming] = useState(false);
  const [streamingResponse, setStreamingResponse] = useState<string>('');
  const [streamingTrace, setStreamingTrace] = useState<ExecutionTrace | null>(null);
  const [streamingCitations, setStreamingCitations] = useState<Citation[] | null>(null);
  const [streamingRecommendations, setStreamingRecommendations] = useState<string[] | null>(null);
  const [streamingFollowupQuestions, setStreamingFollowupQuestions] = useState<FollowUpQuestion[] | null>(null);
  const [streamingContentStructure, setStreamingContentStructure] = useState<any>(null);
  const [streamingMessage, setStreamingMessage] = useState<string>('');
  const [streamingProgress, setStreamingProgress] = useState<ProgressUpdate[]>([]);

  // Error state
  const [connectionError, setConnectionError] = useState<string | null>(null);
  const [streamError, setStreamError] = useState<string | null>(null);
  const [lastFailedMessage, setLastFailedMessage] = useState<FailedMessage | null>(null);

  // Refs
  const accumulatedTraceRef = useRef<ExecutionTrace | null>(null);
  const streamCleanupRef = useRef<(() => void) | null>(null);
  const streamStartTimeRef = useRef<number | null>(null);

  // Cleanup function
  const cleanupStream = useCallback(() => {
    if (streamCleanupRef.current) {
      streamCleanupRef.current();
      streamCleanupRef.current = null;
    }
    setIsStreaming(false);
    setStreamingResponse('');
    setStreamingTrace(null);
    setStreamingCitations(null);
    setStreamingRecommendations(null);
    setStreamingFollowupQuestions(null);
    setStreamingContentStructure(null);
    setStreamingMessage('');
    setStreamingProgress([]);
    accumulatedTraceRef.current = null;
    streamStartTimeRef.current = null;
  }, []);

  // Cleanup on thread change or unmount
  useEffect(() => {
    return cleanupStream;
  }, [selectedThreadId, cleanupStream]);

  const sendMessage = useCallback((
    msg: string,
    orgId: number,
    threadId: number | undefined,
    fileIds: number[] | undefined,
    mode: string | undefined,
    answerMode: AnswerMode | undefined,
    reaskOfQueryId?: number | null,
    agentIds?: string[] | null,
    // Additional context for error handling
    currentMessage?: string,
    currentFileIds?: number[],
    currentMode?: string,
    currentAnswerMode?: AnswerMode,
    followupOfQueryId?: number | null
  ) => {
    if (!userId) return;

    // Clean up any existing stream before starting a new one
    if (streamCleanupRef.current) {
      streamCleanupRef.current();
      streamCleanupRef.current = null;
    }

    // Clear errors
    setConnectionError(null);
    setStreamError(null);
    setLastFailedMessage(null);

    // Reset streaming state
    setIsStreaming(true);
    setStreamingResponse('');
    setStreamingTrace(null);
    setStreamingCitations(null);
    setStreamingRecommendations(null);
    setStreamingFollowupQuestions(null);
    setStreamingContentStructure(null);
    setStreamingProgress([]);
    setStreamingMessage(msg);
    accumulatedTraceRef.current = null;
    streamStartTimeRef.current = Date.now();

    const cleanup = chatAPI.sendMessageStream(
      msg,
      orgId,
      userId,
      threadId,
      fileIds,
      mode,
      answerMode,
      reaskOfQueryId,
      agentIds,
      (event: { type: string; data: any }) => {
        if (event.type === 'trace_update' && event.data?.trace) {
          const newTrace = event.data.trace as ExecutionTrace;

          if (!newTrace || !newTrace.nodes || !Array.isArray(newTrace.nodes)) {
            return;
          }

          const safeTrace: ExecutionTrace = {
            nodes: newTrace.nodes || [],
            edges: newTrace.edges || []
          };

          const currentAccumulated = accumulatedTraceRef.current;
          if (currentAccumulated && currentAccumulated.nodes && Array.isArray(currentAccumulated.nodes) && currentAccumulated.nodes.length > 0) {
            // Merge nodes
            const nodeMap = new Map<string, AgentNode>();
            currentAccumulated.nodes.forEach(node => {
              if (node && node.id && node.name) {
                nodeMap.set(node.id, { ...node });
              }
            });
            safeTrace.nodes.forEach(node => {
              if (!node || !node.id || !node.name) return;
              if (nodeMap.has(node.id)) {
                const existing = nodeMap.get(node.id)!;
                nodeMap.set(node.id, {
                  ...existing,
                  metadata: { ...existing.metadata, ...node.metadata }
                });
              } else {
                nodeMap.set(node.id, { ...node });
              }
            });

            // Merge edges
            const edgeSet = new Set<string>();
            (currentAccumulated.edges || []).forEach(edge => {
              if (edge && edge.source && edge.target) {
                edgeSet.add(`${edge.source}->${edge.target}`);
              }
            });
            const mergedEdges = [...(currentAccumulated.edges || [])];
            (safeTrace.edges || []).forEach(edge => {
              if (!edge || !edge.source || !edge.target) return;
              const edgeKey = `${edge.source}->${edge.target}`;
              if (!edgeSet.has(edgeKey)) {
                mergedEdges.push(edge);
                edgeSet.add(edgeKey);
              }
            });

            const mergedTrace: ExecutionTrace = {
              nodes: Array.from(nodeMap.values()),
              edges: mergedEdges
            };

            accumulatedTraceRef.current = mergedTrace;
            setStreamingTrace(() => ({
              nodes: [...mergedTrace.nodes],
              edges: [...mergedTrace.edges]
            }));
          } else {
            accumulatedTraceRef.current = safeTrace;
            setStreamingTrace(() => ({
              nodes: [...safeTrace.nodes],
              edges: [...safeTrace.edges]
            }));
          }
        }

        if (event.type === 'thread_created') {
          const newThreadId = event.data.thread_id;
          if (newThreadId) {
            const params = new URLSearchParams(searchParams);
            params.set('thread', newThreadId.toString());
            setSearchParams(params, { replace: true });
            queryClient.invalidateQueries({ queryKey: ['threads', userId, selectedOrgId] });
            queryClient.invalidateQueries({ queryKey: ['organizationsWithStats', userId] });
            onThreadCreated?.(newThreadId);
          }
        }

        if (event.type === 'progress_update' && event.data) {
          setStreamingProgress((prev) => [...prev, {
            agent_name: event.data.agent_name,
            message: event.data.message,
            type: event.data.type,
            delegate_to: event.data.delegate_to,
            tool_name: event.data.tool_name,
          }]);
        }

        if (event.type === 'response' && event.data) {
          setStreamingResponse(event.data.response || '');
          if (event.data.execution_trace) {
            const finalTrace = event.data.execution_trace as ExecutionTrace;
            accumulatedTraceRef.current = finalTrace;
            setStreamingTrace(() => ({
              nodes: [...finalTrace.nodes],
              edges: [...finalTrace.edges]
            }));
            onExecutionTraceUpdate?.(event.data.query_id, finalTrace);
          }
          if (event.data.citations) {
            setStreamingCitations(event.data.citations as Citation[]);
          }
          if (event.data.recommendations) {
            setStreamingRecommendations(event.data.recommendations as string[]);
          }
          if (event.data.followup_questions) {
            setStreamingFollowupQuestions(event.data.followup_questions as FollowUpQuestion[]);
          }
          if (event.data.content_structure) {
            setStreamingContentStructure(event.data.content_structure);
          }
          if (event.data.is_clarification && event.data.clarification_questions) {
            onClarificationNeeded?.(event.data.clarification_questions, event.data.query_id);
          }
        }

        if (event.type === 'error') {
          setIsStreaming(false);
          const errorMessage = event.data?.message || 'An error occurred while processing your request';
          setStreamError(errorMessage);

          setStreamingResponse('');
          setStreamingTrace(null);
          setStreamingCitations(null);
          setStreamingRecommendations(null);
          setStreamingContentStructure(null);
          setStreamingProgress([]);

          toast({
            title: 'Error',
            description: errorMessage,
            status: 'error',
            duration: 5000,
            isClosable: true,
          });

          if (selectedOrgId && selectedThreadId) {
            setLastFailedMessage({
              message: currentMessage || msg,
              orgId: selectedOrgId,
              threadId: selectedThreadId,
              fileIds: currentFileIds,
              mode: currentMode || mode || 'agentic',
              answerMode: currentAnswerMode || answerMode || 'light',
              reaskOfQueryId: null,
            });
          }

          queryClient.invalidateQueries({ queryKey: ['thread-queries', selectedThreadId] });
          queryClient.invalidateQueries({ queryKey: ['threads', userId, selectedOrgId] });
        }

        if (event.type === 'done') {
          setIsStreaming(false);
          queryClient.invalidateQueries({ queryKey: ['thread-queries', selectedThreadId] });
          queryClient.invalidateQueries({ queryKey: ['threads', userId, selectedOrgId] });
          queryClient.invalidateQueries({ queryKey: ['organizationsWithStats', userId] });
          onMessageSent?.();

          setStreamingResponse('');
          setStreamingTrace(null);
          setStreamingCitations(null);
          setStreamingRecommendations(null);
          setStreamingContentStructure(null);
          setStreamingProgress([]);
          setStreamingMessage('');
          accumulatedTraceRef.current = null;
          streamStartTimeRef.current = null;
          streamCleanupRef.current = null;
        }
      },
      (error: Error) => {
        console.error('SSE connection error:', error);
        setIsStreaming(false);
        setConnectionError(error.message || 'Connection lost');

        setLastFailedMessage({
          message: msg,
          orgId,
          threadId: threadId!,
          fileIds,
          mode: mode!,
          answerMode: answerMode!,
          reaskOfQueryId,
        });

        streamCleanupRef.current = null;
        toast({
          title: 'Connection Error',
          description: 'Lost connection to server. You can retry your question.',
          status: 'error',
          duration: 5000,
          isClosable: true,
        });
      },
      () => {
        setIsStreaming(false);
        streamCleanupRef.current = null;
      },
      followupOfQueryId
    );

    streamCleanupRef.current = cleanup;
    return cleanup;
  }, [
    userId,
    selectedOrgId,
    selectedThreadId,
    searchParams,
    setSearchParams,
    queryClient,
    toast,
    onThreadCreated,
    onClarificationNeeded,
    onExecutionTraceUpdate,
    onMessageSent,
  ]);

  const retryLastMessage = useCallback(() => {
    if (lastFailedMessage) {
      sendMessage(
        lastFailedMessage.message,
        lastFailedMessage.orgId,
        lastFailedMessage.threadId,
        lastFailedMessage.fileIds,
        lastFailedMessage.mode,
        lastFailedMessage.answerMode,
        lastFailedMessage.reaskOfQueryId
      );
    }
  }, [lastFailedMessage, sendMessage]);

  const clearErrors = useCallback(() => {
    setConnectionError(null);
    setStreamError(null);
    setLastFailedMessage(null);
  }, []);

  return {
    // Streaming state
    isStreaming,
    streamingResponse,
    streamingTrace,
    streamingCitations,
    streamingRecommendations,
    streamingFollowupQuestions,
    streamingContentStructure,
    streamingMessage,
    streamingProgress,
    streamStartTime: streamStartTimeRef.current,
    // Error state
    connectionError,
    streamError,
    lastFailedMessage,
    // Actions
    sendMessage,
    retryLastMessage,
    clearErrors,
    cleanupStream,
  };
}
