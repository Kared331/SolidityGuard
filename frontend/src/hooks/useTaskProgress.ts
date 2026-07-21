import { useState, useEffect, useRef } from 'react';

interface SSEEvent {
  type: string;
  project_id: number;
  [key: string]: unknown;
}

interface UseTaskProgressOptions {
  projectId: string;
  onEvent?: (event: SSEEvent) => void;
  enabled?: boolean;
}

interface UseTaskProgressResult {
  connected: boolean;
  lastEvent: SSEEvent | null;
  error: string | null;
}

function useTaskProgress({ projectId, onEvent, enabled = true }: UseTaskProgressOptions): UseTaskProgressResult {
  const [connected, setConnected] = useState(false);
  const [lastEvent, setLastEvent] = useState<SSEEvent | null>(null);
  const [error, setError] = useState<string | null>(null);
  const onEventRef = useRef(onEvent);
  onEventRef.current = onEvent;
  const esRef = useRef<EventSource | null>(null);

  useEffect(() => {
    if (!enabled || !projectId) return;
    let cancelled = false;

    const baseUrl = import.meta.env.VITE_API_BASE_URL || '/api';
    const sseUrl = `${baseUrl}/v1/projects/${projectId}/events`;

    // Delay SSE open to avoid ERR_ABORTED on fast route switches
    const timer = setTimeout(() => {
      if (cancelled) return;
      const es = new EventSource(sseUrl);
      esRef.current = es;
      es.onopen = () => {
        if (!cancelled) { setConnected(true); setError(null); }
      };
      es.onmessage = (event) => {
        if (cancelled) return;
        try {
          const data = JSON.parse(event.data) as SSEEvent;
          setLastEvent(data);
          onEventRef.current?.(data);
        } catch {
          /* ignore parse errors */
        }
      };
      es.onerror = () => {
        if (!cancelled) { setConnected(false); setError('SSE connection lost'); }
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
  }, [projectId, enabled]);

  return { connected, lastEvent, error };
}

export default useTaskProgress;
