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
      // page_size 显式拉全量（后端上限 100）：列表当前在本地做分页，
      // 不传则后端默认只回第一页 20 条，超出部分永远不可见
      const params = search
        ? { search, page_size: 100 }
        : { page_size: 100 };
      const { data } = await client.get<VulnerabilityPaginatedResponse>(
        '/v1/vulnerabilities',
        { params },
      );
      return data.items ?? [];
    },
    staleTime: STALE_TIME,
  });
}
