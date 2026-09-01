import { useMemo } from 'react';

/**
 * P2-3: 审计长任务进度展示。
 *
 * 派生 hook——不创建独立 SSE 连接，而是从 useSSE 暴露的 lastEvent 中
 * 抽取 audit_progress 事件，输出最新进度快照。避免重复 EventSource 连接。
 *
 * 后端事件 schema（见 backend/app/llm/pipeline/stream.py::publish_progress）：
 *   { type: 'audit_progress', project_id, phase, current_file, current_function,
 *     total_functions, completed_functions, findings_so_far }
 */
export interface AuditProgress {
  phase: string;
  current_file?: string | null;
  current_function?: string | null;
  total_functions: number;
  completed_functions: number;
  findings_so_far: number;
}

interface SSEEvent {
  type: string;
  project_id: number;
  [key: string]: unknown;
}

interface UseTaskProgressOptions {
  lastEvent: SSEEvent | null;
}

interface UseTaskProgressResult {
  progress: AuditProgress | null;
  /** 0–100 整数百分比，无进度时为 null */
  percent: number | null;
}

const PHASE_LABELS: Record<string, string> = {
  parsing: '解析合约',
  summarizing: '生成摘要',
  embedding: '向量化',
  rag_retrieval: '检索漏洞知识',
  auditing: 'LLM 审计中',
  complete: '审计完成',
};

export function phaseLabel(phase: string): string {
  return PHASE_LABELS[phase] ?? phase;
}

function useTaskProgress({ lastEvent }: UseTaskProgressOptions): UseTaskProgressResult {
  const progress = useMemo<AuditProgress | null>(() => {
    if (!lastEvent || lastEvent.type !== 'audit_progress') return null;
    return {
      phase: String(lastEvent.phase ?? ''),
      current_file: (lastEvent.current_file as string | null | undefined) ?? null,
      current_function: (lastEvent.current_function as string | null | undefined) ?? null,
      total_functions: Number(lastEvent.total_functions ?? 0),
      completed_functions: Number(lastEvent.completed_functions ?? 0),
      findings_so_far: Number(lastEvent.findings_so_far ?? 0),
    };
  }, [lastEvent]);

  const percent = useMemo(() => {
    if (!progress) return null;
    if (progress.phase === 'complete') return 100;
    if (progress.total_functions <= 0) return null;
    const p = Math.round((progress.completed_functions / progress.total_functions) * 100);
    return Math.max(0, Math.min(100, p));
  }, [progress]);

  return { progress, percent };
}

export default useTaskProgress;
