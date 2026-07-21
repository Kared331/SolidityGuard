import { useCallback, useMemo } from 'react';
import { Table, Tag } from '../../design-system';
import type { TableColumn } from '../../design-system';
import type { SlitherDetection } from '../../api/types';
import { useAuditDetailStore } from '../../stores/useAuditDetailStore';
import styles from './AnalysisTab.module.css';

interface AnalysisTabProps {
  detections: SlitherDetection[];
}

function impactToSeverityLabel(impact?: string): string {
  const map: Record<string, string> = {
    High: '高危',
    Medium: '中危',
    Low: '低危',
    Informational: '信息',
    Optimization: '优化',
  };
  return impact ? (map[impact] ?? impact) : '未知';
}

function impactToTagVariant(impact?: string): 'critical' | 'high' | 'medium' | 'low' | 'info' | 'neutral' {
  const map: Record<string, 'critical' | 'high' | 'medium' | 'low' | 'info' | 'neutral'> = {
    High: 'high',
    Medium: 'medium',
    Low: 'low',
    Informational: 'info',
    Optimization: 'neutral',
  };
  return impact ? (map[impact] ?? 'neutral') : 'neutral';
}

export default function AnalysisTab({ detections }: AnalysisTabProps) {
  const openDrawer = useAuditDetailStore((s) => s.openDrawer);

  const handleRowClick = useCallback(
    (record: SlitherDetection) => {
      openDrawer(record as unknown as Record<string, unknown>, 'slither');
    },
    [openDrawer]
  );

  const columns: TableColumn<SlitherDetection>[] = useMemo(
    () => [
      {
        key: 'check_name',
        title: '检测项',
        dataIndex: 'check_name',
      },
      {
        key: 'impact',
        title: '严重程度',
        dataIndex: 'impact',
        width: '100px',
        render: (value: string | undefined) => (
          <Tag variant={impactToTagVariant(value)} size="sm">
            {impactToSeverityLabel(value)}
          </Tag>
        ),
      },
      {
        key: 'description',
        title: '描述',
        dataIndex: 'description',
        render: (value: string) => (
          <span>{value.length > 100 ? value.slice(0, 100) + '...' : value}</span>
        ),
      },
      {
        key: 'confidence',
        title: '置信度',
        dataIndex: 'confidence',
        width: '80px',
      },
    ],
    []
  );

  return (
    <div className={styles['at-container']}>
      <Table
        columns={columns}
        dataSource={detections}
        emptyText="暂无 Slither 分析结果"
        rowKey="id"
        onRowClick={handleRowClick}
      />
    </div>
  );
}
