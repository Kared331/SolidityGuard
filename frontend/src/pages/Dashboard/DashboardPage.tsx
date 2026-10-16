import { useState, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import { Button, Input, Icon, Spinner } from '../../design-system';
import { useProjects } from '../../api/hooks/useProjects';
import ProjectCard from './ProjectCard';
import InkVortex from '../../components/InkVortex/InkVortex';
import styles from './DashboardPage.module.css';

export default function DashboardPage() {
  const navigate = useNavigate();
  const { data: projects, isLoading } = useProjects();
  const [search, setSearch] = useState('');

  const filtered = useMemo(() => {
    if (!projects) return [];
    const q = search.trim().toLowerCase();
    if (!q) return projects;
    return projects.filter((p) => p.name.toLowerCase().includes(q));
  }, [projects, search]);

  const readyCount = useMemo(
    () => filtered.filter((p) => p.status === 'ready').length,
    [filtered]
  );

  return (
    <div>
      {/* 卷首：墨点漩涡 + 居中标题 */}
      <section className={styles['dashboard__hero']}>
        <InkVortex className={styles['dashboard__vortex']} />
        <div className={styles['dashboard__hero-content']}>
          <h1 className={styles['dashboard__title']}>项目卷宗</h1>
          {!isLoading && projects && projects.length > 0 && (
            <p className={styles['dashboard__count']}>
              共 <span className={styles['dashboard__count-num']}>{filtered.length}</span>{' '}
              卷 · 其中{' '}
              <span className={styles['dashboard__count-num']}>{readyCount}</span>{' '}
              卷已就绪
            </p>
          )}
        </div>
      </section>

      <div className={styles['dashboard__toolbar']}>
        <div className={styles['dashboard__search']}>
          <Input
            placeholder="检索卷宗..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            prefix={<Icon name="search" size={16} />}
          />
        </div>
        <Button variant="primary" onClick={() => navigate('/upload')}>
          新建上传
        </Button>
      </div>

      {isLoading ? (
        <div className={styles['dashboard__grid']}>
          {Array.from({ length: 6 }).map((_, i) => (
            <div key={i} className={styles['dashboard__skeleton-card']}>
              <Spinner size="lg" />
            </div>
          ))}
        </div>
      ) : filtered.length === 0 ? (
        <div className={styles['dashboard__empty']}>
          <div className={styles['dashboard__empty-icon']}>
            <Icon name="upload" size={48} />
          </div>
          <h2 className={styles['dashboard__empty-title']}>此卷空白</h2>
          <span className={styles['dashboard__empty-text']}>
            上传第一份合约，开始批注
          </span>
          <Button variant="primary" onClick={() => navigate('/upload')}>
            新建上传
          </Button>
        </div>
      ) : (
        <div className={styles['dashboard__grid']}>
          {filtered.map((project, idx) => (
            <ProjectCard key={project.id} project={project} index={idx} />
          ))}
        </div>
      )}
    </div>
  );
}
