import { useNavigate } from 'react-router-dom';
import { Icon } from '../../design-system';
import type { ProjectResponse } from '../../api/types';
import { formatDate } from '../../utils/format';
import styles from './ProjectCard.module.css';

interface ProjectCardProps {
  project: ProjectResponse;
  /** 卷宗编号（渲染为 001 式行号） */
  index: number;
}

/* 朱批状态映射：就绪=墨绿，处理中=藤黄，失败=朱砂，待处理=铅笔 */
const STATUS_MAP: Record<string, { tone: string; label: string }> = {
  ready: { tone: 'ready', label: '就绪' },
  processing: { tone: 'processing', label: '处理中' },
  analyzing: { tone: 'processing', label: '分析中' },
  failed: { tone: 'failed', label: '失败' },
  uploaded: { tone: 'pending', label: '待处理' },
};

function getStatus(status: string) {
  return STATUS_MAP[status] ?? { tone: 'pending', label: status };
}

export default function ProjectCard({ project, index }: ProjectCardProps) {
  const navigate = useNavigate();
  const status = getStatus(project.status);
  const serial = String(index + 1).padStart(3, '0');

  return (
    <article
      className={styles['entry']}
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
      {/* 左侧行号 gutter——代码手稿的视觉签名 */}
      <div className={styles['entry__gutter']}>
        <span className={styles['entry__serial']}>{serial}</span>
      </div>

      <div className={styles['entry__main']}>
        <div className={styles['entry__top']}>
          <h3 className={styles['entry__name']}>{project.name || '未命名卷宗'}</h3>
          <span className={`${styles['entry__status']} ${styles[`entry__status--${status.tone}`]}`}>
            {status.label}
          </span>
        </div>
        <div className={styles['entry__meta']}>
          <span className={styles['entry__meta-item']}>
            创建于 <span className={styles['entry__meta-mono']}>{formatDate(project.created_at)}</span>
          </span>
          {project.file_count !== undefined && (
            <span className={styles['entry__meta-item']}>
              <Icon name="file" size={13} />
              <span>
                <span className={styles['entry__meta-mono']}>{project.file_count}</span> 个文件
              </span>
            </span>
          )}
        </div>
      </div>

      <div className={styles['entry__arrow']}>
        <Icon name="arrow-right" size={16} />
      </div>
    </article>
  );
}
