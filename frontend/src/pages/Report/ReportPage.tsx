import { useState, useCallback } from 'react';
import { useParams } from 'react-router-dom';
import { Button, Breadcrumb, Icon } from '../../design-system';
import type { BreadcrumbItem } from '../../design-system';
import { useReports, useGenerateReport } from '../../api/hooks/useReports';
import FormatSelector from './FormatSelector';
import type { ReportFormat } from './FormatSelector';
import ReportList from './ReportList';
import styles from './ReportPage.module.css';

function ReportContent({ projectId }: { projectId: string }) {
  const [selectedFormat, setSelectedFormat] = useState<ReportFormat>('html');

  const { data: reports = [], isLoading: reportsLoading } =
    useReports(projectId);
  const generateMutation = useGenerateReport();

  const handleGenerate = useCallback(() => {
    generateMutation.mutate({ projectId, format: selectedFormat });
  }, [projectId, selectedFormat, generateMutation]);

  const breadcrumbItems: BreadcrumbItem[] = [
    { title: '项目列表', href: '/dashboard' },
    { title: `Project #${projectId}`, href: `/projects/${projectId}` },
    { title: '报告' },
  ];

  return (
    <div className={styles['report-page']}>
      <Breadcrumb items={breadcrumbItems} />

      <h1
        className="ds-text-xl"
        style={{ margin: 'var(--ds-space-4) 0 var(--ds-space-6)' }}
      >
        生成报告
      </h1>

      <div className={styles['report-generate-section']}>
        <FormatSelector
          value={selectedFormat}
          onChange={setSelectedFormat}
        />

        <div className={styles['report-generate-action']}>
          <Button
            variant="brand"
            size="md"
            onClick={handleGenerate}
            disabled={generateMutation.isPending}
            loading={generateMutation.isPending}
          >
            {generateMutation.isPending ? '正在生成...' : '生成报告'}
          </Button>
        </div>

        {generateMutation.isError && (
          <div
            className={`${styles['report-generate-status']} ${styles['report-generate-status--error']}`}
          >
            生成失败: {(generateMutation.error as Error)?.message || '未知错误'}
          </div>
        )}

        {generateMutation.isSuccess && (
          <div
            className={`${styles['report-generate-status']} ${styles['report-generate-status--success']}`}
          >
            报告生成成功
          </div>
        )}
      </div>

      <div className={styles['report-history-section']}>
        <h2
          className="ds-text-lg"
          style={{ marginBottom: 'var(--ds-space-4)' }}
        >
          历史报告
        </h2>
        <ReportList
          reports={reports}
          isLoading={reportsLoading}
          projectId={projectId}
        />
      </div>
    </div>
  );
}

export default function ReportPage() {
  const { id: projectId } = useParams<{ id: string }>();

  if (!projectId) {
    return (
      <div className={styles['report-page']}>
        <div className={styles['report-empty-state']}>
          <Icon
            name="file"
            size={48}
            color="var(--ds-color-icon-tertiary)"
          />
          <p>请先选择一个项目</p>
        </div>
      </div>
    );
  }

  return <ReportContent projectId={projectId} />;
}
