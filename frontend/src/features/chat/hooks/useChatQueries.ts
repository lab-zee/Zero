import { useQuery } from '@tanstack/react-query';
import { chatAPI, organizationAPI, fileAPI } from '../../../services/api';

interface UseChatQueriesOptions {
  userId: number | undefined;
  selectedOrgId: number | null;
  selectedThreadId: number | null;
}

export function useChatQueries({ userId, selectedOrgId, selectedThreadId }: UseChatQueriesOptions) {
  // Fetch user's organizations
  const {
    data: organizations,
    isLoading: organizationsLoading,
    error: organizationsError,
  } = useQuery({
    queryKey: ['organizations', userId],
    queryFn: () => organizationAPI.getMyOrganizations(userId!),
    enabled: !!userId,
  });

  // Fetch threads for selected organization
  const {
    data: threads,
    isLoading: threadsLoading,
    error: threadsError,
  } = useQuery({
    queryKey: ['threads', userId, selectedOrgId],
    queryFn: () => chatAPI.getThreads(userId!, selectedOrgId!),
    enabled: !!userId && !!selectedOrgId,
  });

  // Get current thread data
  const currentThread = threads?.find(t => t.id === selectedThreadId);

  // Fetch messages for selected thread
  const {
    data: messages,
    isLoading: messagesLoading,
    error: messagesError,
  } = useQuery({
    queryKey: ['thread-queries', selectedThreadId],
    queryFn: () => chatAPI.getThreadQueries(selectedThreadId!, userId!),
    enabled: !!selectedThreadId,
  });

  // Fetch uploaded files for selected organization
  const {
    data: files,
    isLoading: filesLoading,
    error: filesError,
  } = useQuery({
    queryKey: ['files', userId, selectedOrgId],
    queryFn: () => fileAPI.getFiles(userId!, selectedOrgId!),
    enabled: !!userId && !!selectedOrgId,
  });

  return {
    // Organizations
    organizations,
    organizationsLoading,
    organizationsError,
    // Threads
    threads,
    threadsLoading,
    threadsError,
    currentThread,
    // Messages
    messages,
    messagesLoading,
    messagesError,
    // Files
    files,
    filesLoading,
    filesError,
  };
}
