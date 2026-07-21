import { useMemo } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import { Spinner, Button, Icon } from '../../design-system';
import { useAuditResults } from '../../api/hooks/useAuditResults';
import { useProject } from '../../api/hooks/useProjects';
import { useAuditDetailStore } from '../../stores/useAuditDetailStore';
import { formatDate } from '../../utils/format';
import { SEVERITY_CONFIG, SEVERITY_ORDER } from '../../utils/severity';
import ExecutiveSummary from './ExecutiveSummary';
import RiskOverview from './RiskOverview';
import DetailedFindings from './DetailedFindings';
import RecommendationsSummary from './RecommendationsSummary';
import FindingDetailDrawer from '../ProjectDetail/FindingDetailDrawer';
import styles from './LLMAuditPage.module.css';

function countBySeverity(findings: import('../../api/types').AuditFinding[]): Record<string, number> {
  const counts: Record<string, number> = {};
  for (const sev of SEVERITY_ORDER) {
    counts[sev] = 0;
  }
  for (const f of findings) {
    const key = f.severity.toLowerCase();
    if (counts[key] !== undefined) {
      counts[key]++;
    }
  }
  return counts;
}

export default function LLMAuditPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const projectId = id || '';

  const { data: project, isLoading: projectLoading } = useProject(projectId);
  const { data: findings, isLoading: findingsLoading } = useAuditResults(projectId);

  const { drawerOpen, selectedFinding, findingType, closeDrawer } = useAuditDetailStore();

  const isLoading = projectLoading || findingsLoading;
  const auditFindings = findings || [];
  const projectName = project?.name || '';
  const latestTimestamp = useMemo(() => {
    if (auditFindings.length === 0) return formatDate(new Date().toISOString());
    const timestamps = auditFindings
      .map((f) => new Date(f.created_at).getTime())
      .filter((t) => !isNaN(t));
    if (timestamps.length === 0) return formatDate(new Date().toISOString());
    const latest = new Date(Math.max(...timestamps));
    return formatDate(latest.toISOString());
  }, [auditFindings]);

  const counts = useMemo(() => countBySeverity(auditFindings), [auditFindings]);
  const total = auditFindings.length;

  const handleReaudit = () => {
    alert('重新审计功能即将上线，敬请期待。');
  };

  const handleExportReport = () => {
    navigate(`/projects/${projectId}/report`);
  };

  const summaryParts: string[] = [];
  for (const sev of SEVERITY_ORDER) {
    if (counts[sev] > 0) {
      const sevConfig = SEVERITY_CONFIG[sev];
      const prefix = sevConfig.label;
      summaryParts.push(`${prefix}${counts[sev]}`);
    }
  }

  if (isLoading) {
    return (
      <div className={styles.loading}>
        <Spinner size="lg" />
      </div>
    );
  }

  return (
    <div className={styles.page}>
      {/* Header */}
      <header className={styles.header}>
        <Link to={`/projects/${projectId}`} className={styles.backLink}>
          <Icon name="arrow-left" size={14} />
          <span>返回项目</span>
        </Link>
        <h1 className={styles.title}>LLM 智能合约安全审计报告</h1>
        <p className={styles.subtitle}>
          Project #{projectId}: {projectName}
        </p>
        <span className={styles.timestamp}>
          生成时间: {latestTimestamp}
        </span>
        <p className={styles.summaryLine}>
          共发现 {total} 个漏洞:
          {summaryParts.length > 0
            ? summaryParts.join(', ')
            : ' 无'}
        </p>
      </header>

      {/* Section 1: Executive Summary */}
      {project && (
        <ExecutiveSummary project={project} findings={auditFindings} />
      )}

      {/* Section 2: Risk Overview */}
      <RiskOverview findings={auditFindings} />

      {/* Section 3: Detailed Findings */}
      <DetailedFindings findings={auditFindings} />

      {/* Section 4: Recommendations */}
      <RecommendationsSummary findings={auditFindings} />

      {/* Footer Actions */}
      <div className={styles.footer}>
        <Button variant="brand" onClick={handleReaudit}>
          重新审计
        </Button>
        <Button variant="primary" onClick={handleExportReport}>
          导出为报告
        </Button>
      </div>

      {/* Detail Drawer */}
      {selectedFinding && (
        <FindingDetailDrawer
          open={drawerOpen}
          onClose={closeDrawer}
          finding={selectedFinding}
          findingType={findingType}
        />
      )}
    </div>
  );
}
