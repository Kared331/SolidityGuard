import { useState, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import { Button, Input, Icon, Spinner } from '../../design-system';
import { useProjects } from '../../api/hooks/useProjects';
import ProjectCard from './ProjectCard';
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

  return (
    <div>
      <div className={styles['dashboard__header']}>
        <h1 className="ds-text-2xl" style={{ margin: 0 }}>
          项目列表
        </h1>
        <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--ds-space-3)' }}>
          <div className={styles['dashboard__search']}>
            <Input
              placeholder="搜索项目..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              prefix={<Icon name="search" size={16} />}
            />
          </div>
          <Button variant="primary" onClick={() => navigate('/upload')}>
            新建上传
          </Button>
        </div>
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
          <span className={styles['dashboard__empty-text']}>暂无项目，点击新建上传开始</span>
          <Button variant="primary" onClick={() => navigate('/upload')}>
            新建上传
          </Button>
        </div>
      ) : (
        <div className={styles['dashboard__grid']}>
          {filtered.map((project) => (
            <ProjectCard key={project.id} project={project} />
          ))}
        </div>
      )}
    </div>
  );
}
