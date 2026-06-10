import { useState, useEffect, useRef } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import {
  Box,
  Button,
  VStack,
  HStack,
  Heading,
  Text,
  useToast,
  Spinner,
  Center,
  Divider,
  IconButton,
  useDisclosure,
  AlertDialog,
  AlertDialogBody,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogContent,
  AlertDialogOverlay,
  useColorModeValue,
  Accordion,
  AccordionItem,
  AccordionButton,
  AccordionPanel,
  AccordionIcon,
  Tooltip,
  Badge,
  Skeleton,
  SkeletonText,
  Tabs,
  TabList,
  TabPanels,
  Tab,
  TabPanel,
} from '@chakra-ui/react';
import { AttachmentIcon, CloseIcon, CopyIcon, DownloadIcon } from '@chakra-ui/icons';
import { useAuth } from '../contexts/AuthContext';
import { chatAPI, organizationAPI, fileAPI, agentAPI, FileInfo, ExecutionTrace, AgentNode, Citation, AnswerMode } from '../services/api';

// Get API URL for constructing full URLs (e.g., for images)
const API_URL = (import.meta.env.VITE_API_URL || 'http://localhost:3001').replace(/\/+$/, '');
import ExecutionGraph from '../components/ExecutionGraph';
import ReactECharts from 'echarts-for-react';
import ExportModal from '../components/ExportModal';
import PreferencesModal from '../components/PreferencesModal';
import ThreadHeader from '../components/ThreadHeader';
import MessageInput from '../components/MessageInput';
import ClarificationModal from '../components/ClarificationModal';
import ProgressTimeline, { ProgressUpdate } from '../components/ProgressTimeline';
import LLMPromptsViewer from '../components/LLMPromptsViewer';
import FollowUpSuggestions, { FollowUpQuestion } from '../components/FollowUpSuggestions';
import TabbedMessageContent from '../components/TabbedMessageContent';
import ReAskButton from '../components/ReAskButton';
import AnswerModeSelector from '../components/AnswerModeSelector';
import { exportAsMarkdown, exportAsJSON, exportAsText, downloadAsFile } from '../features/chat/utils/exportHelpers';

const Chat = () => {
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();
  const { user } = useAuth();
  const queryClient = useQueryClient();
  const toast = useToast();
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const cancelRef = useRef<HTMLButtonElement>(null);

  // Initialize from URL params
  const orgIdFromUrl = searchParams.get('org');
  const threadIdFromUrl = searchParams.get('thread');

  // Get selected org and thread from URL params (managed by Sidebar)
  const selectedOrgId = orgIdFromUrl ? parseInt(orgIdFromUrl) : null;
  const selectedThreadId = threadIdFromUrl ? parseInt(threadIdFromUrl) : null;

  // Restore selection from sessionStorage when navigating back with no URL params
  useEffect(() => {
    if (!orgIdFromUrl && !threadIdFromUrl) {
      const storedOrgId = sessionStorage.getItem('lastChatOrgId');
      const storedThreadId = sessionStorage.getItem('lastChatThreadId');
      if (storedOrgId) {
        const params = new URLSearchParams();
        params.set('org', storedOrgId);
        if (storedThreadId) {
          params.set('thread', storedThreadId);
        }
        setSearchParams(params, { replace: true });
      }
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []); // Only on mount

  // Persist selection to sessionStorage so it survives navigation
  useEffect(() => {
    if (selectedOrgId) {
      sessionStorage.setItem('lastChatOrgId', selectedOrgId.toString());
      if (selectedThreadId) {
        sessionStorage.setItem('lastChatThreadId', selectedThreadId.toString());
      } else {
        sessionStorage.removeItem('lastChatThreadId');
      }
    }
  }, [selectedOrgId, selectedThreadId]);
  
  const bgColor = useColorModeValue('white', 'surface.800');
  const borderColor = useColorModeValue('gray.200', 'whiteAlpha.100');
  const chatBg = useColorModeValue('gray.50', 'surface.950');
  const userMsgBg = useColorModeValue('blue.50', 'blue.900');
  const assistantMsgBg = useColorModeValue('gray.50', 'surface.800');
  const [message, setMessage] = useState('');
  const [selectedFileIds, setSelectedFileIds] = useState<number[]>([]);
  const [uploadedFiles, setUploadedFiles] = useState<FileInfo[]>([]);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [chatMode] = useState<string>('agentic'); // Always use agentic mode
  const [executionTraces, setExecutionTraces] = useState<Record<number, ExecutionTrace>>({});
  const [fullscreenTraceId, setFullscreenTraceId] = useState<number | null>(null);
  const [selectedNode, setSelectedNode] = useState<AgentNode | null>(null);
  const { isOpen: isNodeModalOpen, onOpen: onNodeModalOpen, onClose: onNodeModalClose } = useDisclosure();
  const { isOpen: isPreferencesOpen, onOpen: onPreferencesOpen, onClose: onPreferencesClose } = useDisclosure();
  const { isOpen: isExportOpen, onOpen: onExportOpen, onClose: onExportClose } = useDisclosure();
  const { isOpen: isClarificationOpen, onOpen: onClarificationOpen, onClose: onClarificationClose } = useDisclosure();
  const [budgetFocus, setBudgetFocus] = useState<number>(0.5);
  const [responseLength, setResponseLength] = useState<number>(0.5);
  const [creativity, setCreativity] = useState<number>(0.5);
  const [answerMode, setAnswerMode] = useState<AnswerMode>('light'); // Default to balanced mode
  const [exportIncludeTraces, setExportIncludeTraces] = useState<boolean>(false);
  const [clarificationQuestions, setClarificationQuestions] = useState<string[]>([]);
  const [clarificationQueryId, setClarificationQueryId] = useState<number | null>(null);
  const [followupOfQueryId, setFollowupOfQueryId] = useState<number | null>(null);
  const [connectionError, setConnectionError] = useState<string | null>(null);
  const [streamError, setStreamError] = useState<string | null>(null);
  const [lastFailedMessage, setLastFailedMessage] = useState<{
    message: string;
    orgId: number;
    threadId: number;
    fileIds?: number[];
    mode: string;
    answerMode: AnswerMode;
    reaskOfQueryId?: number | null;
  } | null>(null);

  // Fetch user's organizations
  const { data: organizations } = useQuery({
    queryKey: ['organizations', user?.id],
    queryFn: () => organizationAPI.getMyOrganizations(user!.id),
    enabled: !!user,
  });

  // Fetch threads for selected organization
  const { data: threads } = useQuery({
    queryKey: ['threads', user?.id, selectedOrgId],
    queryFn: () => chatAPI.getThreads(user!.id, selectedOrgId!),
    enabled: !!user && !!selectedOrgId,
  });

  // Get current thread data
  const currentThread = threads?.find(t => t.id === selectedThreadId);

  // Fetch available agents for agent selection
  const { data: availableAgents } = useQuery({
    queryKey: ['agents', user?.id],
    queryFn: () => agentAPI.getAgents(user!.id),
    enabled: !!user,
    staleTime: 5 * 60 * 1000,
  });

  // Update preferences when thread changes
  useEffect(() => {
    if (currentThread?.thread_metadata) {
      setBudgetFocus(currentThread.thread_metadata.budget_focus ?? 0.5);
      setResponseLength(currentThread.thread_metadata.response_length ?? 0.5);
      setCreativity(currentThread.thread_metadata.creativity ?? 0.5);
    } else {
      setBudgetFocus(0.5);
      setResponseLength(0.5);
      setCreativity(0.5);
    }
  }, [currentThread]);

  // Mutation to update thread preferences
  const updateThreadMutation = useMutation({
    mutationFn: (update: { title?: string; thread_metadata?: { budget_focus?: number; response_length?: number; creativity?: number }; selected_agent_ids?: string[] | null }) =>
      chatAPI.updateThread(selectedThreadId!, update, user!.id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['threads', user?.id, selectedOrgId] });
      // Don't close modal automatically - let user close it manually
      toast({
        title: 'Preferences updated',
        status: 'success',
        duration: 2000,
        isClosable: true,
      });
    },
    onError: (error: any) => {
      toast({
        title: 'Failed to update preferences',
        description: error.message || 'An error occurred',
        status: 'error',
        duration: 3000,
        isClosable: true,
      });
    },
  });

  // Fetch messages for selected thread
  const { data: messages, isLoading: messagesLoading, error: messagesError } = useQuery({
    queryKey: ['thread-queries', selectedThreadId, user?.id],
    queryFn: () => chatAPI.getThreadQueries(selectedThreadId!, user!.id),
    enabled: !!selectedThreadId && !!user,
    retry: false,
  });

  // Load execution traces when messages are fetched and extract execution_times
  useEffect(() => {
    if (messages) {
      const traces: Record<number, ExecutionTrace> = {};
      messages.forEach((msg) => {
        if (msg.execution_trace && msg.id) {
          traces[msg.id] = msg.execution_trace;
          // Extract execution_times from execution_trace metadata if not already set
          if (!msg.execution_times) {
            // Check both direct metadata and nested metadata
            const execTimes = (msg.execution_trace as any).metadata?.execution_times || 
                             (msg.execution_trace as any).execution_times;
            if (execTimes) {
              (msg as any).execution_times = execTimes;
            }
          }
        }
      });
      setExecutionTraces(traces);
    }
  }, [messages]);

  // Fetch uploaded files for selected organization
  const { data: files } = useQuery({
    queryKey: ['files', user?.id, selectedOrgId],
    queryFn: () => fileAPI.getFiles(user!.id, selectedOrgId!),
    enabled: !!user && !!selectedOrgId,
  });

  useEffect(() => {
    if (files) {
      setUploadedFiles(files);
    }
  }, [files]);

  const [isStreaming, setIsStreaming] = useState(false);
  const [streamingResponse, setStreamingResponse] = useState<string>('');
  const [streamingTrace, setStreamingTrace] = useState<ExecutionTrace | null>(null);
  const [streamingCitations, setStreamingCitations] = useState<Citation[] | null>(null);
  const [streamingRecommendations, setStreamingRecommendations] = useState<string[] | null>(null);
  const [streamingFollowupQuestions, setStreamingFollowupQuestions] = useState<FollowUpQuestion[] | null>(null);
  const [streamingContentStructure, setStreamingContentStructure] = useState<any>(null);
  const [streamingMessage, setStreamingMessage] = useState<string>(''); // Store user's message during streaming
  const [streamingProgress, setStreamingProgress] = useState<ProgressUpdate[]>([]);
  
  // Accumulate trace data progressively to prevent overwrites
  const accumulatedTraceRef = useRef<ExecutionTrace | null>(null);
  // Store cleanup function for active stream
  const streamCleanupRef = useRef<(() => void) | null>(null);
  // Track stream start time for unique keys
  const streamStartTimeRef = useRef<number | null>(null);


  const sendMessageStream = (
    msg: string,
    orgId: number,
    threadId: number | undefined,
    fileIds: number[] | undefined,
    mode: string | undefined,
    ansMode: AnswerMode | undefined,
    reaskOfQueryId?: number | null,
    agentIds?: string[] | null,
    followupOfQueryId?: number | null
  ) => {
    // Clean up any existing stream before starting a new one
    if (streamCleanupRef.current) {
      streamCleanupRef.current();
      streamCleanupRef.current = null;
    }

    // Clear any previous connection errors and stream errors
    setConnectionError(null);
    setStreamError(null);
    setLastFailedMessage(null);

    // Reset ALL streaming state synchronously before starting a new stream
    // IMPORTANT: Set isStreaming FIRST to ensure the container can render
    setIsStreaming(true);
    setStreamingResponse('');
    setStreamingTrace(null);
    setStreamingCitations(null);
    setStreamingRecommendations(null);
    setStreamingFollowupQuestions(null);
    setStreamingContentStructure(null);
    setStreamingProgress([]); // Reset progress timeline
    setStreamingMessage(msg); // Store the user's message
    accumulatedTraceRef.current = null; // Reset accumulated trace
    streamStartTimeRef.current = Date.now(); // Set new stream start time for unique key

    const cleanup = chatAPI.sendMessageStream(
      msg,
      orgId,
      user!.id,
      threadId,
      fileIds,
      mode,
      ansMode,
      reaskOfQueryId,
      agentIds,
      (event) => {
        if (event.type === 'trace_update' && event.data?.trace) {
          const newTrace = event.data.trace as ExecutionTrace;
          
          // Ensure trace has nodes and edges arrays
          if (!newTrace || !newTrace.nodes || !Array.isArray(newTrace.nodes)) {
            return;
          }
          
          const safeTrace: ExecutionTrace = {
            nodes: newTrace.nodes || [],
            edges: newTrace.edges || []
          };
          
          // Always update the trace immediately for real-time display
          // Accumulate trace data progressively instead of replacing
          const currentAccumulated = accumulatedTraceRef.current;
          if (currentAccumulated && currentAccumulated.nodes && Array.isArray(currentAccumulated.nodes) && currentAccumulated.nodes.length > 0) {
            // Merge new nodes and edges into accumulated trace
            const nodeMap = new Map<string, AgentNode>();
            
            // Add existing nodes
            currentAccumulated.nodes.forEach(node => {
              if (node && node.id && node.name) {
                nodeMap.set(node.id, { ...node });
              }
            });
            
            // Add/update new nodes (merge metadata if node exists)
            safeTrace.nodes.forEach(node => {
              if (!node || !node.id || !node.name) return;
              if (nodeMap.has(node.id)) {
                // Merge metadata
                const existing = nodeMap.get(node.id)!;
                nodeMap.set(node.id, {
                  ...existing,
                  metadata: { ...existing.metadata, ...node.metadata }
                });
              } else {
                nodeMap.set(node.id, { ...node });
              }
            });
            
            // Merge edges (use Set to avoid duplicates)
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
            // Use functional update to ensure we're working with latest state
            setStreamingTrace(() => {
              // Always create new object reference to force re-render
              return {
                nodes: [...mergedTrace.nodes],
                edges: [...mergedTrace.edges]
              };
            });
          } else {
            // First trace update - use as-is
            accumulatedTraceRef.current = safeTrace;
            // Use functional update to ensure we're working with latest state
            setStreamingTrace(() => {
              // Always create new object reference to force re-render
              return {
                nodes: [...safeTrace.nodes],
                edges: [...safeTrace.edges]
              };
            });
          }
        }
        
        if (event.type === 'thread_created') {
          // Handle thread creation from streaming endpoint
          const newThreadId = event.data.thread_id;
          if (newThreadId) {
            // Update URL params to select the new thread
            const params = new URLSearchParams(searchParams);
            params.set('thread', newThreadId.toString());
            setSearchParams(params, { replace: true });
            // Invalidate threads query to show the new thread in sidebar
            queryClient.invalidateQueries({ queryKey: ['threads', user?.id, selectedOrgId] });
            queryClient.invalidateQueries({ queryKey: ['organizationsWithStats', user?.id] });
          }
        }

        if (event.type === 'progress_update' && event.data) {
          // Add progress update to the timeline
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
            // Use the final trace from response (should be complete)
            const finalTrace = event.data.execution_trace as ExecutionTrace;
            accumulatedTraceRef.current = finalTrace;
            // Use functional update to ensure we're working with latest state
            setStreamingTrace(() => {
              // Always create new object reference to force re-render
              return {
                nodes: [...finalTrace.nodes],
                edges: [...finalTrace.edges]
              };
            });
            setExecutionTraces((prev) => ({
              ...prev,
              [event.data.query_id]: finalTrace,
            }));
          }
          // Extract citations, recommendations, followup questions, and visualizations from response data
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
          if (event.data.execution_times) {
            // Store execution times for display (will be saved with query)
            // This will be available when the query is fetched from the database
          }
          // Check for clarification request
          if (event.data.is_clarification && event.data.clarification_questions) {
            setClarificationQuestions(event.data.clarification_questions);
            setClarificationQueryId(event.data.query_id);
            // Open clarification modal after a short delay to ensure streaming completes
            setTimeout(() => onClarificationOpen(), 500);
          }
        }
        
        if (event.type === 'error') {
          // Handle execution error from backend
          setIsStreaming(false);
          const errorMessage = event.data?.message || 'An error occurred while processing your request';
          setStreamError(errorMessage);

          // Clear streaming state
          setStreamingResponse('');
          setStreamingTrace(null);
          setStreamingCitations(null);
          setStreamingRecommendations(null);
          setStreamingContentStructure(null);
          setStreamingProgress([]);

          // Show toast notification
          toast({
            title: 'Error',
            description: errorMessage,
            status: 'error',
            duration: 5000,
            isClosable: true,
          });

          // Store failed message for retry (only if org and thread are selected)
          if (selectedOrgId && selectedThreadId) {
            setLastFailedMessage({
              message: message,
              orgId: selectedOrgId,
              threadId: selectedThreadId,
              fileIds: selectedFileIds,
              mode: chatMode,
              answerMode: answerMode,
              reaskOfQueryId: null,
            });
          }

          // Refresh queries in case a partial query was saved
          queryClient.invalidateQueries({ queryKey: ['thread-queries', selectedThreadId] });
          queryClient.invalidateQueries({ queryKey: ['threads', user?.id, selectedOrgId] });
        }

        if (event.type === 'done') {
          setIsStreaming(false);
          queryClient.invalidateQueries({ queryKey: ['thread-queries', selectedThreadId] });
          queryClient.invalidateQueries({ queryKey: ['threads', user?.id, selectedOrgId] });
          queryClient.invalidateQueries({ queryKey: ['organizationsWithStats', user?.id] });
          setMessage('');
          setSelectedFileIds([]);

          // Clear streaming state immediately (don't delay - it interferes with next message)
          setStreamingResponse('');
          setStreamingTrace(null);
                setStreamingCitations(null);
          setStreamingRecommendations(null);
          setStreamingContentStructure(null);
          setStreamingProgress([]);
          setStreamingMessage('');
          accumulatedTraceRef.current = null;
          streamStartTimeRef.current = null; // Clear stream start time
          streamCleanupRef.current = null; // Clear cleanup ref
        }
      },
      (error) => {
        // Handle SSE connection error
        console.error('SSE connection error:', error);
        setIsStreaming(false);
        setConnectionError(error.message || 'Connection lost');

        // Store failed message details for retry
        setLastFailedMessage({
          message: msg,
          orgId,
          threadId: threadId!,
          fileIds,
          mode: mode!,
          answerMode: ansMode!,
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
        streamCleanupRef.current = null; // Clear cleanup ref on completion
      },
      followupOfQueryId
    );

    // Store cleanup function
    streamCleanupRef.current = cleanup;

    return cleanup;
  };

  const createThreadMutation = useMutation({
    mutationFn: (title?: string) =>
      chatAPI.createThread({ organization_id: selectedOrgId!, title }, user!.id),
    onSuccess: (newThread) => {
      queryClient.invalidateQueries({ queryKey: ['threads', user?.id, selectedOrgId] });
      queryClient.invalidateQueries({ queryKey: ['organizationsWithStats', user?.id] });
      // Update URL params to select the new thread
      const params = new URLSearchParams(searchParams);
      params.set('thread', newThread.id.toString());
      setSearchParams(params, { replace: true });
    },
    onError: (error: any) => {
      toast({
        title: 'Error',
        description: error.response?.data?.detail || 'Failed to create thread',
        status: 'error',
        duration: 3000,
        isClosable: true,
      });
    },
  });


  // URL params are managed by Sidebar, no need to sync here

  useEffect(() => {
    if (!user) {
      navigate('/login');
      return;
    }
  }, [user, navigate]);

  // Cleanup stream when thread changes or component unmounts
  useEffect(() => {
    return () => {
      // Cleanup any active stream when thread changes or component unmounts
      if (streamCleanupRef.current) {
        streamCleanupRef.current();
        streamCleanupRef.current = null;
      }
      // Reset streaming state
      setIsStreaming(false);
      setStreamingResponse('');
      setStreamingTrace(null);
        setStreamingCitations(null);
      setStreamingRecommendations(null);
      setStreamingContentStructure(null);
      setStreamingMessage('');
      accumulatedTraceRef.current = null;
      streamStartTimeRef.current = null;
    };
  }, [selectedThreadId]);

  // Also cleanup on component unmount
  useEffect(() => {
    return () => {
      if (streamCleanupRef.current) {
        streamCleanupRef.current();
        streamCleanupRef.current = null;
      }
    };
  }, []);

  // Copy message to clipboard
  const copyToClipboard = (text: string, label: string = 'Message') => {
    navigator.clipboard.writeText(text).then(() => {
      toast({
        title: 'Copied!',
        description: `${label} copied to clipboard`,
        status: 'success',
        duration: 2000,
        isClosable: true,
      });
    }).catch(() => {
      toast({
        title: 'Error',
        description: 'Failed to copy to clipboard',
        status: 'error',
        duration: 2000,
        isClosable: true,
      });
    });
  };

  // Handle export using imported utilities
  const handleExport = (format: 'markdown' | 'json' | 'text') => {
    if (!messages || !currentThread) {
      toast({
        title: 'Error',
        description: 'No messages to export',
        status: 'error',
        duration: 2000,
        isClosable: true,
      });
      return;
    }

    const organizationName = organizations?.find(o => o.id === selectedOrgId)?.name || 'Unknown';
    let content: string;
    let filename: string;
    let mimeType: string;

    if (format === 'markdown') {
      content = exportAsMarkdown(messages, currentThread, organizationName, exportIncludeTraces);
      filename = `conversation-${currentThread.id}.md`;
      mimeType = 'text/markdown';
    } else if (format === 'json') {
      content = exportAsJSON(messages, currentThread, organizationName, exportIncludeTraces);
      filename = `conversation-${currentThread.id}.json`;
      mimeType = 'application/json';
    } else {
      content = exportAsText(messages, currentThread, organizationName, exportIncludeTraces);
      filename = `conversation-${currentThread.id}.txt`;
      mimeType = 'text/plain';
    }

    downloadAsFile(content, filename, mimeType);

    toast({
      title: 'Exported!',
      description: `Conversation exported as ${format.toUpperCase()}`,
      status: 'success',
      duration: 2000,
      isClosable: true,
    });

    onExportClose();
  };

  // Generate shareable link
  const generateShareableLink = () => {
    if (!selectedThreadId || !selectedOrgId) {
      toast({
        title: 'Error',
        description: 'No thread selected',
        status: 'error',
        duration: 2000,
        isClosable: true,
      });
      return;
    }
    
    const baseUrl = window.location.origin;
    const shareUrl = `${baseUrl}/chat?org=${selectedOrgId}&thread=${selectedThreadId}`;
    
    copyToClipboard(shareUrl, 'Shareable link');
  };

  const uploadFileMutation = useMutation({
    mutationFn: (file: File) => fileAPI.uploadFile(file, selectedOrgId!, user!.id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['files', user?.id, selectedOrgId] });
      toast({
        title: 'File uploaded',
        status: 'success',
        duration: 2000,
        isClosable: true,
      });
    },
    onError: (error: any) => {
      toast({
        title: 'Error',
        description: error.response?.data?.detail || 'Failed to upload file',
        status: 'error',
        duration: 3000,
        isClosable: true,
      });
    },
  });

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file || !selectedOrgId || !user) return;
    uploadFileMutation.mutate(file);
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };

  const handleFileSelect = (fileId: number) => {
    setSelectedFileIds((prev) =>
      prev.includes(fileId) ? prev.filter((id) => id !== fileId) : [...prev, fileId]
    );
  };

  const handleClarificationSubmit = (answers: string) => {
    if (!selectedOrgId || !selectedThreadId || !clarificationQueryId) {
      toast({
        title: 'Error',
        description: 'Missing required information for clarification',
        status: 'error',
        duration: 3000,
        isClosable: true,
      });
      return;
    }

    // Close the modal
    onClarificationClose();

    // Send the clarification answers with reask_of_query_id
    sendMessageStream(
      answers,
      selectedOrgId,
      selectedThreadId,
      undefined, // no file IDs for clarification responses
      chatMode,
      answerMode,
      clarificationQueryId // Pass the original query ID
    );

    // Clear clarification state
    setClarificationQuestions([]);
    setClarificationQueryId(null);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!message.trim() || !user || !selectedOrgId) return;

    const msgText = message;
    const fileIds = selectedFileIds.length > 0 ? selectedFileIds : undefined;
    const currentFollowupId = followupOfQueryId;

    // Clear the input field and follow-up mode immediately after capturing
    setMessage('');
    setFollowupOfQueryId(null);

    if (!selectedThreadId) {
      // Create a new thread automatically, then send message
      createThreadMutation.mutate(undefined, {
        onSuccess: (newThread) => {
          // Update URL params to select the new thread
          const params = new URLSearchParams(searchParams);
          params.set('thread', newThread.id.toString());
          setSearchParams(params, { replace: true });
          // Send message using streaming
          sendMessageStream(msgText, selectedOrgId, newThread.id, fileIds, chatMode, answerMode, undefined, undefined, currentFollowupId);
        },
      });
    } else {
      // Use streaming for real-time updates
      sendMessageStream(msgText, selectedOrgId, selectedThreadId, fileIds, chatMode, answerMode, undefined, undefined, currentFollowupId);
    }
  };

  const handleReAsk = (queryId: number, newMode: AnswerMode) => {
    if (!user || !selectedOrgId || !selectedThreadId || !messages) {
      toast({
        title: 'Error',
        description: 'Cannot re-ask question at this time',
        status: 'error',
        duration: 3000,
        isClosable: true,
      });
      return;
    }

    // Find the original message
    const originalQuery = messages.find(msg => msg.id === queryId);
    if (!originalQuery) {
      toast({
        title: 'Error',
        description: 'Original question not found',
        status: 'error',
        duration: 3000,
        isClosable: true,
      });
      return;
    }

    // Re-send the message with the new mode and reask reference
    sendMessageStream(
      originalQuery.message,
      selectedOrgId,
      selectedThreadId,
      undefined, // no files for re-ask
      chatMode,
      newMode,
      queryId // Pass the original query ID as reask_of_query_id
    );

    toast({
      title: 'Re-generating answer',
      description: `Creating ${newMode} version of your question`,
      status: 'info',
      duration: 2000,
      isClosable: true,
    });
  };


  if (!user) return null;

  return (
    <Box w="100%" h="100vh" display="flex" flexDirection="column" bg={chatBg}>
      {/* Thread Header - Sticky */}
      {selectedThreadId && currentThread && (
        <ThreadHeader
          thread={currentThread}
          messageCount={messages?.length || 0}
          onShareLink={generateShareableLink}
          onExport={onExportOpen}
          onPreferences={onPreferencesOpen}
        />
      )}

      {/* Chat Messages - Simplified */}
      <Box flex="1" display="flex" flexDirection="column" overflowY="auto" px={6} py={4}>
          
          {!selectedOrgId ? (
            <Center h="100%">
              <VStack spacing={4}>
                <Text fontSize="lg" color="gray.400">
                  Select an organization from the sidebar to start chatting
                </Text>
                {organizations && organizations.length === 0 && (
                  <Button colorScheme="brand" onClick={() => navigate('/organizations/new')}>
                    Create Your First Organization
                  </Button>
                )}
              </VStack>
            </Center>
          ) : !selectedThreadId ? (
            <Center h="100%">
              <VStack spacing={4}>
                <Text fontSize="lg" color="gray.400">
                  Select a thread from the sidebar or send a message to create one
                </Text>
              </VStack>
            </Center>
          ) : (
            <>
              {/* Messages Area */}
              <VStack spacing={4} align="stretch" flex="1" pb={4}>
                {messagesLoading ? (
                  <VStack spacing={4} align="stretch" px={4}>
                    {/* Skeleton for user message */}
                    <Box
                      bg={userMsgBg}
                      p={3}
                      borderRadius="md"
                      maxW="80%"
                      ml="auto"
                    >
                      <Skeleton height="20px" width="60px" mb={2} />
                      <SkeletonText noOfLines={2} spacing={2} />
                    </Box>
                    {/* Skeleton for assistant message */}
                    <Box
                      bg={bgColor}
                      p={4}
                      borderRadius="lg"
                      maxW="80%"
                      borderWidth={1}
                      borderColor={borderColor}
                    >
                      <Skeleton height="20px" width="100px" mb={3} />
                      <SkeletonText noOfLines={5} spacing={3} />
                      <Skeleton height="200px" mt={4} borderRadius="md" />
                    </Box>
                    {/* Skeleton for another user message */}
                    <Box
                      bg={userMsgBg}
                      p={3}
                      borderRadius="md"
                      maxW="80%"
                      ml="auto"
                    >
                      <Skeleton height="20px" width="60px" mb={2} />
                      <SkeletonText noOfLines={1} />
                    </Box>
                  </VStack>
                ) : (messages && messages.length > 0) || isStreaming ? (
                  <VStack spacing={4} align="stretch">
                    {messages && messages.map((msg) => {
                      const timestamp = msg.created_at ? new Date(msg.created_at) : null;
                      const formatTime = (date: Date) => {
                        return date.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' });
                      };
                      const formatDate = (date: Date) => {
                        const today = new Date();
                        const yesterday = new Date(today);
                        yesterday.setDate(yesterday.getDate() - 1);
                        
                        if (date.toDateString() === today.toDateString()) {
                          return 'Today';
                        } else if (date.toDateString() === yesterday.toDateString()) {
                          return 'Yesterday';
                        } else {
                          return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: date.getFullYear() !== today.getFullYear() ? 'numeric' : undefined });
                        }
                      };
                      
                      return (
                      <VStack key={msg.id} spacing={2} align="stretch">
                        {/* User Message */}
                        <Box
                          bg={userMsgBg}
                          p={3}
                          borderRadius="md"
                          maxW="80%"
                          ml="auto"
                        >
                          <HStack justify="space-between" mb={1}>
                            <Text fontWeight="semibold" fontSize="sm">
                              You
                            </Text>
                            <HStack spacing={2}>
                              {timestamp && (
                                <Text fontSize="xs" color="gray.400">
                                  {formatDate(timestamp)} {formatTime(timestamp)}
                                </Text>
                              )}
                              <IconButton
                                aria-label="Copy message"
                                icon={<CopyIcon />}
                                size="xs"
                                variant="ghost"
                                onClick={() => copyToClipboard(msg.message, 'Message')}
                              />
                            </HStack>
                          </HStack>
                          <Text>{msg.message}</Text>
                          {msg.files && msg.files.length > 0 && (
                            <VStack align="stretch" mt={2} spacing={1}>
                              {msg.files.map((file) => (
                                <HStack
                                  key={file.id}
                                  bg="whiteAlpha.50"
                                  p={2}
                                  borderRadius="sm"
                                  fontSize="xs"
                                  spacing={2}
                                >
                                  <AttachmentIcon />
                                  <Text flex="1" isTruncated>
                                    {file.original_filename}
                                  </Text>
                                  <Text color="gray.400">
                                    {(file.file_size / 1024).toFixed(1)} KB
                                  </Text>
                                </HStack>
                              ))}
                            </VStack>
                          )}
                        </Box>
                        {/* Assistant Message */}
                        {msg.response && (
                          <Box
                            bg={assistantMsgBg}
                            p={4}
                            borderRadius="md"
                            maxW="80%"
                            position="relative"
                          >
                            <HStack justify="space-between" mb={2}>
                              <HStack spacing={2}>
                                <Text fontWeight="bold" fontSize="sm" color="gray.400">
                                  Assistant
                                </Text>
                                <IconButton
                                  aria-label="Copy message"
                                  icon={<CopyIcon />}
                                  size="xs"
                                  variant="ghost"
                                  onClick={() => copyToClipboard(msg.response || '', 'Message')}
                                />
                                {(() => {
                                  // Format time in MM:SS format
                                  const formatTime = (seconds: number | undefined): string => {
                                    if (!seconds) return '0:00';
                                    const mins = Math.floor(seconds / 60);
                                    const secs = Math.floor(seconds % 60);
                                    return `${mins}:${secs.toString().padStart(2, '0')}`;
                                  };
                                  
                                  const totalReasoningTime = (msg.execution_times?.agent_time || 0) + (msg.execution_times?.tool_time || 0);
                                  
                                  // Debug: log execution_times to see what we have
                                  if (msg.execution_times) {
                                    console.log('Execution times for message', msg.id, ':', msg.execution_times);
                                  }
                                  
                                  const cachedToolCalls = msg.execution_times?.cached_tool_calls || 0;
                                  const totalToolCalls = msg.execution_times?.total_tool_calls || 0;

                                  return msg.execution_times ? (
                                    <HStack spacing={2} fontSize="xs" color="gray.400">
                                      <Text>
                                        Response {formatTime(msg.execution_times.total_time)}
                                        {cachedToolCalls > 0 && (
                                          <Tooltip label={`${cachedToolCalls}/${totalToolCalls} tool calls served from cache`}>
                                            <Text as="span" color="green.400" cursor="default"> *</Text>
                                          </Tooltip>
                                        )}
                                      </Text>
                                      {totalReasoningTime > 0 && (
                                        <Text>
                                          • Total reasoning {formatTime(totalReasoningTime)}
                                        </Text>
                                      )}
                                    </HStack>
                                  ) : null;
                                })()}
                              </HStack>
                              {(() => {
                                // Calculate completion time: request time + response duration
                                if (timestamp && msg.execution_times?.total_time) {
                                  const completionTime = new Date(timestamp.getTime() + (msg.execution_times.total_time * 1000));
                                  return (
                                    <Text fontSize="xs" color="gray.400">
                                      {formatDate(completionTime)} {formatTime(completionTime)}
                                    </Text>
                                  );
                                } else if (timestamp) {
                                  return (
                                    <Text fontSize="xs" color="gray.400">
                                      {formatDate(timestamp)} {formatTime(timestamp)}
                                    </Text>
                                  );
                                }
                                return null;
                              })()}
                            </HStack>
                            
                            {/* Visualizations are now rendered only within the TabbedMessageContent component */}
                            
                            {/* Execution Flow - Tabbed (Network vs Progress) */}
                            {(() => {
                              const trace = executionTraces[msg.id] || msg.execution_trace;
                              if (trace && trace.nodes && trace.nodes.length > 0) {
                                // Extract progress updates and LLM prompts from trace metadata if available
                                const progressUpdates = (trace as any).metadata?.progress_updates || [];
                                const llmPrompts = (trace as any).metadata?.llm_prompts || [];

                                return (
                                  <Box mb={4} p={3} bg="surface.900" borderRadius="md" borderWidth={1}>
                                    <Text fontSize="sm" fontWeight="bold" color="gray.300" mb={2}>
                                      Execution Flow
                                    </Text>
                                    <Tabs size="sm" variant="enclosed" isLazy>
                                      <TabList>
                                        <Tab>Network Graph</Tab>
                                        <Tab>Progress Stream</Tab>
                                        <Tab>LLM Prompts</Tab>
                                      </TabList>
                                      <TabPanels>
                                        <TabPanel p={0} pt={3} h="350px">
                                          <ExecutionGraph
                                            key={`trace-${msg.id}`}
                                            trace={trace}
                                            onNodeClick={(node) => {
                                              setSelectedNode(node);
                                              onNodeModalOpen();
                                            }}
                                          />
                                        </TabPanel>
                                        <TabPanel p={0} pt={3} h="350px" overflowY="auto">
                                          {progressUpdates.length > 0 ? (
                                            <ProgressTimeline
                                              updates={progressUpdates}
                                              isStreaming={false}
                                            />
                                          ) : (
                                            <Box p={4} textAlign="center" color="gray.400" fontSize="sm">
                                              Progress data not available for this query
                                            </Box>
                                          )}
                                        </TabPanel>
                                        <TabPanel p={0} pt={3} h="350px" overflowY="auto">
                                          {llmPrompts.length > 0 ? (
                                            <LLMPromptsViewer prompts={llmPrompts} />
                                          ) : (
                                            <Box p={4} textAlign="center" color="gray.400" fontSize="sm">
                                              LLM prompt data not available for this query
                                            </Box>
                                          )}
                                        </TabPanel>
                                      </TabPanels>
                                    </Tabs>
                                  </Box>
                                );
                              }
                              return null;
                            })()}

                            {/* Display error if present in execution trace */}
                            {msg.execution_trace?.metadata?.error && (
                              <Box
                                p={4}
                                bg="whiteAlpha.50"
                                borderRadius="md"
                                borderWidth={1}
                                borderColor="red.700"
                                mb={4}
                              >
                                <HStack spacing={2} mb={2}>
                                  <Text fontWeight="bold" fontSize="sm" color="red.300">
                                    ❌ Error Occurred
                                  </Text>
                                </HStack>
                                <Text fontSize="sm" color="red.300">
                                  {msg.execution_trace.metadata.error}
                                </Text>
                              </Box>
                            )}

                            <TabbedMessageContent
                              content={msg.response}
                              contentStructure={msg.content_structure}
                              citations={msg.citations}
                              files={msg.files}
                              userId={user?.id}
                            />

                            {/* Re-ask Button and Answer Mode Badge */}
                            <HStack mt={3} spacing={3} justify="space-between" align="center">
                              <ReAskButton
                                queryId={msg.id}
                                currentMode={msg.answer_mode}
                                onReAsk={handleReAsk}
                                isDisabled={isStreaming}
                              />
                              {msg.answer_mode && (
                                <HStack spacing={2}>
                                  <Text fontSize="xs" color="gray.400">Format:</Text>
                                  <Badge
                                    colorScheme={
                                      msg.answer_mode === 'summary' ? 'green' :
                                      msg.answer_mode === 'light' ? 'blue' :
                                      msg.answer_mode === 'extended' ? 'purple' :
                                      msg.answer_mode === 'project_plan' ? 'orange' :
                                      msg.answer_mode === 'roadmap' ? 'teal' :
                                      'gray'
                                    }
                                    fontSize="xs"
                                  >
                                    {msg.answer_mode === 'summary' ? 'EXEC SUMMARY' :
                                     msg.answer_mode === 'light' ? 'ONE-PAGER' :
                                     msg.answer_mode === 'extended' ? 'EXEC REPORT' :
                                     msg.answer_mode === 'project_plan' ? '30-60-90 PLAN' :
                                     'ROADMAP'}
                                  </Badge>
                                  {msg.reask_of_query_id && (
                                    <Tooltip label={`Re-generated from question #${msg.reask_of_query_id}`}>
                                      <Badge colorScheme="orange" fontSize="xs">
                                        RE-ASKED
                                      </Badge>
                                    </Tooltip>
                                  )}
                                </HStack>
                              )}
                            </HStack>

                            {/* Recommendations */}
                            {msg.recommendations && msg.recommendations.length > 0 && (
                              <Box mt={4} p={4} bg="whiteAlpha.50" borderRadius="md" borderWidth={1} borderColor="green.700">
                                <Text fontSize="sm" fontWeight="bold" color="green.300" mb={3}>
                                  📖 Suggested Readings
                                </Text>
                                <VStack align="stretch" spacing={2}>
                                  {msg.recommendations.map((rec, idx) => (
                                    <Text key={idx} fontSize="sm" color="gray.300">
                                      • {rec}
                                    </Text>
                                  ))}
                                </VStack>
                              </Box>
                            )}

                            {/* Follow-up Questions */}
                            {msg.followup_questions && msg.followup_questions.length > 0 && (
                              <FollowUpSuggestions
                                questions={msg.followup_questions}
                                parentQueryId={msg.id}
                                onQuestionClick={(question, type, parentQueryId) => {
                                  if (type === 'deep_dive' && parentQueryId && selectedOrgId && selectedThreadId) {
                                    sendMessageStream(
                                      question,
                                      selectedOrgId,
                                      selectedThreadId,
                                      undefined,
                                      chatMode,
                                      answerMode,
                                      undefined,
                                      undefined,
                                      parentQueryId
                                    );
                                  } else {
                                    setMessage(question);
                                  }
                                }}
                                onActivateFollowUpMode={(queryId) => {
                                  setFollowupOfQueryId(queryId);
                                  // Focus the message input
                                  const textarea = document.querySelector('textarea');
                                  if (textarea) textarea.focus();
                                }}
                              />
                            )}

                            {/* Generated Images are now rendered only within the TabbedMessageContent component */}
                          </Box>
                        )}
                      </VStack>
                      );
                    })}

                    {/* Streaming Response - show at the end of messages */}
                    {isStreaming && (
                      <Box key={`streaming-${streamStartTimeRef.current || Date.now()}`}>
                        <Box
                          bg="brand.900"
                          p={4}
                          borderRadius="lg"
                          mb={3}
                          maxW="75%"
                          ml="auto"
                          boxShadow="sm"
                        >
                          <Text fontWeight="semibold" fontSize="sm" mb={2} color="brand.300">
                            You
                          </Text>
                          <Text color="gray.200">{streamingMessage || message || 'Processing...'}</Text>
                        </Box>
                        <Box
                          bg={bgColor}
                          p={4}
                          borderRadius="lg"
                          maxW="75%"
                          borderWidth={1}
                          borderColor={borderColor}
                          boxShadow="sm"
                        >
                          <HStack mb={2}>
                            <Spinner size="sm" />
                            <Text fontWeight="bold" fontSize="sm" color="gray.400">
                              Assistant (Processing...)
                            </Text>
                          </HStack>
                          {streamingResponse && (
                            <TabbedMessageContent
                              content={streamingResponse}
                              contentStructure={streamingContentStructure}
                              citations={streamingCitations || undefined}
                              userId={user?.id}
                            />
                          )}

                          {/* Streaming Recommendations */}
                          {streamingRecommendations && streamingRecommendations.length > 0 && (
                            <Box mt={4} p={4} bg="whiteAlpha.50" borderRadius="md" borderWidth={1} borderColor="green.700">
                              <Text fontSize="sm" fontWeight="bold" color="green.300" mb={3}>
                                📖 Suggested Readings
                              </Text>
                              <VStack align="stretch" spacing={2}>
                                {streamingRecommendations.map((rec, idx) => (
                                  <Text key={idx} fontSize="sm" color="gray.300">
                                    • {rec}
                                  </Text>
                                ))}
                              </VStack>
                            </Box>
                          )}

                          {/* Streaming Follow-up Questions */}
                          {streamingFollowupQuestions && streamingFollowupQuestions.length > 0 && (
                            <FollowUpSuggestions
                              questions={streamingFollowupQuestions}
                              onQuestionClick={(question) => {
                                setMessage(question);
                              }}
                            />
                          )}
                        </Box>
                      </Box>
                    )}

                    {/* Execution View - Tabbed (Network vs Progress Stream) */}
                    {((streamingTrace && streamingTrace.nodes && streamingTrace.nodes.length > 0) || streamingProgress.length > 0) && (
                      <Box mt={4} p={3} bg="surface.900" borderRadius="md" borderWidth={1} key={`execution-view-${streamStartTimeRef.current || Date.now()}`}>
                        <HStack justify="space-between" mb={2}>
                          <Text fontSize="sm" fontWeight="bold" color="gray.300">
                            Execution View (Live)
                          </Text>
                        </HStack>
                        <Tabs size="sm" variant="enclosed" isLazy>
                          <TabList>
                            <Tab>Network Graph</Tab>
                            <Tab>Progress Stream</Tab>
                            <Tab>LLM Prompts</Tab>
                          </TabList>
                          <TabPanels>
                            <TabPanel p={0} pt={3} h="350px">
                              {streamingTrace && streamingTrace.nodes && streamingTrace.nodes.length > 0 ? (
                                <ExecutionGraph
                                  key={`streaming-${streamStartTimeRef.current || 'default'}`}
                                  trace={streamingTrace}
                                  onNodeClick={(node) => {
                                    setSelectedNode(node);
                                    onNodeModalOpen();
                                  }}
                                />
                              ) : (
                                <Box p={4} textAlign="center" color="gray.400" fontSize="sm">
                                  No network data yet...
                                </Box>
                              )}
                            </TabPanel>
                            <TabPanel p={0} pt={3} h="350px" overflowY="auto">
                              {streamingProgress.length > 0 ? (
                                <ProgressTimeline
                                  updates={streamingProgress}
                                  isStreaming={isStreaming}
                                />
                              ) : (
                                <Box p={4} textAlign="center" color="gray.400" fontSize="sm">
                                  No progress updates yet...
                                </Box>
                              )}
                            </TabPanel>
                            <TabPanel p={0} pt={3} h="350px" overflowY="auto">
                              <Box p={4} textAlign="center" color="gray.400" fontSize="sm">
                                Available after response completes
                              </Box>
                            </TabPanel>
                          </TabPanels>
                        </Tabs>
                      </Box>
                    )}
                    
                    <div ref={messagesEndRef} />
                  </VStack>
                ) : messagesError ? (
                  <Center h="100%">
                    <Text color="red.400" textAlign="center">
                      {(messagesError as any)?.response?.data?.detail || 'Failed to load messages. You may not have access to this thread.'}
                    </Text>
                  </Center>
                ) : (
                  <Center h="100%">
                    <Text color="gray.400" textAlign="center">
                      No messages yet. Start the conversation!
                    </Text>
                  </Center>
                )}
              </VStack>
            </>
          )}
      </Box>

      {/* Message Input - Always visible when org and thread selected */}
      {selectedOrgId && selectedThreadId && (
        <Box>
          {/* Execution Error / Retry Banner */}
          {streamError && lastFailedMessage && (
            <Box
              bg="whiteAlpha.50"
              borderTopWidth={1}
              borderColor="orange.700"
              px={4}
              py={3}
            >
              <HStack spacing={3} justify="space-between">
                <HStack spacing={2}>
                  <Text fontSize="sm" color="orange.300" fontWeight="medium">
                    ❌ Execution Error
                  </Text>
                  <Text fontSize="sm" color="orange.400">
                    {streamError}
                  </Text>
                </HStack>
                <HStack spacing={2}>
                  <Button
                    size="sm"
                    colorScheme="orange"
                    variant="outline"
                    onClick={() => {
                      setStreamError(null);
                      setLastFailedMessage(null);
                    }}
                  >
                    Dismiss
                  </Button>
                  <Button
                    size="sm"
                    colorScheme="orange"
                    onClick={() => {
                      if (lastFailedMessage) {
                        sendMessageStream(
                          lastFailedMessage.message,
                          lastFailedMessage.orgId,
                          lastFailedMessage.threadId,
                          lastFailedMessage.fileIds,
                          lastFailedMessage.mode,
                          lastFailedMessage.answerMode,
                          lastFailedMessage.reaskOfQueryId || null
                        );
                        setStreamError(null);
                        setLastFailedMessage(null);
                      }
                    }}
                  >
                    Retry
                  </Button>
                </HStack>
              </HStack>
            </Box>
          )}

          {/* Connection Error / Retry Banner */}
          {connectionError && lastFailedMessage && (
            <Box
              bg="whiteAlpha.50"
              borderTopWidth={1}
              borderColor="red.700"
              px={4}
              py={3}
            >
              <HStack spacing={3} justify="space-between">
                <HStack spacing={2}>
                  <Text fontSize="sm" color="red.300" fontWeight="medium">
                    ⚠️ Connection Error
                  </Text>
                  <Text fontSize="sm" color="red.600">
                    {connectionError}
                  </Text>
                </HStack>
                <HStack spacing={2}>
                  <Button
                    size="sm"
                    colorScheme="red"
                    variant="outline"
                    onClick={() => {
                      setConnectionError(null);
                      setLastFailedMessage(null);
                    }}
                  >
                    Dismiss
                  </Button>
                  <Button
                    size="sm"
                    colorScheme="red"
                    onClick={() => {
                      if (lastFailedMessage) {
                        sendMessageStream(
                          lastFailedMessage.message,
                          lastFailedMessage.orgId,
                          lastFailedMessage.threadId,
                          lastFailedMessage.fileIds,
                          lastFailedMessage.mode,
                          lastFailedMessage.answerMode,
                          lastFailedMessage.reaskOfQueryId
                        );
                      }
                    }}
                  >
                    Retry
                  </Button>
                </HStack>
              </HStack>
            </Box>
          )}

          {/* Answer Mode Selector */}
          <Box borderTopWidth="1px" borderColor={borderColor}>
            <AnswerModeSelector value={answerMode} onChange={setAnswerMode} />
          </Box>

          <MessageInput
            message={message}
            onMessageChange={setMessage}
            onSubmit={handleSubmit}
            isStreaming={isStreaming}
            selectedFileIds={selectedFileIds}
            uploadedFiles={uploadedFiles}
            onFileSelect={handleFileSelect}
            onFileUpload={handleFileUpload}
            isUploading={uploadFileMutation.isPending}
            selectedOrgId={selectedOrgId}
            isFollowUpMode={followupOfQueryId !== null}
            onCancelFollowUp={() => setFollowupOfQueryId(null)}
          />
        </Box>
      )}

      {/* Thread Preferences Modal */}
      <PreferencesModal
        isOpen={isPreferencesOpen}
        onClose={onPreferencesClose}
        budgetFocus={budgetFocus}
        responseLength={responseLength}
        creativity={creativity}
        onBudgetFocusChange={setBudgetFocus}
        onBudgetFocusChangeEnd={(value) => {
          if (selectedThreadId && user) {
            updateThreadMutation.mutate({
              thread_metadata: { 
                budget_focus: value,
                response_length: responseLength,
                creativity: creativity
              }
            });
          }
        }}
        onResponseLengthChange={setResponseLength}
        onResponseLengthChangeEnd={(value) => {
          if (selectedThreadId && user) {
            updateThreadMutation.mutate({
              thread_metadata: { 
                budget_focus: budgetFocus,
                response_length: value,
                creativity: creativity
              }
            });
          }
        }}
        onCreativityChange={setCreativity}
        onCreativityChangeEnd={(value) => {
          if (selectedThreadId && user) {
            updateThreadMutation.mutate({
              thread_metadata: {
                budget_focus: budgetFocus,
                response_length: responseLength,
                creativity: value
              }
            });
          }
        }}
        availableAgents={availableAgents}
        selectedAgentIds={currentThread?.selected_agent_ids}
        onAgentSelectionChange={(agentIds) => {
          if (selectedThreadId && user) {
            updateThreadMutation.mutate({ selected_agent_ids: agentIds });
          }
        }}
      />

      {/* Export Modal */}
      <ExportModal
        isOpen={isExportOpen}
        onClose={onExportClose}
        includeTraces={exportIncludeTraces}
        onIncludeTracesChange={setExportIncludeTraces}
        onExport={handleExport}
        hasMessages={!!messages && messages.length > 0}
      />

      {/* Clarification Modal */}
      <ClarificationModal
        isOpen={isClarificationOpen}
        onClose={onClarificationClose}
        questions={clarificationQuestions}
        onSubmit={handleClarificationSubmit}
        isSubmitting={isStreaming}
      />


      {/* Fullscreen Graph Modal */}
      {fullscreenTraceId && (() => {
        const trace = executionTraces[fullscreenTraceId] || 
          messages?.find(m => m.id === fullscreenTraceId)?.execution_trace;
        if (!trace) return null;
        
        return (
          <Box
            position="fixed"
            top={0}
            left={0}
            right={0}
            bottom={0}
            bg="surface.800"
            zIndex={9999}
            p={4}
            display="flex"
            flexDirection="column"
          >
            <HStack justify="space-between" mb={4} flexShrink={0}>
              <Heading size="md">Execution Flow - Full Screen</Heading>
              <Button onClick={() => setFullscreenTraceId(null)}>
                <CloseIcon mr={2} />
                Close
              </Button>
            </HStack>
            <Box flex="1" minH={0}>
              <ExecutionGraph 
                trace={trace}
                onNodeClick={(node) => {
                  setSelectedNode(node);
                  onNodeModalOpen();
                }}
              />
            </Box>
          </Box>
        );
      })()}

      {/* Node Details Modal */}
      <AlertDialog
        isOpen={isNodeModalOpen}
        leastDestructiveRef={cancelRef}
        onClose={onNodeModalClose}
        size="2xl"
      >
        <AlertDialogOverlay zIndex={10000}>
          <AlertDialogContent maxH="80vh" overflowY="auto" zIndex={10001}>
            <AlertDialogHeader fontSize="lg" fontWeight="bold">
              Node Details: {selectedNode?.name || 'Unknown'}
            </AlertDialogHeader>

            <AlertDialogBody>
              <Box>
                <VStack align="stretch" spacing={4}>
                  {/* Agent Usage Context - Show prominently for agent nodes */}
                  {selectedNode?.type === 'agent' && selectedNode?.metadata && (() => {
                    // Find all other instances of this agent in the current trace
                    const currentTrace = streamingTrace || 
                      (fullscreenTraceId !== null ? 
                        (executionTraces[fullscreenTraceId] || 
                         messages?.find(m => m.id === fullscreenTraceId)?.execution_trace) : null) ||
                      (selectedNode ? Object.values(executionTraces).find(t => 
                        t?.nodes?.some(n => n.id === selectedNode.id)) : null);
                    
                    const sameAgentNodes = currentTrace?.nodes?.filter(n => 
                      n.type === 'agent' && 
                      n.metadata?.agent_id === selectedNode.metadata?.agent_id &&
                      n.id !== selectedNode.id
                    ) || [];
                    
                    return (
                      <>
                        {selectedNode.metadata.delegated_task && (
                          <Box p={4} bg="whiteAlpha.50" borderRadius="md" borderWidth={1} borderColor="blue.700">
                            <Text fontWeight="bold" fontSize="sm" color="blue.300" mb={2}>
                              📋 Task/Query Assigned to This Instance:
                            </Text>
                            <Box fontSize="sm" color="blue.200" mb={2}>
                              <ReactMarkdown 
                                remarkPlugins={[remarkGfm]}
                                components={{
                                  strong: ({node, children, ...props}: any) => (
                                    <Text as="span" fontWeight="bold" display="inline" {...props}>
                                      {children}
                                    </Text>
                                  ),
                                  em: ({node, children, ...props}: any) => (
                                    <Text as="span" fontStyle="italic" display="inline" {...props}>
                                      {children}
                                    </Text>
                                  ),
                                  p: ({node, ...props}: any) => <Text mb={2} {...props} />,
                                  ul: ({node, ...props}: any) => <VStack as="ul" align="stretch" spacing={1} pl={4} mb={2} {...props} />,
                                  ol: ({node, ...props}: any) => <VStack as="ol" align="stretch" spacing={1} pl={4} mb={2} {...props} />,
                                  li: ({node, ...props}: any) => <Box as="li" {...props} />,
                                  a: ({node, href, children, ...props}: any) => (
                                    <a 
                                      href={href} 
                                      target="_blank" 
                                      rel="noopener noreferrer"
                                      style={{ color: 'var(--chakra-colors-blue-300)', textDecoration: 'underline' }}
                                      {...props}
                                    >
                                      {children}
                                    </a>
                                  ),
                                }}
                              >
                                {selectedNode.metadata.delegated_task}
                              </ReactMarkdown>
                            </Box>
                            {selectedNode.metadata.delegated_from && (
                              <Text fontSize="xs" color="blue.400" fontStyle="italic">
                                Delegated from: {selectedNode.metadata.delegated_from}
                              </Text>
                            )}
                          </Box>
                        )}
                        {selectedNode.metadata.query && !selectedNode.metadata.delegated_task && (
                          <Box p={4} bg="whiteAlpha.50" borderRadius="md" borderWidth={1} borderColor="green.700">
                            <Text fontWeight="bold" fontSize="sm" color="green.300" mb={2}>
                              📋 Initial Query for This Instance:
                            </Text>
                            <Box fontSize="sm" color="green.200">
                              <ReactMarkdown 
                                remarkPlugins={[remarkGfm]}
                                components={{
                                  strong: ({node, children, ...props}: any) => (
                                    <Text as="span" fontWeight="bold" display="inline" {...props}>
                                      {children}
                                    </Text>
                                  ),
                                  em: ({node, children, ...props}: any) => (
                                    <Text as="span" fontStyle="italic" display="inline" {...props}>
                                      {children}
                                    </Text>
                                  ),
                                  p: ({node, ...props}: any) => <Text mb={2} {...props} />,
                                  ul: ({node, ...props}: any) => <VStack as="ul" align="stretch" spacing={1} pl={4} mb={2} {...props} />,
                                  ol: ({node, ...props}: any) => <VStack as="ol" align="stretch" spacing={1} pl={4} mb={2} {...props} />,
                                  li: ({node, ...props}: any) => <Box as="li" {...props} />,
                                  a: ({node, href, children, ...props}: any) => (
                                    <a 
                                      href={href} 
                                      target="_blank" 
                                      rel="noopener noreferrer"
                                      style={{ color: 'var(--chakra-colors-blue-300)', textDecoration: 'underline' }}
                                      {...props}
                                    >
                                      {children}
                                    </a>
                                  ),
                                }}
                              >
                                {selectedNode.metadata.query}
                              </ReactMarkdown>
                            </Box>
                          </Box>
                        )}
                        
                        {/* Show other instances if agent appears multiple times */}
                        {sameAgentNodes.length > 0 && (
                          <Box p={4} bg="whiteAlpha.50" borderRadius="md" borderWidth={1} borderColor="yellow.700">
                            <Text fontWeight="bold" fontSize="sm" color="yellow.400" mb={2}>
                              🔄 Other Instances of This Agent ({sameAgentNodes.length}):
                            </Text>
                            <VStack align="stretch" spacing={2}>
                              {sameAgentNodes.map((otherNode, idx) => (
                                <Box key={otherNode.id} p={2} bg="surface.800" borderRadius="md" borderWidth={1}>
                                  <Text fontSize="xs" fontWeight="bold" color="gray.400" mb={1}>
                                    Instance {idx + 1} (ID: {otherNode.id.slice(-8)})
                                  </Text>
                                  {otherNode.metadata?.delegated_task ? (
                                    <Text fontSize="xs" color="gray.300" whiteSpace="pre-wrap">
                                      Task: {otherNode.metadata.delegated_task.substring(0, 150)}
                                      {otherNode.metadata.delegated_task.length > 150 ? '...' : ''}
                                    </Text>
                                  ) : otherNode.metadata?.query ? (
                                    <Text fontSize="xs" color="gray.300" whiteSpace="pre-wrap">
                                      Query: {otherNode.metadata.query.substring(0, 150)}
                                      {otherNode.metadata.query.length > 150 ? '...' : ''}
                                    </Text>
                                  ) : (
                                    <Text fontSize="xs" color="gray.400" fontStyle="italic">
                                      No task/query information available
                                    </Text>
                                  )}
                                </Box>
                              ))}
                            </VStack>
                          </Box>
                        )}
                        
                        {selectedNode.metadata.role && (
                          <Box>
                            <Text fontWeight="bold" fontSize="sm" mb={1}>Role:</Text>
                            <Text fontSize="sm">{selectedNode.metadata.role}</Text>
                          </Box>
                        )}
                      </>
                    );
                  })()}
                  
                  {/* Tool Usage Context */}
                  {selectedNode?.type === 'tool' && selectedNode?.metadata && (
                    <>
                      {selectedNode.metadata.arguments && (
                        <Box p={4} bg="whiteAlpha.50" borderRadius="md" borderWidth={1} borderColor="orange.700">
                          <Text fontWeight="bold" fontSize="sm" color="orange.300" mb={2}>
                            🔧 Tool Arguments:
                          </Text>
                          <Box
                            bg="surface.800"
                            p={2}
                            borderRadius="md"
                            borderWidth={1}
                            overflowX="auto"
                            maxH="300px"
                            overflowY="auto"
                          >
                            <pre style={{ margin: 0, fontSize: '12px', whiteSpace: 'pre-wrap' }}>
                              {JSON.stringify(selectedNode.metadata.arguments, null, 2)}
                            </pre>
                          </Box>
                        </Box>
                      )}
                      {/* Render generated image if this is an image_generator tool */}
                      {selectedNode.name === 'image_generator' && (() => {
                        try {
                          const resultText = selectedNode.metadata.result || selectedNode.metadata.result_preview || '';
                          let imageFileInfo = null;
                          
                          // Try to parse the result as JSON (the tool returns JSON with file info)
                          if (resultText) {
                            try {
                              const parsed = JSON.parse(resultText);
                              if (parsed.success && parsed.file_path) {
                                imageFileInfo = parsed;
                              }
                            } catch {
                              // Not JSON, continue
                            }
                          }
                          
                          // Also check if we have file info in metadata directly
                          if (!imageFileInfo && selectedNode.metadata.file_info) {
                            imageFileInfo = selectedNode.metadata.file_info;
                          }
                          
                          // If we have file info, try to find the associated file ID from the query
                          if (imageFileInfo) {
                            // Find the current message/query that contains this node
                            const currentMessage = messages?.find(m => {
                              const trace = executionTraces[m.id] || m.execution_trace;
                              return trace?.nodes?.some(n => n.id === selectedNode.id);
                            });
                            
                            // Find image files associated with this query
                            const imageFiles = currentMessage?.files?.filter(f => 
                              f.content_type?.startsWith('image/') && 
                              f.original_filename.includes('generated_image')
                            ) || [];
                            
                            if (imageFiles.length > 0) {
                              // Use the first matching image file
                              const imageFile = imageFiles[0];
                              const imageUrl = `${API_URL}/api/files/${imageFile.id}/download?user_id=${user?.id}`;
                              
                              return (
                                <Box p={4} bg="whiteAlpha.50" borderRadius="md" borderWidth={1} borderColor="green.700" mt={4}>
                                  <Text fontWeight="bold" fontSize="sm" color="green.300" mb={2}>
                                    🖼️ Generated Image:
                                  </Text>
                                  <Box
                                    bg="surface.800"
                                    p={3}
                                    borderRadius="md"
                                    borderWidth={1}
                                    maxW="100%"
                                  >
                                    <img 
                                      src={imageUrl} 
                                      alt={imageFileInfo.prompt || "Generated image"}
                                      style={{ 
                                        maxWidth: '100%', 
                                        height: 'auto',
                                        borderRadius: '8px'
                                      }}
                                    />
                                    {imageFileInfo.prompt && (
                                      <Text fontSize="xs" color="gray.400" mt={2} fontStyle="italic">
                                        Prompt: {imageFileInfo.prompt}
                                      </Text>
                                    )}
                                  </Box>
                                </Box>
                              );
                            }
                          }
                          
                          // Fallback: show that image was generated but file not found
                          // Try to show the file_path if available for debugging
                          const filePath = imageFileInfo?.file_path;
                          return (
                            <Box p={4} bg="whiteAlpha.50" borderRadius="md" borderWidth={1} borderColor="yellow.700" mt={4}>
                              <Text fontWeight="bold" fontSize="sm" color="yellow.400" mb={2}>
                                ⚠️ Image Generated
                              </Text>
                              <Text fontSize="xs" color="yellow.300" mb={2}>
                                An image was generated, but the file association could not be found. The file may still be processing or there was an issue associating it with the query.
                              </Text>
                              {filePath && (
                                <Text fontSize="xs" color="gray.400" fontFamily="mono" mt={2}>
                                  File path: {filePath}
                                </Text>
                              )}
                              {imageFileInfo && (
                                <Box mt={2} p={2} bg="surface.800" borderRadius="md" fontSize="xs">
                                  <Text fontWeight="bold" mb={1}>File Info:</Text>
                                  <Text>Size: {imageFileInfo.file_size ? `${(imageFileInfo.file_size / 1024).toFixed(2)} KB` : 'Unknown'}</Text>
                                  <Text>Type: {imageFileInfo.content_type || 'image/png'}</Text>
                                  {imageFileInfo.prompt && (
                                    <Text mt={1} fontStyle="italic">Prompt: {imageFileInfo.prompt.substring(0, 100)}...</Text>
                                  )}
                                </Box>
                              )}
                            </Box>
                          );
                        } catch (error) {
                          return (
                            <Box p={4} bg="whiteAlpha.50" borderRadius="md" borderWidth={1} borderColor="red.700" mt={4}>
                              <Text fontWeight="bold" fontSize="sm" color="red.300" mb={2}>
                                ❌ Image Display Error
                              </Text>
                              <Text fontSize="xs" color="red.300">
                                Error displaying image: {error instanceof Error ? error.message : String(error)}
                              </Text>
                            </Box>
                          );
                        }
                      })()}
                      {/* Render ECharts visualization if this is a visualizer tool */}
                      {selectedNode.name === 'visualizer' && (() => {
                        try {
                          // The visualizer tool returns instructions, but the actual ECharts config
                          // is generated by the LLM and might be in the result text.
                          // We need to extract it from the result, which may contain the JSON config.
                          
                          let echartsConfig = null;
                          let configSource = '';
                          let debugInfo: string[] = [];
                          
                          // Check for direct echarts_config in metadata
                          if (selectedNode.metadata.echarts_config) {
                            echartsConfig = typeof selectedNode.metadata.echarts_config === 'string'
                              ? JSON.parse(selectedNode.metadata.echarts_config)
                              : selectedNode.metadata.echarts_config;
                            configSource = 'echarts_config';
                          } else {
                            // Try to extract from result text - the LLM generates the config
                            const resultText = selectedNode.metadata.result || selectedNode.metadata.result_preview || '';
                            debugInfo.push(`Result text length: ${resultText.length}`);
                            
                            if (resultText) {
                              // First try to find visualization markers [VISUALIZATION_START]... [VISUALIZATION_END]
                              const vizMatch = resultText.match(/\[VISUALIZATION_START\](.*?)\[VISUALIZATION_END\]/s);
                              if (vizMatch) {
                                const configStr = vizMatch[1].trim();
                                debugInfo.push(`Found VISUALIZATION markers, length: ${configStr.length}`);
                                
                                // Try direct JSON parse first
                                try {
                                  echartsConfig = JSON.parse(configStr);
                                  configSource = 'VISUALIZATION markers (direct)';
                                } catch (e) {
                                  debugInfo.push(`Direct parse failed: ${e instanceof Error ? e.message : String(e)}`);
                                  
                                  // If direct parse fails, try to extract JSON object from the content
                                  // Look for JSON object that starts with ECharts-specific keys
                                  const echartsPattern = /\{\s*"(?:title|series|xAxis|yAxis|legend|tooltip)"\s*:/;
                                  const jsonMatch = configStr.match(echartsPattern);
                                  
                                  if (jsonMatch) {
                                    try {
                                      const startPos = jsonMatch.index!;
                                      // Extract complete JSON object by counting braces
                                      let braceCount = 0;
                                      let inString = false;
                                      let escapeNext = false;
                                      let jsonStr = '';
                                      
                                      for (let i = startPos; i < configStr.length; i++) {
                                        const char = configStr[i];
                                        
                                        if (escapeNext) {
                                          escapeNext = false;
                                          jsonStr += char;
                                          continue;
                                        }
                                        
                                        if (char === '\\') {
                                          escapeNext = true;
                                          jsonStr += char;
                                          continue;
                                        }
                                        
                                        if (char === '"' && !escapeNext) {
                                          inString = !inString;
                                          jsonStr += char;
                                          continue;
                                        }
                                        
                                        jsonStr += char;
                                        
                                        if (!inString) {
                                          if (char === '{') {
                                            braceCount++;
                                          } else if (char === '}') {
                                            braceCount--;
                                            if (braceCount === 0) {
                                              // Found complete JSON object
                                              break;
                                            }
                                          }
                                        }
                                      }
                                      
                                      if (braceCount === 0 && jsonStr) {
                                        debugInfo.push(`Extracted JSON from markers, length: ${jsonStr.length}`);
                                        const parsed = JSON.parse(jsonStr);
                                        // Verify this is an ECharts config (not tool arguments)
                                        if (parsed && 
                                            !(parsed.data && parsed.chart_type) &&  // Not tool arguments
                                            (parsed.series || parsed.xAxis || parsed.yAxis || 
                                             (parsed.title && typeof parsed.title === 'object'))) {
                                          echartsConfig = parsed;
                                          configSource = 'VISUALIZATION markers (extracted)';
                                        }
                                      }
                                    } catch (extractError) {
                                      debugInfo.push(`Failed to extract JSON from markers: ${extractError instanceof Error ? extractError.message : String(extractError)}`);
                                      debugInfo.push(`Content preview: ${configStr.substring(0, 500)}`);
                                    }
                                  } else {
                                    debugInfo.push(`No ECharts pattern found in markers content`);
                                    debugInfo.push(`Content preview: ${configStr.substring(0, 500)}`);
                                  }
                                  
                                  // Try to clean and fix common placeholder issues
                                  if (!echartsConfig) {
                                    try {
                                      // Replace common placeholder patterns
                                      let cleaned = configStr
                                        .replace(/\.\.\./g, '') // Remove "..."
                                        .replace(/\[\.\.\.\]/g, '[]') // Replace [...] with []
                                        .replace(/"\.\.\."/g, '""') // Replace "..." with ""
                                        .replace(/\.\.\.,/g, '') // Remove "...,"
                                        .replace(/,\s*\.\.\./g, '') // Remove ", ..."
                                        .replace(/\.\.\.\s*\}/g, '}') // Remove "... }"
                                        .replace(/\.\.\.\s*\]/g, ']'); // Remove "... ]"
                                      
                                      // Try to find JSON object in cleaned string
                                      const cleanedPattern = /\{\s*"(?:title|series|xAxis|yAxis|legend|tooltip)"\s*:/;
                                      const cleanedMatch = cleaned.match(cleanedPattern);
                                      
                                      if (cleanedMatch) {
                                        const startPos = cleanedMatch.index!;
                                        let braceCount = 0;
                                        let inString = false;
                                        let escapeNext = false;
                                        let jsonStr = '';
                                        
                                        for (let i = startPos; i < cleaned.length; i++) {
                                          const char = cleaned[i];
                                          
                                          if (escapeNext) {
                                            escapeNext = false;
                                            jsonStr += char;
                                            continue;
                                          }
                                          
                                          if (char === '\\') {
                                            escapeNext = true;
                                            jsonStr += char;
                                            continue;
                                          }
                                          
                                          if (char === '"' && !escapeNext) {
                                            inString = !inString;
                                            jsonStr += char;
                                            continue;
                                          }
                                          
                                          jsonStr += char;
                                          
                                          if (!inString) {
                                            if (char === '{') {
                                              braceCount++;
                                            } else if (char === '}') {
                                              braceCount--;
                                              if (braceCount === 0) {
                                                break;
                                              }
                                            }
                                          }
                                        }
                                        
                                        if (braceCount === 0 && jsonStr) {
                                          const parsed = JSON.parse(jsonStr);
                                          if (parsed && 
                                              !(parsed.data && parsed.chart_type) &&
                                              (parsed.series || parsed.xAxis || parsed.yAxis || 
                                               (parsed.title && typeof parsed.title === 'object'))) {
                                            echartsConfig = parsed;
                                            configSource = 'VISUALIZATION markers (cleaned)';
                                            debugInfo.push(`Successfully parsed after cleaning placeholders`);
                                          }
                                        }
                                      }
                                    } catch (cleanError) {
                                      debugInfo.push(`Cleaning attempt failed: ${cleanError instanceof Error ? cleanError.message : String(cleanError)}`);
                                    }
                                  }
                                }
                              }
                              
                              // If not found, try to find JSON object in the text (look for ECharts configs, not tool arguments)
                              if (!echartsConfig) {
                                // Look for ALL JSON objects that start with ECharts-specific keys (not tool arguments)
                                const echartsPattern = /\{\s*"(?:title|series|xAxis|yAxis|legend|tooltip)"\s*:/g;
                                const matches = [...resultText.matchAll(echartsPattern)];
                                
                                // Try each match, skipping ones with placeholders
                                for (const match of matches) {
                                  if (!match.index) continue;
                                  try {
                                    const startPos = match.index!;
                                    // Extract complete JSON object by counting braces
                                    let braceCount = 0;
                                    let inString = false;
                                    let escapeNext = false;
                                    let jsonStr = '';
                                    
                                    for (let i = startPos; i < resultText.length; i++) {
                                      const char = resultText[i];
                                      
                                      if (escapeNext) {
                                        escapeNext = false;
                                        jsonStr += char;
                                        continue;
                                      }
                                      
                                      if (char === '\\') {
                                        escapeNext = true;
                                        jsonStr += char;
                                        continue;
                                      }
                                      
                                      if (char === '"' && !escapeNext) {
                                        inString = !inString;
                                        jsonStr += char;
                                        continue;
                                      }
                                      
                                      jsonStr += char;
                                      
                                      if (!inString) {
                                        if (char === '{') {
                                          braceCount++;
                                        } else if (char === '}') {
                                          braceCount--;
                                          if (braceCount === 0) {
                                            // Found complete JSON object
                                            break;
                                          }
                                        }
                                      }
                                    }
                                    
                                    if (braceCount === 0 && jsonStr) {
                                      // Skip if it contains placeholder patterns
                                      if (jsonStr.includes('...') || jsonStr.includes('…')) {
                                        debugInfo.push(`Skipping JSON with placeholders, length: ${jsonStr.length}`);
                                        continue;
                                      }
                                      
                                      debugInfo.push(`Found JSON object pattern, length: ${jsonStr.length}`);
                                      try {
                                        const parsed = JSON.parse(jsonStr);
                                        // Verify this is an ECharts config (not tool arguments)
                                        // Tool arguments have "data" and "chart_type" as top-level keys
                                        if (parsed && 
                                            !(parsed.data && parsed.chart_type) &&  // Not tool arguments
                                            (parsed.series || parsed.xAxis || parsed.yAxis || 
                                             (parsed.title && typeof parsed.title === 'object'))) {
                                          echartsConfig = parsed;
                                          configSource = 'JSON pattern match';
                                          break; // Found valid config
                                        }
                                      } catch (parseError) {
                                        debugInfo.push(`Parse failed: ${parseError instanceof Error ? parseError.message : String(parseError)}`);
                                      }
                                    }
                                  } catch (e) {
                                    debugInfo.push(`Failed to parse JSON pattern: ${e instanceof Error ? e.message : String(e)}`);
                                    // Continue to next match
                                  }
                                  if (echartsConfig) break; // Found valid config, stop searching
                                }
                              }
                              
                              // If still not found, try parsing the entire result as JSON
                              if (!echartsConfig && resultText.trim()) {
                                try {
                                  const trimmed = resultText.trim();
                                  // Skip if it looks like instructions (starts with "Generate" or similar)
                                  if (!trimmed.toLowerCase().startsWith('generate') && !trimmed.toLowerCase().startsWith('create')) {
                                    const parsed = JSON.parse(trimmed);
                                    if (parsed && (parsed.series || parsed.xAxis || parsed.yAxis || parsed.title)) {
                                      echartsConfig = parsed;
                                      configSource = 'full result JSON';
                                    }
                                  }
                                } catch {
                                  // Not JSON, continue
                                }
                              }
                              
                              // Also check if result is already an object (not a string)
                              if (!echartsConfig && selectedNode.metadata.result && typeof selectedNode.metadata.result === 'object') {
                                const result = selectedNode.metadata.result;
                                if (result.series || result.xAxis || result.yAxis || result.title) {
                                  echartsConfig = result;
                                  configSource = 'result object';
                                }
                              }
                            }
                          }
                          
                          if (echartsConfig) {
                            return (
                              <Box p={4} bg="whiteAlpha.50" borderRadius="md" borderWidth={1} borderColor="purple.700" mt={4}>
                                <Text fontWeight="bold" fontSize="sm" color="purple.700" mb={2}>
                                  📊 Visualization (from {configSource}):
                                </Text>
                                <Box
                                  bg="surface.800"
                                  p={3}
                                  borderRadius="md"
                                  borderWidth={1}
                                  minH="400px"
                                >
                                  <ReactECharts
                                    option={{
                                      ...echartsConfig,
                                      legend: {
                                        ...(echartsConfig.legend || {}),
                                        bottom: 0, // Always position legend at bottom
                                        orient: echartsConfig.legend?.orient || 'horizontal',
                                        selectedMode: 'multiple', // Allow clicking legend to toggle series visibility
                                        type: echartsConfig.legend?.type || 'scroll',
                                      },
                                    }}
                                    style={{ height: '400px', width: '100%' }}
                                    opts={{ renderer: 'canvas', locale: 'EN' }}
                                  />
                                </Box>
                              </Box>
                            );
                          } else {
                            // Show debug info if we can't find the config
                            return (
                              <Box p={4} bg="whiteAlpha.50" borderRadius="md" borderWidth={1} borderColor="yellow.700" mt={4}>
                                <Text fontWeight="bold" fontSize="sm" color="yellow.400" mb={2}>
                                  ⚠️ Visualization Config Not Found
                                </Text>
                                <Text fontSize="xs" color="yellow.300" mb={2}>
                                  Could not extract ECharts config from metadata. The visualizer tool returns instructions, and the actual chart config is generated by the LLM in its response.
                                </Text>
                                {debugInfo.length > 0 && (
                                  <Box mt={2} p={2} bg="whiteAlpha.100" borderRadius="sm">
                                    <Text fontSize="xs" fontWeight="bold" mb={1}>Debug Info:</Text>
                                    {debugInfo.map((info, idx) => (
                                      <Text key={idx} fontSize="xs" color="yellow.300">{info}</Text>
                                    ))}
                                  </Box>
                                )}
                                <Text fontSize="xs" color="yellow.300" mt={2}>
                                  Check the "Full Result" section below - it may contain the ECharts JSON config that needs to be extracted.
                                </Text>
                              </Box>
                            );
                          }
                        } catch (error) {
                          // Show error if parsing fails
                          return (
                            <Box p={4} bg="whiteAlpha.50" borderRadius="md" borderWidth={1} borderColor="red.700" mt={4}>
                              <Text fontWeight="bold" fontSize="sm" color="red.300" mb={2}>
                                ❌ Visualization Error
                              </Text>
                              <Text fontSize="xs" color="red.300">
                                Error parsing visualization config: {error instanceof Error ? error.message : String(error)}
                              </Text>
                            </Box>
                          );
                        }
                      })()}
                      {selectedNode.metadata.result && (() => {
                        const result = selectedNode.metadata.result;
                        const isString = typeof result === 'string';
                        const resultString = isString ? result : JSON.stringify(result, null, 2);
                        
                        // Check if this is a SWOT analysis (special formatting)
                        const isSWOT = isString && (
                          result.toLowerCase().includes('swot analysis') ||
                          (result.includes('STRENGTHS') && result.includes('WEAKNESSES') && 
                           result.includes('OPPORTUNITIES') && result.includes('THREATS'))
                        );
                        
                        // Check if the result looks like markdown (contains markdown patterns)
                        const looksLikeMarkdown = isString && (
                          result.includes('##') || 
                          result.includes('**') || 
                          result.includes('*') ||
                          result.includes('[') && result.includes('](') ||
                          result.includes('```') ||
                          result.includes('- ') ||
                          result.includes('1. ')
                        );
                        
                        // Check if it's JSON (starts with { or [)
                        const isJSON = isString && (result.trim().startsWith('{') || result.trim().startsWith('['));
                        
                        return (
                          <Box>
                            <Text fontWeight="bold" fontSize="sm" mb={1}>Full Result:</Text>
                            <Box
                              bg="surface.900"
                              p={4}
                              borderRadius="md"
                              borderWidth={1}
                              maxH="400px"
                              overflowY="auto"
                              overflowX="auto"
                            >
                              {(() => {
                                // Comprehensive markdown components for better rendering
                                const markdownComponents = {
                                  h1: ({node, ...props}: any) => <Heading size="lg" mb={4} mt={2} {...props} />,
                                  h2: ({node, ...props}: any) => <Heading size="md" mt={4} mb={3} fontWeight="bold" {...props} />,
                                  h3: ({node, ...props}: any) => <Heading size="sm" mt={3} mb={2} fontWeight="semibold" {...props} />,
                                  h4: ({node, ...props}: any) => <Heading size="xs" mt={3} mb={2} fontWeight="semibold" {...props} />,
                                  h5: ({node, ...props}: any) => <Text fontSize="sm" fontWeight="bold" mt={2} mb={1} {...props} />,
                                  h6: ({node, ...props}: any) => <Text fontSize="xs" fontWeight="bold" mt={2} mb={1} {...props} />,
                                  p: ({node, ...props}: any) => <Text mb={3} lineHeight="1.6" {...props} />,
                                  strong: ({node, children, ...props}: any) => (
                                    <Text as="span" fontWeight="bold" display="inline" {...props}>
                                      {children}
                                    </Text>
                                  ),
                                  em: ({node, children, ...props}: any) => (
                                    <Text as="span" fontStyle="italic" display="inline" {...props}>
                                      {children}
                                    </Text>
                                  ),
                                  ul: ({node, ...props}: any) => <VStack as="ul" align="stretch" spacing={2} pl={6} mb={3} listStyleType="disc" {...props} />,
                                  ol: ({node, ...props}: any) => <VStack as="ol" align="stretch" spacing={2} pl={6} mb={3} listStyleType="decimal" {...props} />,
                                  li: ({node, ...props}: any) => <Box as="li" mb={1} lineHeight="1.6" {...props} />,
                                  blockquote: ({node, ...props}: any) => (
                                    <Box 
                                      as="blockquote"
                                      borderLeftWidth={4}
                                      borderColor="blue.300"
                                      pl={4}
                                      py={2}
                                      my={3}
                                      bg="whiteAlpha.50"
                                      fontStyle="italic"
                                      {...props}
                                    />
                                  ),
                                  code: ({node, inline, ...props}: any) => {
                                    if (inline) {
                                      return (
                                        <Text
                                          as="code"
                                          fontFamily="mono"
                                          fontSize="0.9em"
                                          bg="surface.800"
                                          px={1.5}
                                          py={0.5}
                                          borderRadius="sm"
                                          {...props}
                                        />
                                      );
                                    }
                                    return (
                                      <Box
                                        as="pre"
                                        bg="gray.900"
                                        color="gray.100"
                                        p={4}
                                        borderRadius="md"
                                        overflowX="auto"
                                        my={3}
                                        fontSize="xs"
                                        fontFamily="mono"
                                        {...props}
                                      />
                                    );
                                  },
                                  hr: ({node, ...props}: any) => <Divider my={4} {...props} />,
                                  table: ({node, ...props}: any) => (
                                    <Box overflowX="auto" my={4}>
                                      <Box as="table" width="100%" borderCollapse="collapse" {...props} />
                                    </Box>
                                  ),
                                  thead: ({node, ...props}: any) => <Box as="thead" bg="surface.800" {...props} />,
                                  tbody: ({node, ...props}: any) => <Box as="tbody" {...props} />,
                                  tr: ({node, ...props}: any) => <Box as="tr" borderBottomWidth={1} borderColor="whiteAlpha.100" {...props} />,
                                  th: ({node, ...props}: any) => (
                                    <Box as="th" px={3} py={2} textAlign="left" fontWeight="bold" fontSize="sm" {...props} />
                                  ),
                                  td: ({node, ...props}: any) => (
                                    <Box as="td" px={3} py={2} fontSize="sm" {...props} />
                                  ),
                                  a: ({node, href, children, ...props}: any) => (
                                    <a 
                                      href={href} 
                                      target="_blank" 
                                      rel="noopener noreferrer"
                                      style={{ color: 'var(--chakra-colors-blue-300)', textDecoration: 'underline' }}
                                      {...props}
                                    >
                                      {children}
                                    </a>
                                  ),
                                };

                                if (isSWOT || (looksLikeMarkdown && !isJSON)) {
                                  return (
                                    <Box fontSize="sm" px={2}>
                                      <ReactMarkdown 
                                        remarkPlugins={[remarkGfm]}
                                        components={markdownComponents}
                                      >
                                        {resultString}
                                      </ReactMarkdown>
                                    </Box>
                                  );
                                } else if (isJSON) {
                                  return (
                                    <Text fontSize="xs" fontFamily="mono" color="gray.400" whiteSpace="pre-wrap" px={2}>
                                      {resultString}
                                    </Text>
                                  );
                                } else {
                                  return (
                                    <Text fontSize="sm" color="gray.300" whiteSpace="pre-wrap" px={2}>
                                      {resultString}
                                    </Text>
                                  );
                                }
                              })()}
                            </Box>
                          </Box>
                        );
                      })()}
                    </>
                  )}
                  
                  <Divider />
                  
                  <Box>
                    <Text fontWeight="bold" mb={1}>Type:</Text>
                    <Text>{selectedNode?.type || 'N/A'}</Text>
                  </Box>
                  <Box>
                    <Text fontWeight="bold" mb={1}>Node ID:</Text>
                    <Text fontFamily="mono" fontSize="sm">{selectedNode?.id || 'N/A'}</Text>
                  </Box>
                  {selectedNode?.metadata && (
                    <Accordion defaultIndex={[]} allowToggle>
                      <AccordionItem border="none">
                        <AccordionButton px={0} py={2} _hover={{ bg: 'transparent' }}>
                          <Box flex="1" textAlign="left">
                            <Text fontWeight="bold">Full Metadata</Text>
                          </Box>
                          <HStack spacing={2}>
                            <Button
                              size="xs"
                              leftIcon={<DownloadIcon />}
                              variant="ghost"
                              onClick={(e) => {
                                e.stopPropagation();
                                if (selectedNode) {
                                  const metadataJson = JSON.stringify(selectedNode, null, 2);
                                  const blob = new Blob([metadataJson], { type: 'application/json' });
                                  const url = URL.createObjectURL(blob);
                                  const a = document.createElement('a');
                                  a.href = url;
                                  const nodeName = selectedNode.name || 'node';
                                  const nodeId = selectedNode.id || 'unknown';
                                  a.download = `${nodeName}-${nodeId}-metadata.json`;
                                  document.body.appendChild(a);
                                  a.click();
                                  document.body.removeChild(a);
                                  URL.revokeObjectURL(url);
                                }
                              }}
                              onClickCapture={(e) => e.stopPropagation()}
                            >
                              Download
                            </Button>
                            <AccordionIcon />
                          </HStack>
                        </AccordionButton>
                        <AccordionPanel px={0} pb={4}>
                          <Box
                            bg="surface.900"
                            p={3}
                            borderRadius="md"
                            borderWidth={1}
                            maxH="500px"
                            overflowY="auto"
                            overflowX="auto"
                          >
                            <pre style={{ margin: 0, fontSize: '12px', whiteSpace: 'pre-wrap', wordBreak: 'break-word' }}>
                              {JSON.stringify(selectedNode.metadata, null, 2)}
                            </pre>
                          </Box>
                        </AccordionPanel>
                      </AccordionItem>
                    </Accordion>
                  )}
                </VStack>
              </Box>
            </AlertDialogBody>

            <AlertDialogFooter>
              <Button
                leftIcon={<DownloadIcon />}
                variant="outline"
                onClick={() => {
                  if (selectedNode) {
                    const metadataJson = JSON.stringify(selectedNode, null, 2);
                    const blob = new Blob([metadataJson], { type: 'application/json' });
                    const url = URL.createObjectURL(blob);
                    const a = document.createElement('a');
                    a.href = url;
                    a.download = `node-${selectedNode.id}-metadata.json`;
                    document.body.appendChild(a);
                    a.click();
                    document.body.removeChild(a);
                    URL.revokeObjectURL(url);
                  }
                }}
              >
                Download Metadata
              </Button>
              <Button onClick={onNodeModalClose}>
                Close
              </Button>
            </AlertDialogFooter>
          </AlertDialogContent>
        </AlertDialogOverlay>
      </AlertDialog>
    </Box>
  );
};

export default Chat;
