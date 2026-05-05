import { useQuery } from '@tanstack/react-query';
import { agentAPI, type ToolInfo } from '../services/api';

/**
 * Hook for fetching and caching available tools from the backend.
 * Uses React Query for automatic caching and background refetching.
 */
export const useTools = () => {
  return useQuery({
    queryKey: ['tools'],
    queryFn: agentAPI.getTools,
    staleTime: 5 * 60 * 1000, // 5 minutes - tools don't change frequently
    gcTime: 30 * 60 * 1000, // 30 minutes cache time (formerly cacheTime)
    refetchOnWindowFocus: false, // Don't refetch when window regains focus
  });
};

export type { ToolInfo };
