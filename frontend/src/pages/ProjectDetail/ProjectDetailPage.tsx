import { useState, useEffect, useCallback } from 'react';
import { useParams, Link } from 'react-router-dom';
import { Tag, Icon, Tabs } from '../../design-system';
import type { TabItem } from '../../design-system';
import { useProject } from '../../api/hooks/useProjects';
import { useAnalyses } from '../../api/hooks/useAnalyses';
import { useFuzzResults } from '../../api/hooks/useFuzzResults';
import { useAuditResults } from '../../api/hooks/useAuditResults';
import { useSSE } from '../../hooks/useSSE';
import useTaskProgress, { phaseLabel } from '../../hooks/useTaskProgress';
import { useAppStore } from '../../stores/useAppStore';
import { useAuditDetailStore } from '../../stores/useAuditDetailStore';
import OperationBar from './OperationBar';
import FilesPanel from './FilesPanel';
import AnalysisTab from './AnalysisTab';
import FuzzingTab from './FuzzingTab';
import LLMAuditTab from './LLMAuditTab';
import FindingDetailDrawer from './FindingDetailDrawer';
import styles from './ProjectDetailPage.module.css';

const STATUS_TAG_MAP: Record<string, { variant: 'success' | 'info' | 'critical' | 'neutral'; label: string }> = {
  ready: { variant: 'success', label: '就绪' },
  analyzing: { variant: 'info', label: '分析中' },
  running: { variant: 'info', label: '运行中' },
  failed: { variant: 'critical', label: '失败' },
  completed: { variant: 'success', label: '完成' },
};

function getStatusTagConfig(status: string) {
  return STATUS_TAG_MAP[status] ?? { variant: 'neutral' as const, label: status };
}

export default function ProjectDetailPage() {
  const { id } = useParams<{ id: string }>();
  const projectId = id ?? '';

  const { data: project, isLoading: projectLoading } = useProject(projectId);
  const { data: analyses = [] } = useAnalyses(projectId);
  const { data: fuzzResults = [] } = useFuzzResults(projectId);
  const { data: auditResults = [] } = useAuditResults(projectId);
  const { lastEvent } = useSSE({ projectId });
  // P2-3: 从 SSE audit_progress 事件派生进度快照（无独立连接）
  const { progress, percent } = useTaskProgress({ lastEvent });
  const setCurrentProject = useAppStore((s) => s.setCurrentProject);
  const { drawerOpen, selectedFinding, findingType, closeDrawer } = useAuditDetailStore();

  const [activeTab, setActiveTab] = useState('slither');

  useEffect(() => {
    if (project) {
      setCurrentProject(project.id, project.name);
    }
    return () => {
      setCurrentProject(null, '');
    };
  }, [project, setCurrentProject]);

  const handleTabChange = useCallback((key: string) => {
    setActiveTab(key);
  }, []);

  if (projectLoading) {
    return (
      <div className={styles['pd-loading']}>
        <div className={styles['pd-loading-spinner']} />
        <span className="ds-text-secondary">加载项目详情...</span>
      </div>
    );
  }

  if (!project) {
    return (
      <div className={styles['pd-empty']}>
        <Icon name="alert-circle" size={48} />
        <span className="ds-text-secondary">项目未找到</span>
        <Link to="/dashboard" style={{ color: 'var(--ds-color-text-link)' }}>
          返回项目列表
        </Link>
      </div>
    );
  }

  const statusConfig = getStatusTagConfig(project.status);

  // Analyses now comes as flat DetectionResponse[] directly from backend
  const allDetections = analyses;

  const tabItems: TabItem[] = [
    {
      key: 'slither',
      label: allDetections.length > 0
        ? `Slither 分析 (${allDetections.length})`
        : 'Slither 分析',
      content: <AnalysisTab detections={allDetections} />,
    },
    {
      key: 'fuzz',
      label: fuzzResults.length > 0
        ? `Fuzzing 测试 (${fuzzResults.length})`
        : 'Fuzzing 测试',
      content: <FuzzingTab fuzzResults={fuzzResults} />,
    },
    {
      key: 'llm',
      label: auditResults.length > 0
        ? `LLM 审计 (${auditResults.length})`
        : 'LLM 审计',
      content: <LLMAuditTab auditResults={auditResults} projectId={projectId} />,
    },
  ];

  return (
    <div className={styles['pd-page']}>
      {/* Header */}
      <div className={styles['pd-header']}>
        <Link to="/dashboard" className={styles['pd-back-link']}>
          <Icon name="arrow-left" size={16} />
          返回
        </Link>
        <div className={styles['pd-header-title']}>
          <h1 className="ds-text-xl" style={{ margin: 0 }}>
            Project #{project.id}: {project.name}
          </h1>
          <Tag variant={statusConfig.variant} size="sm">
            {statusConfig.label}
          </Tag>
        </div>
      </div>

      {/* Operation Bar */}
      <OperationBar projectId={projectId} />

      {/* P2-3: 长任务实时进度条（仅 audit_progress 事件到达后渲染） */}
      {progress && (
        <div className={styles['pd-progress']} role="status" aria-live="polite">
          <div className={styles['pd-progress-head']}>
            <span className={styles['pd-progress-phase']}>
              {phaseLabel(progress.phase)}
            </span>
            <span className={styles['pd-progress-count']}>
              {progress.completed_functions}/{progress.total_functions} 函数
              {progress.findings_so_far > 0 && ` · ${progress.findings_so_far} 条发现`}
            </span>
          </div>
          <div className={styles['pd-progress-track']}>
            <div
              className={styles['pd-progress-bar']}
              style={{ width: percent != null ? `${percent}%` : '100%' }}
              data-indeterminate={percent == null ? 'true' : 'false'}
            />
          </div>
          {progress.current_function && (
            <div className={styles['pd-progress-detail']}>
              当前: {progress.current_file ?? ''}::{progress.current_function}
            </div>
          )}
        </div>
      )}

      {/* Files Panel */}
      <FilesPanel projectId={projectId} />

      {/* Tabs */}
      <div className={styles['pd-tabs-wrapper']}>
        <Tabs
          items={tabItems}
          activeKey={activeTab}
          onChange={handleTabChange}
        />
      </div>

      {/* Shared Detail Drawer */}
      <FindingDetailDrawer
        open={drawerOpen}
        onClose={closeDrawer}
        finding={selectedFinding}
        findingType={findingType}
      />
    </div>
  );
}
