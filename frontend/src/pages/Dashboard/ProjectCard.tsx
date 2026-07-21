import { useNavigate } from 'react-router-dom';
import { Card, Tag, Icon } from '../../design-system';
import type { ProjectResponse } from '../../api/types';
import { formatDate } from '../../utils/format';
import styles from './ProjectCard.module.css';

interface ProjectCardProps {
  project: ProjectResponse;
}

const STATUS_TAG_MAP: Record<string, { variant: 'success' | 'info' | 'critical' | 'neutral'; label: string }> = {
  ready: { variant: 'success', label: '就绪' },
  analyzing: { variant: 'info', label: '分析中' },
  failed: { variant: 'critical', label: '失败' },
};

function getStatusConfig(status: string) {
  return STATUS_TAG_MAP[status] ?? { variant: 'neutral' as const, label: status };
}

export default function ProjectCard({ project }: ProjectCardProps) {
  const navigate = useNavigate();
  const statusConfig = getStatusConfig(project.status);

  return (
    <Card
      hoverable
      padding="default"
      title={project.name}
      extra={
        <Tag variant={statusConfig.variant} size="sm">
          {statusConfig.label}
        </Tag>
      }
    >
      <div
        className={styles['project-card__body']}
        onClick={() => navigate(`/projects/${project.id}`)}
        role="button"
        tabIndex={0}
        onKeyDown={(e) => {
          if (e.key === 'Enter' || e.key === ' ') {
            e.preventDefault();
            navigate(`/projects/${project.id}`);
          }
        }}
      >
        <div className={styles['project-card__meta']}>
          <span className={styles['project-card__meta-item']}>
            <Icon name="clock" size={14} />
            <span>创建于 {formatDate(project.created_at)}</span>
          </span>
          {project.file_count !== undefined && (
            <span className={styles['project-card__meta-item']}>
              <Icon name="file" size={14} />
              <span>{project.file_count} 个文件</span>
            </span>
          )}
        </div>
      </div>
    </Card>
  );
}
