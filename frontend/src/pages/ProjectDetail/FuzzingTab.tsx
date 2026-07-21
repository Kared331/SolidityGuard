import { useCallback, useMemo } from 'react';
import { Table, Tag } from '../../design-system';
import type { TableColumn } from '../../design-system';
import type { FuzzResult } from '../../api/types';
import { useAuditDetailStore } from '../../stores/useAuditDetailStore';
import styles from './FuzzingTab.module.css';

interface FuzzingTabProps {
  fuzzResults: FuzzResult[];
}

function failuresToStatus(failuresCount: number): { variant: 'success' | 'critical'; label: string } {
  if (failuresCount === 0) return { variant: 'success', label: '通过 (0 失败)' };
  return { variant: 'critical', label: `失败 (${failuresCount})` };
}

export default function FuzzingTab({ fuzzResults }: FuzzingTabProps) {
  const openDrawer = useAuditDetailStore((s) => s.openDrawer);

  const handleRowClick = useCallback(
    (record: FuzzResult) => {
      openDrawer(record as unknown as Record<string, unknown>, 'fuzz');
    },
    [openDrawer]
  );

  const columns: TableColumn<FuzzResult>[] = useMemo(
    () => [
      {
        key: 'id',
        title: '运行 ID',
        dataIndex: 'id',
        width: '80px',
      },
      {
        key: 'failures_count',
        title: '状态',
        dataIndex: 'failures_count',
        width: '140px',
        render: (value: number) => {
          const s = failuresToStatus(value);
          return (
            <Tag variant={s.variant} size="sm">
              {s.label}
            </Tag>
          );
        },
      },
      {
        key: 'raw_output',
        title: '输出',
        dataIndex: 'raw_output',
        render: (value: string | undefined) => (
          <span className={styles['ft-output']}>
            {value ? (value.length > 120 ? value.slice(0, 120) + '...' : value) : '-'}
          </span>
        ),
      },
    ],
    []
  );

  return (
    <div className={styles['ft-container']}>
      <Table
        columns={columns}
        dataSource={fuzzResults}
        emptyText="暂无 Fuzzing 测试结果"
        rowKey="id"
        onRowClick={handleRowClick}
      />
    </div>
  );
}
