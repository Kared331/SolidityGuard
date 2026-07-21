import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import client from '../client';
import type { SlitherDetection } from '../types';
import { queryKeys } from '../queryKeys';

const STALE_TIME = 30_000;

export function useAnalyses(projectId: string) {
  return useQuery<SlitherDetection[]>({
    queryKey: queryKeys.analyses.byProject(projectId),
    queryFn: async () => {
      const { data } = await client.get<SlitherDetection[]>(
        `/v1/projects/${projectId}/analyses`,
      );
      return data;
    },
    staleTime: STALE_TIME,
  });
}

export function useTriggerAnalysis() {
  const queryClient = useQueryClient();

  return useMutation<unknown, Error, string>({
    mutationFn: async (projectId: string) => {
      const { data } = await client.post(
        `/v1/projects/${projectId}/analyze`,
      );
      return data;
    },
    onSuccess: (_data, projectId) => {
      queryClient.invalidateQueries({
        queryKey: queryKeys.analyses.byProject(projectId),
      });
    },
  });
}
