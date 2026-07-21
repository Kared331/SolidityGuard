import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import client from '../client';
import type { ReportResponse } from '../types';
import { queryKeys } from '../queryKeys';

const STALE_TIME = 30_000;

export function useReports(projectId: string) {
  return useQuery<ReportResponse[]>({
    queryKey: queryKeys.reports.byProject(projectId),
    queryFn: async () => {
      const { data } = await client.get<ReportResponse[]>(
        `/v1/projects/${projectId}/reports`,
      );
      return data;
    },
    staleTime: STALE_TIME,
  });
}

export function useGenerateReport() {
  const queryClient = useQueryClient();

  return useMutation<
    ReportResponse,
    Error,
    { projectId: string; format: 'html' | 'pdf' | 'word' }
  >({
    mutationFn: async ({ projectId, format }) => {
      const { data } = await client.post<ReportResponse>(
        `/v1/projects/${projectId}/report`,
        { format },
      );
      return data;
    },
    onSuccess: (_data, { projectId }) => {
      queryClient.invalidateQueries({
        queryKey: queryKeys.reports.byProject(projectId),
      });
    },
  });
}
