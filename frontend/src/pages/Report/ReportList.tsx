import { Table, Button, Icon, Tag } from '../../design-system';
import type { TableColumn } from '../../design-system';
import type { ReportResponse } from '../../api/types';
import { formatDate } from '../../utils/format';
import styles from './ReportList.module.css';

interface Props {
  reports: ReportResponse[];
  isLoading: boolean;
  projectId: string;
}

export default function ReportList({ reports, isLoading, projectId }: Props) {
  const API_BASE = import.meta.env.VITE_API_BASE_URL || '/api';

  const columns: TableColumn<ReportResponse>[] = [
    {
      key: 'name',
      title: '报告名称',
      dataIndex: 'id',
      render: (_value, record: ReportResponse) => {
        const date = formatDate(record.created_at);
        return `Audit Report #${projectId} - ${date}`;
      },
    },
    {
      key: 'format',
      title: '格式',
      dataIndex: 'format',
      render: (value: string) => (
        <Tag variant="neutral" size="sm">
          {value.toUpperCase()}
        </Tag>
      ),
      width: '80px',
    },
    {
      key: 'created_at',
      title: '生成时间',
      dataIndex: 'created_at',
      render: (value: string) => formatDate(value),
      width: '180px',
    },
    {
      key: 'actions',
      title: '操作',
      dataIndex: 'id',
      render: (_value, record: ReportResponse) => (
        <Button
          variant="ghost"
          size="sm"
          onClick={(e) => {
            e.stopPropagation();
            window.open(`${API_BASE}/v1/reports/${record.id}/download`, '_blank');
          }}
        >
          <Icon name="download" size={14} />
          下载
        </Button>
      ),
      width: '100px',
    },
  ];

  return (
    <div className={styles['report-list']}>
      <Table
        columns={columns}
        dataSource={reports}
        loading={isLoading}
        emptyText="暂无历史报告"
        rowKey="id"
      />
    </div>
  );
}
