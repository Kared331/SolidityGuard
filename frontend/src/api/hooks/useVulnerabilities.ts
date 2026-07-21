import { useQuery } from '@tanstack/react-query';
import client from '../client';
import type { VulnerabilityEntry } from '../types';
import { queryKeys } from '../queryKeys';

const STALE_TIME = 30_000;

interface VulnerabilityPaginatedResponse {
  total: number;
  page: number;
  page_size: number;
  items: VulnerabilityEntry[];
}

export function useVulnerabilities(search?: string) {
  return useQuery<VulnerabilityEntry[]>({
    queryKey: search
      ? queryKeys.vulnerabilities.search(search)
      : queryKeys.vulnerabilities.all,
    queryFn: async () => {
      const params = search ? { search } : {};
      const { data } = await client.get<VulnerabilityPaginatedResponse>(
        '/v1/vulnerabilities',
        { params },
      );
      return data.items ?? [];
    },
    staleTime: STALE_TIME,
  });
}
