import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import client from '../client';
import type { AuditFinding } from '../types';
import { queryKeys } from '../queryKeys';

const STALE_TIME = 30_000;

export function useAuditResults(projectId: string) {
  return useQuery<AuditFinding[]>({
    queryKey: queryKeys.auditResults.byProject(projectId),
    queryFn: async () => {
      const { data } = await client.get<AuditFinding[]>(
        `/v1/projects/${projectId}/llm-audit-results`,
      );
      return data;
    },
    staleTime: STALE_TIME,
  });
}

export function useTriggerLLMAudit() {
  const queryClient = useQueryClient();

  return useMutation<unknown, Error, string>({
    mutationFn: async (projectId: string) => {
      const { data } = await client.post(
        `/v1/projects/${projectId}/llm-audit`,
      );
      return data;
    },
    onSuccess: (_data, projectId) => {
      queryClient.invalidateQueries({
        queryKey: queryKeys.auditResults.byProject(projectId),
      });
    },
  });
}
