import React, { useState, useMemo, useCallback, useRef, useEffect } from 'react';
import { Input, Select, Table, Icon, Button } from '../../design-system';
import type { TableColumn, PaginationConfig, SelectOption } from '../../design-system';
import { useVulnerabilities, useTriggerKnowledgeSync } from '../../api/hooks/useVulnerabilities';
import type { VulnerabilityEntry } from '../../api/types';
import { getSeverityConfig, toSeverityTagVariant } from '../../utils/severity';
import { DEFAULT_PAGE_SIZE } from '../../utils/constants';
import { useToastStore } from '../../stores/useToastStore';
import VulnerabilityDetailDrawer from './VulnerabilityDetailDrawer';
import Tag from '../../design-system/components/Tag';
import styles from './VulnerabilitiesPage.module.css';

const SEVERITY_OPTIONS: SelectOption[] = [
  { label: '全部', value: 'all' },
  { label: 'Critical', value: 'critical' },
  { label: 'High', value: 'high' },
  { label: 'Medium', value: 'medium' },
  { label: 'Low', value: 'low' },
  { label: 'Info', value: 'informational' },
];


export default function VulnerabilitiesPage() {
  const [searchTerm, setSearchTerm] = useState('');
  const [debouncedSearch, setDebouncedSearch] = useState('');
  const [severityFilter, setSeverityFilter] = useState('all');
  const [selectedVuln, setSelectedVuln] = useState<VulnerabilityEntry | null>(null);
  const [currentPage, setCurrentPage] = useState(1);

  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const addToast = useToastStore((s) => s.addToast);
  const syncMutation = useTriggerKnowledgeSync();

  const handleSync = useCallback(() => {
    if (syncMutation.isPending) return;
    syncMutation.mutate(undefined, {
      onSuccess: () =>
        addToast({
          type: 'success',
          message: '知识库同步任务已启动，同步完成后刷新可见更新。',
          duration: 4000,
        }),
      onError: () =>
        addToast({
          type: 'error',
          message: '同步触发失败，请稍后重试。',
          duration: 4000,
        }),
    });
  }, [syncMutation, addToast]);

  const handleSearchChange = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const value = e.target.value;
    setSearchTerm(value);
    if (timerRef.current) clearTimeout(timerRef.current);
    timerRef.current = setTimeout(() => {
      setDebouncedSearch(value);
      setCurrentPage(1);
    }, 300);
  }, []);

  useEffect(() => {
    return () => {
      if (timerRef.current) clearTimeout(timerRef.current);
    };
  }, []);

  const { data: vulnerabilities = [], isLoading } = useVulnerabilities(
    debouncedSearch || undefined
  );

  const filteredData = useMemo(() => {
    if (severityFilter === 'all') return vulnerabilities;
    return vulnerabilities.filter(
      (v) => (v.severity ?? '').toLowerCase() === severityFilter
    );
  }, [vulnerabilities, severityFilter]);

  const totalPages = filteredData.length > 0
    ? Math.ceil(filteredData.length / DEFAULT_PAGE_SIZE)
    : 0;

  const paginatedData = useMemo(() => {
    const start = (currentPage - 1) * DEFAULT_PAGE_SIZE;
    return filteredData.slice(start, start + DEFAULT_PAGE_SIZE);
  }, [filteredData, currentPage]);

  const handleSeverityChange = useCallback((value: string) => {
    setSeverityFilter(value);
    setCurrentPage(1);
  }, []);

  const pagination: PaginationConfig | undefined =
    totalPages > 1
      ? {
          current: currentPage,
          pageSize: DEFAULT_PAGE_SIZE,
          total: filteredData.length,
          onChange: (page) => setCurrentPage(page),
        }
      : undefined;

  const columns: TableColumn<VulnerabilityEntry>[] = useMemo(
    () => [
      {
        key: 'swc_id',
        title: 'SWC ID',
        dataIndex: 'swc_id',
        render: (value: string) => (
          <span className={styles['vuln-swc-id']}>{value}</span>
        ),
        width: '120px',
      },
      {
        key: 'title',
        title: 'Title',
        dataIndex: 'title',
        render: (value: string) => (
          <span className={styles['vuln-title']}>{value}</span>
        ),
      },
      {
        key: 'severity',
        title: 'Severity',
        dataIndex: 'severity',
        render: (value: string) => {
          const config = getSeverityConfig(value);
          return (
            <Tag variant={toSeverityTagVariant(value)} size="sm">
              {config.label}
            </Tag>
          );
        },
        width: '100px',
      },
      {
        key: 'code_example',
        title: 'Code Example',
        dataIndex: 'code_example',
        render: (value: string | undefined) => {
          if (value) {
            return (
              <Icon
                name="check"
                size={16}
                color="var(--ds-color-info)"
              />
            );
          }
          return <span className={styles['vuln-no-example']}>-</span>;
        },
        width: '120px',
      },
    ],
    []
  );

  return (
    <div className={styles['vuln-page']}>
      <h1
        className="ds-text-2xl"
        style={{ marginBottom: 'var(--ds-space-6)' }}
      >
        漏洞知识库 (SWC Registry)
      </h1>

      <div className={styles['vuln-toolbar']}>
        <Input
          type="search"
          placeholder="搜索漏洞..."
          value={searchTerm}
          onChange={handleSearchChange}
          prefix={
            <Icon
              name="search"
              size={16}
              color="var(--ds-color-icon-tertiary)"
            />
          }
        />
        <Select
          options={SEVERITY_OPTIONS}
          value={severityFilter}
          onChange={handleSeverityChange}
        />
        <Button
          variant="secondary"
          onClick={handleSync}
          loading={syncMutation.isPending}
          disabled={syncMutation.isPending}
        >
          同步数据
        </Button>
      </div>

      <Table
        columns={columns}
        dataSource={paginatedData}
        loading={isLoading}
        emptyText="未找到匹配的漏洞"
        rowKey="id"
        onRowClick={(record) => setSelectedVuln(record)}
        pagination={pagination}
      />

      <VulnerabilityDetailDrawer
        vulnerability={selectedVuln}
        open={selectedVuln !== null}
        onClose={() => setSelectedVuln(null)}
      />
    </div>
  );
}
