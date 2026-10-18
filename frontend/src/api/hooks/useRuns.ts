import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import client from '../client';
import type { AuditRunDetail, AuditRunSummary, CompareResult } from '../types';
import { queryKeys } from '../queryKeys';

const POLL_MS = 2500;

export function useRuns(projectId: string) {
  return useQuery<AuditRunSummary[]>({
    queryKey: queryKeys.runs.byProject(projectId),
    queryFn: async () => {
      const { data } = await client.get<AuditRunSummary[]>(`/v1/projects/${projectId}/runs`);
      return data;
    },
    // Keep polling while any run is still executing (no SSE dependency here).
    refetchInterval: (query) => {
      const runs = query.state.data;
      return runs?.some((r) => r.status === 'running') ? POLL_MS : false;
    },
  });
}

export function useRun(runId: string | null) {
  return useQuery<AuditRunDetail>({
    queryKey: queryKeys.runs.detail(runId ?? 'none'),
    queryFn: async () => {
      const { data } = await client.get<AuditRunDetail>(`/v1/runs/${runId}`);
      return data;
    },
    enabled: Boolean(runId),
  });
}

export function useCompareRuns(baseId: string | null, headId: string | null) {
  return useQuery<CompareResult>({
    queryKey: queryKeys.runs.compare(baseId ?? 'none', headId ?? 'none'),
    queryFn: async () => {
      const { data } = await client.get<CompareResult>(`/v1/runs/${baseId}/compare/${headId}`);
      return data;
    },
    enabled: Boolean(baseId && headId),
  });
}

export function useTriggerIncremental(projectId: string) {
  const queryClient = useQueryClient();
  return useMutation<{ status: string; task_id: string }, Error, { diff: string }>({
    mutationFn: async (payload) => {
      const { data } = await client.post(`/v1/projects/${projectId}/incremental-audit`, payload, {
        timeout: 60000,
      });
      return data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.runs.byProject(projectId) });
    },
  });
}
