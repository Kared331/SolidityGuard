import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import client from '../client';
import type { FuzzResult } from '../types';
import { queryKeys } from '../queryKeys';

const STALE_TIME = 30_000;

export function useFuzzResults(projectId: string) {
  return useQuery<FuzzResult[]>({
    queryKey: queryKeys.fuzzResults.byProject(projectId),
    queryFn: async () => {
      const { data } = await client.get<FuzzResult[]>(
        `/v1/projects/${projectId}/fuzz-results`,
      );
      return data;
    },
    staleTime: STALE_TIME,
  });
}

export function useTriggerFuzz() {
  const queryClient = useQueryClient();

  return useMutation<unknown, Error, string>({
    mutationFn: async (projectId: string) => {
      const { data } = await client.post(
        `/v1/projects/${projectId}/fuzz`,
      );
      return data;
    },
    onSuccess: (_data, projectId) => {
      queryClient.invalidateQueries({
        queryKey: queryKeys.fuzzResults.byProject(projectId),
      });
    },
  });
}
