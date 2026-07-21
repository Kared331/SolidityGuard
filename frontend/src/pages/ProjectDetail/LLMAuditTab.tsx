import { useCallback, useMemo } from 'react';
import { Link } from 'react-router-dom';
import { Table, Tag, Icon } from '../../design-system';
import type { TableColumn } from '../../design-system';
import type { AuditFinding } from '../../api/types';
import { getSeverityConfig, toSeverityTagVariant } from '../../utils/severity';
import { useAuditDetailStore } from '../../stores/useAuditDetailStore';
import styles from './LLMAuditTab.module.css';

interface LLMAuditTabProps {
  auditResults: AuditFinding[];
  projectId: string;
}


export default function LLMAuditTab({ auditResults, projectId }: LLMAuditTabProps) {
  const openDrawer = useAuditDetailStore((s) => s.openDrawer);

  const handleRowClick = useCallback(
    (record: AuditFinding) => {
      openDrawer(record as unknown as Record<string, unknown>, 'llm');
    },
    [openDrawer]
  );

  // Count by severity
  const severityCounts = useMemo(() => {
    const counts: Record<string, number> = {};
    auditResults.forEach((r) => {
      const s = r.severity.toLowerCase();
      counts[s] = (counts[s] || 0) + 1;
    });
    return counts;
  }, [auditResults]);

  const columns: TableColumn<AuditFinding>[] = useMemo(
    () => [
      {
        key: 'contract_name',
        title: '合约',
        dataIndex: 'contract_name',
        width: '180px',
      },
      {
        key: 'function_name',
        title: '函数',
        dataIndex: 'function_name',
        width: '180px',
        render: (value: string | undefined) => value || '-',
      },
      {
        key: 'vulnerability_description',
        title: '漏洞描述',
        dataIndex: 'vulnerability_description',
        render: (value: string) => (
          <span className={styles['llm-desc']}>
            {value.length > 80 ? value.slice(0, 80) + '...' : value}
          </span>
        ),
      },
      {
        key: 'severity',
        title: '严重程度',
        dataIndex: 'severity',
        width: '100px',
        render: (value: string) => {
          const config = getSeverityConfig(value);
          return (
            <Tag variant={toSeverityTagVariant(value)} size="sm">
              {config.label}
            </Tag>
          );
        },
      },
    ],
    []
  );

  return (
    <div className={styles['llm-container']}>
      {/* Severity summary */}
      {auditResults.length > 0 && (
        <div className={styles['llm-summary']}>
          <span className="ds-text-sm ds-text-secondary">Severity 分布:</span>
          <div className={styles['llm-summary-tags']}>
            {severityCounts['critical'] && (
              <Tag variant="critical" size="sm">
                Critical x{severityCounts['critical']}
              </Tag>
            )}
            {severityCounts['high'] && (
              <Tag variant="high" size="sm">
                High x{severityCounts['high']}
              </Tag>
            )}
            {severityCounts['medium'] && (
              <Tag variant="medium" size="sm">
                Medium x{severityCounts['medium']}
              </Tag>
            )}
            {severityCounts['low'] && (
              <Tag variant="low" size="sm">
                Low x{severityCounts['low']}
              </Tag>
            )}
            {severityCounts['informational'] && (
              <Tag variant="info" size="sm">
                Info x{severityCounts['informational']}
              </Tag>
            )}
          </div>
        </div>
      )}

      <Table
        columns={columns}
        dataSource={auditResults}
        emptyText="暂无 LLM 审计结果"
        rowKey="id"
        onRowClick={handleRowClick}
      />

      {auditResults.length > 0 && (
        <div className={styles['llm-footer']}>
          <Link
            to={`/projects/${projectId}/llm-audit`}
            className={styles['llm-report-link']}
          >
            <Icon name="external-link" size={14} />
            查看完整报告
          </Link>
        </div>
      )}
    </div>
  );
}
