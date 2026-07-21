import { useState, useCallback } from 'react';
import { Card, Table, Icon, Tag } from '../../design-system';
import type { TableColumn } from '../../design-system';
import { useQuery } from '@tanstack/react-query';
import client from '../../api/client';
import type { ProjectFile } from '../../api/types';
import { queryKeys } from '../../api/queryKeys';
import styles from './FilesPanel.module.css';

interface FilesPanelProps {
  projectId: string;
}

function useFiles(projectId: string) {
  return useQuery<ProjectFile[]>({
    queryKey: queryKeys.files.byProject(projectId),
    queryFn: async () => {
      const { data } = await client.get<ProjectFile[]>(
        `/v1/projects/${projectId}/files`
      );
      return data;
    },
    staleTime: 30_000,
  });
}

const FILE_STATUS_MAP: Record<string, { variant: 'success' | 'neutral' | 'critical'; label: string }> = {
  ready: { variant: 'success', label: '就绪' },
  pending: { variant: 'neutral', label: '等待中' },
  analyzing: { variant: 'neutral', label: '分析中' },
  failed: { variant: 'critical', label: '失败' },
};

function getFileStatusConfig(status: string) {
  return FILE_STATUS_MAP[status] ?? { variant: 'neutral' as const, label: status };
}

export default function FilesPanel({ projectId }: FilesPanelProps) {
  const [collapsed, setCollapsed] = useState(false);
  const { data: files = [], isLoading } = useFiles(projectId);

  const toggleCollapsed = useCallback(() => {
    setCollapsed((prev) => !prev);
  }, []);

  const columns: TableColumn<ProjectFile>[] = [
    {
      key: 'file_path',
      title: '文件名',
      dataIndex: 'file_path',
      render: (value: string) => {
        // Extract just the filename from the path
        const filename = value.includes('/') ? value.split('/').pop()! : value;
        return (
          <span className={styles['fp-file-name']}>
            <Icon name="file" size={14} />
            {filename}
          </span>
        );
      },
    },
    {
      key: 'status',
      title: '状态',
      dataIndex: 'status',
      width: '120px',
      render: (value: string) => {
        const cfg = getFileStatusConfig(value);
        return (
          <Tag variant={cfg.variant} size="sm">
            {cfg.label}
          </Tag>
        );
      },
    },
  ];

  return (
    <Card
      title="项目文件"
      extra={
        <button
          className={styles['fp-toggle-btn']}
          onClick={toggleCollapsed}
          type="button"
        >
          <Icon
            name={collapsed ? 'chevron-right' : 'chevron-down'}
            size={12}
          />
          {collapsed ? '展开' : '收起'}
        </button>
      }
      padding="compact"
    >
      <span className={styles['fp-file-count']}>
        {files.length} 个文件
      </span>
      {!collapsed && (
        <div style={{ marginTop: 'var(--ds-space-3)' }}>
          <Table
            columns={columns}
            dataSource={files}
            loading={isLoading}
            emptyText="暂无文件"
            rowKey="id"
          />
        </div>
      )}
    </Card>
  );
}
