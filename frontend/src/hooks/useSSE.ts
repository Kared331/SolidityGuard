import { useState, useEffect, useRef, useCallback } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import { useAppStore } from '../stores/useAppStore';
import { useToastStore, type ToastType } from '../stores/useToastStore';
import { queryKeys } from '../api/queryKeys';

interface SSEEvent {
  type: string;
  project_id: number;
  count?: number;
  [key: string]: unknown;
}

interface UseSSEOptions {
  projectId: string;
  enabled?: boolean;
}

/** Maps backend SSE event types to query invalidation + user-facing toast labels */
const EVENT_CONFIG: Record<string, {
  queryKeyFn: (pid: string) => readonly unknown[];
  label: string;
  toast: ToastType;
}> = {
  new_detections: {
    queryKeyFn: (pid) => queryKeys.analyses.byProject(pid),
    label: 'Slither 分析',
    toast: 'info',
  },
  new_fuzz_results: {
    queryKeyFn: (pid) => queryKeys.fuzzResults.byProject(pid),
    label: 'Fuzzing 测试',
    toast: 'success',
  },
  new_audit_results: {
    queryKeyFn: (pid) => queryKeys.auditResults.byProject(pid),
    label: 'LLM 审计',
    toast: 'info',
  },
  new_report: {
    queryKeyFn: (pid) => queryKeys.reports.byProject(pid),
    label: '报告生成',
    toast: 'success',
  },
};

export function useSSE({ projectId, enabled = true }: UseSSEOptions) {
  const queryClient = useQueryClient();
  const setSseConnected = useAppStore((s) => s.setSseConnected);
  const addToast = useToastStore((s) => s.addToast);
  const [connected, setConnected] = useState(false);
  const [lastEvent, setLastEvent] = useState<SSEEvent | null>(null);
  const [error, setError] = useState<string | null>(null);
  const esRef = useRef<EventSource | null>(null);

  const handleEvent = useCallback(
    (data: SSEEvent) => {
      const pid = String(data.project_id);
      const config = EVENT_CONFIG[data.type];

      if (config) {
        queryClient.invalidateQueries({ queryKey: config.queryKeyFn(pid) });

        // Show notification toast
        const count = typeof data.count === 'number' ? data.count : 0;
        const countText = count > 0 ? ` (${count} 条)` : '';
        addToast({
          type: config.toast,
          message: `${config.label}完成${countText}`,
          duration: 4000,
        });
      }

      // Always invalidate project detail to refresh status
      queryClient.invalidateQueries({ queryKey: queryKeys.projects.detail(pid) });
    },
    [queryClient, addToast],
  );

  useEffect(() => {
    if (!enabled || !projectId) return;
    let cancelled = false;

    const baseUrl = import.meta.env.VITE_API_BASE_URL || '/api';
    const sseUrl = `${baseUrl}/v1/projects/${projectId}/events`;

    const timer = setTimeout(() => {
      if (cancelled) return;
      const es = new EventSource(sseUrl);
      esRef.current = es;

      es.onopen = () => {
        if (!cancelled) {
          setConnected(true);
          setError(null);
          setSseConnected(true);
        }
      };

      es.onmessage = (event) => {
        if (cancelled) return;
        try {
          const data = JSON.parse(event.data) as SSEEvent;
          setLastEvent(data);
          handleEvent(data);
        } catch {
          /* ignore parse errors */
        }
      };

      es.onerror = () => {
        if (!cancelled) {
          setConnected(false);
          setError('SSE connection lost');
          setSseConnected(false);
        }
        es.close();
        esRef.current = null;
      };
    }, 200);

    return () => {
      cancelled = true;
      clearTimeout(timer);
      if (esRef.current) {
        esRef.current.close();
        esRef.current = null;
      }
    };
  }, [projectId, enabled, handleEvent, setSseConnected]);

  return { connected, lastEvent, error };
}
