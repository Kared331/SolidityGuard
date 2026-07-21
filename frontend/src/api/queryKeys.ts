export const queryKeys = {
  projects: {
    all: ['projects'] as const,
    detail: (id: string) => ['projects', 'detail', id] as const,
  },
  files: {
    byProject: (projectId: string) => ['files', 'byProject', projectId] as const,
  },
  analyses: {
    all: ['analyses'] as const,
    byProject: (projectId: string) => ['analyses', 'byProject', projectId] as const,
  },
  fuzzResults: {
    all: ['fuzzResults'] as const,
    byProject: (projectId: string) => ['fuzzResults', 'byProject', projectId] as const,
  },
  auditResults: {
    all: ['auditResults'] as const,
    byProject: (projectId: string) => ['auditResults', 'byProject', projectId] as const,
  },
  reports: {
    all: ['reports'] as const,
    byProject: (projectId: string) => ['reports', 'byProject', projectId] as const,
  },
  vulnerabilities: {
    all: ['vulnerabilities'] as const,
    search: (query: string) => ['vulnerabilities', 'search', query] as const,
  },
};
