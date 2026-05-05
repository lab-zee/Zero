import { useMutation, useQueryClient } from '@tanstack/react-query';
import { useSearchParams } from 'react-router-dom';
import { useToast } from '@chakra-ui/react';
import { chatAPI, fileAPI } from '../../../services/api';

interface UseChatMutationsOptions {
  userId: number | undefined;
  selectedOrgId: number | null;
  selectedThreadId: number | null;
  threadToDelete: number | null;
  setThreadToDelete: (id: number | null) => void;
  onDeleteDialogClose: () => void;
}

export function useChatMutations({
  userId,
  selectedOrgId,
  selectedThreadId,
  threadToDelete,
  setThreadToDelete,
  onDeleteDialogClose,
}: UseChatMutationsOptions) {
  const queryClient = useQueryClient();
  const toast = useToast();
  const [searchParams, setSearchParams] = useSearchParams();

  // Mutation to update thread preferences
  const updateThreadMutation = useMutation({
    mutationFn: (update: { title?: string; thread_metadata?: { budget_focus?: number; response_length?: number; creativity?: number } }) =>
      chatAPI.updateThread(selectedThreadId!, update, userId!),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['threads', userId, selectedOrgId] });
      queryClient.invalidateQueries({ queryKey: ['organizationsWithStats', userId] });
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

  // Create thread mutation
  const createThreadMutation = useMutation({
    mutationFn: (title?: string) =>
      chatAPI.createThread({ organization_id: selectedOrgId!, title }, userId!),
    onSuccess: (newThread) => {
      queryClient.invalidateQueries({ queryKey: ['threads', userId, selectedOrgId] });
      queryClient.invalidateQueries({ queryKey: ['organizationsWithStats', userId] });
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

  // Delete thread mutation
  const deleteThreadMutation = useMutation({
    mutationFn: (threadId: number) => chatAPI.deleteThread(threadId, userId!),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['threads', userId, selectedOrgId] });
      queryClient.invalidateQueries({ queryKey: ['organizationsWithStats', userId] });
      if (selectedThreadId === threadToDelete) {
        // Remove thread from URL params
        const params = new URLSearchParams(searchParams);
        params.delete('thread');
        setSearchParams(params, { replace: true });
      }
      setThreadToDelete(null);
      onDeleteDialogClose();
      toast({
        title: 'Thread deleted',
        status: 'success',
        duration: 2000,
        isClosable: true,
      });
    },
    onError: (error: any) => {
      toast({
        title: 'Error',
        description: error.response?.data?.detail || 'Failed to delete thread',
        status: 'error',
        duration: 3000,
        isClosable: true,
      });
      setThreadToDelete(null);
      onDeleteDialogClose();
    },
  });

  // Upload file mutation
  const uploadFileMutation = useMutation({
    mutationFn: (file: File) => fileAPI.uploadFile(file, selectedOrgId!, userId!),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['files', userId, selectedOrgId] });
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

  // Handle delete confirmation
  const handleDeleteConfirm = () => {
    if (threadToDelete) {
      deleteThreadMutation.mutate(threadToDelete);
    }
  };

  return {
    updateThreadMutation,
    createThreadMutation,
    deleteThreadMutation,
    uploadFileMutation,
    handleDeleteConfirm,
  };
}
