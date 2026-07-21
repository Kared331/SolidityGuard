import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import client from '../client';
import type { ProjectResponse } from '../types';
import { queryKeys } from '../queryKeys';

const STALE_TIME = 30_000; // 30 seconds for lists

export function useProjects() {
  return useQuery<ProjectResponse[]>({
    queryKey: queryKeys.projects.all,
    queryFn: async () => {
      const { data } = await client.get<ProjectResponse[]>('/v1/projects');
      return data;
    },
    staleTime: STALE_TIME,
  });
}

export function useProject(id: string) {
  return useQuery<ProjectResponse>({
    queryKey: queryKeys.projects.detail(id),
    queryFn: async () => {
      const { data } = await client.get<ProjectResponse>(`/v1/projects/${id}`);
      return data;
    },
  });
}

export function useCreateProject() {
  const queryClient = useQueryClient();

  return useMutation<ProjectResponse, Error, FormData>({
    mutationFn: async (formData: FormData) => {
      const { data } = await client.post<ProjectResponse>(
        '/v1/projects',
        formData,
      );
      return data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.projects.all });
    },
  });
}
