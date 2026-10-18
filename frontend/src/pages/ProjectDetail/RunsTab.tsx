import { useMemo, useState } from 'react';
import { Button, Drawer, Icon, Modal, Spinner, Tag } from '../../design-system';
import type { AuditRunDetail, AuditRunSummary, CompareFinding } from '../../api/types';
import { useCompareRuns, useRun, useRuns, useTriggerIncremental } from '../../api/hooks/useRuns';
import styles from './RunsTab.module.css';

const SEGMENTS: Array<{ key: keyof AuditRunSummary; label: string; className: string }> = [
  { key: 'functions_audited', label: '已审', className: 'seg-audited' },
  { key: 'functions_skipped', label: '预算跳过', className: 'seg-skipped' },
  { key: 'functions_failed', label: '失败', className: 'seg-failed' },
  { key: 'functions_filtered', label: '关键词过滤', className: 'seg-filtered' },
  { key: 'functions_unchanged', label: '未变更', className: 'seg-unchanged' },
];

function statusVariant(status: string): 'success' | 'info' | 'critical' | 'medium' | 'neutral' {
  if (status === 'completed') return 'success';
  if (status === 'degraded') return 'medium';
  if (status === 'failed') return 'critical';
  if (status === 'running') return 'info';
  return 'neutral';
}

export function CoverageBar({ run }: { run: AuditRunSummary }) {
  const total = Math.max(run.functions_extracted, 1);
  return (
    <div className={styles['rt-bar-wrap']}>
      <div className={styles['rt-bar']} role="img" aria-label={`覆盖率：已审 ${run.functions_audited} / 共 ${run.functions_extracted}`}>
        {SEGMENTS.map((segment) => {
          const value = Number(run[segment.key] ?? 0);
          if (!value) return null;
          return (
            <div
              key={segment.key}
              className={`${styles['rt-seg']} ${styles[segment.className]}`}
              style={{ width: `${(value / total) * 100}%` }}
              title={`${segment.label}: ${value}`}
            />
          );
        })}
      </div>
      <div className={styles['rt-bar-legend']}>
        {SEGMENTS.map((segment) => (
          <span key={segment.key} className={styles['rt-legend-item']}>
            <i className={`${styles['rt-dot']} ${styles[segment.className]}`} />
            {segment.label} {Number(run[segment.key] ?? 0)}
          </span>
        ))}
      </div>
    </div>
  );
}

function PlanPanel({ detail }: { detail: AuditRunDetail }) {
  const plan = detail.incremental;
  if (!plan) return null;
  return (
    <div className={styles['rt-plan']}>
      <div className={styles['rt-plan-head']}>
        <strong>增量计划</strong>
        <span className="ds-text-secondary">
          {plan.changed_total} 个变更函数 · {plan.unchanged_total} 个未变更
        </span>
      </div>
      {plan.files.map((file) => (
        <div key={file.file} className={styles['rt-plan-file']}>
          <div className={styles['rt-plan-file-name']}>
            {file.file}
            {file.whole_file && <Tag variant="medium" size="sm">整文件回退</Tag>}
          </div>
          <div className={styles['rt-plan-tags']}>
            {file.changed.map((name) => (
              <Tag key={`c-${name}`} variant="info" size="sm">{name}</Tag>
            ))}
            {file.unchanged.slice(0, 8).map((name) => (
              <Tag key={`u-${name}`} variant="neutral" size="sm">{name}</Tag>
            ))}
            {file.unchanged.length > 8 && (
              <span className="ds-text-secondary">+{file.unchanged.length - 8}</span>
            )}
          </div>
        </div>
      ))}
      {plan.missing.length > 0 && (
        <div className={styles['rt-warn']}>
          <Icon name="alert-circle" size={14} /> 未能映射：{plan.missing.join(', ')}
        </div>
      )}
    </div>
  );
}

function FindingColumn({ title, items, tone }: { title: string; items: CompareFinding[]; tone: string }) {
  return (
    <div className={styles['rt-col']}>
      <div className={`${styles['rt-col-head']} ${styles[tone]}`}>
        {title} <span>{items.length}</span>
      </div>
      <ul className={styles['rt-col-list']}>
        {items.length === 0 && <li className="ds-text-secondary">无</li>}
        {items.map((item) => (
          <li key={`${item.contract}-${item.function}-${item.severity}`}>
            <span className={styles['rt-fn']}>{item.function || item.contract}</span>
            <Tag variant="neutral" size="sm">{item.severity}</Tag>
          </li>
        ))}
      </ul>
    </div>
  );
}

export default function RunsTab({ projectId }: { projectId: string }) {
  const { data: runs = [], isLoading, refetch } = useRuns(projectId);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [diffOpen, setDiffOpen] = useState(false);
  const [diffText, setDiffText] = useState('');
  const [picked, setPicked] = useState<string[]>([]);
  const [compareOpen, setCompareOpen] = useState(false);

  const activeId = selectedId ?? (runs[0] ? String(runs[0].id) : null);
  const { data: detail } = useRun(activeId);
  const trigger = useTriggerIncremental(projectId);

  const compare = useCompareRuns(picked[0] ?? null, picked[1] ?? null);

  const togglePick = (id: number) => {
    const key = String(id);
    setPicked((prev) => {
      if (prev.includes(key)) return prev.filter((x) => x !== key);
      const next = [...prev, key];
      return next.length > 2 ? next.slice(1) : next;
    });
  };

  const canCompare = picked.length === 2;
  const hint = useMemo(() => (diffText.trim() ? null : '请粘贴 unified diff'), [diffText]);

  return (
    <div className={styles['rt-layout']}>
      <aside className={styles['rt-list']}>
        <div className={styles['rt-list-head']}>
          <strong>审计运行</strong>
          <div className={styles['rt-list-actions']}>
            <Button size="sm" variant="secondary" onClick={() => refetch()}>刷新</Button>
            <Button size="sm" onClick={() => setDiffOpen(true)}>增量审计</Button>
          </div>
        </div>

        {isLoading && <div className={styles['rt-empty']}><Spinner size="sm" /> 加载中…</div>}
        {!isLoading && runs.length === 0 && (
          <div className={styles['rt-empty']}>还没有审计运行，先点「增量审计」或上方「LLM 审计」。</div>
        )}

        <ul className={styles['rt-rows']}>
          {runs.map((run) => (
            <li key={run.id}>
              <button
                type="button"
                className={`${styles['rt-row']} ${String(run.id) === activeId ? styles['rt-row-active'] : ''}`}
                onClick={() => setSelectedId(String(run.id))}
              >
                <div className={styles['rt-row-top']}>
                  <span className={styles['rt-run-id']}>#{run.id}</span>
                  <Tag variant={run.mode === 'incremental' ? 'info' : 'neutral'} size="sm">
                    {run.mode === 'incremental' ? '增量' : '全量'}
                  </Tag>
                  <Tag variant={statusVariant(run.status)} size="sm">{run.status}</Tag>
                </div>
                <div className={styles['rt-row-meta']}>
                  审 {run.functions_audited} / 共 {run.functions_extracted}
                  {run.functions_unchanged > 0 && ` · 未变 ${run.functions_unchanged}`}
                  {` · ${run.findings} 条发现`}
                </div>
              </button>
              <label className={styles['rt-pick']}>
                <input
                  type="checkbox"
                  checked={picked.includes(String(run.id))}
                  onChange={() => togglePick(run.id)}
                />
                对比
              </label>
            </li>
          ))}
        </ul>

        <div className={styles['rt-compare-bar']}>
          <Button size="sm" disabled={!canCompare} onClick={() => setCompareOpen(true)}>
            对比选中（{picked.length}/2）
          </Button>
          {picked.length > 0 && (
            <Button size="sm" variant="ghost" onClick={() => setPicked([])}>清空</Button>
          )}
        </div>
      </aside>

      <section className={styles['rt-detail']}>
        {!detail && <div className={styles['rt-empty']}>选择左侧一次运行查看详情</div>}
        {detail && (
          <>
            <div className={styles['rt-detail-head']}>
              <h3>运行 #{detail.id}</h3>
              <Tag variant={detail.mode === 'incremental' ? 'info' : 'neutral'} size="sm">
                {detail.mode === 'incremental' ? '增量审计' : '全量审计'}
              </Tag>
              <Tag variant={statusVariant(detail.status)} size="sm">{detail.status}</Tag>
            </div>

            <CoverageBar run={detail} />

            <div className={styles['rt-stats']}>
              <div><span>提取函数</span><strong>{detail.functions_extracted}</strong></div>
              <div><span>已审</span><strong>{detail.functions_audited}</strong></div>
              <div><span>未变更</span><strong>{detail.functions_unchanged}</strong></div>
              <div><span>发现</span><strong>{detail.findings}</strong></div>
              <div><span>模型</span><strong>{detail.model ?? '-'}</strong></div>
              <div><span>知识库</span><strong>{detail.kb_version ?? '-'}</strong></div>
            </div>

            <PlanPanel detail={detail} />

            <div className={styles['rt-units']}>
              <div className={styles['rt-units-head']}>逐函数账本</div>
              <table className={styles['rt-table']}>
                <thead>
                  <tr><th>文件</th><th>函数</th><th>行</th><th>状态</th><th>原因</th><th>发现</th></tr>
                </thead>
                <tbody>
                  {detail.units.map((unit) => (
                    <tr key={`${unit.file}-${unit.function}-${unit.line}`}>
                      <td>{unit.file}</td>
                      <td>{unit.function}</td>
                      <td>{unit.line}</td>
                      <td>{unit.status}</td>
                      <td>{unit.reason ?? '-'}</td>
                      <td>{unit.findings}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </>
        )}
      </section>

      <Modal
        open={diffOpen}
        onClose={() => setDiffOpen(false)}
        title="粘贴 unified diff 触发增量审计"
        width={720}
        footer={
          <div className={styles['rt-modal-footer']}>
            <span className="ds-text-secondary">{hint ?? '只审计被改动命中的函数'}</span>
            <div>
              <Button variant="ghost" onClick={() => setDiffOpen(false)}>取消</Button>
              <Button
                disabled={!diffText.trim() || trigger.isPending}
                onClick={() =>
                  trigger.mutate(
                    { diff: diffText },
                    {
                      onSuccess: () => {
                        setDiffOpen(false);
                        setDiffText('');
                        refetch();
                      },
                    },
                  )
                }
              >
                {trigger.isPending ? '提交中…' : '开始增量审计'}
              </Button>
            </div>
          </div>
        }
      >
        <textarea
          className={styles['rt-textarea']}
          value={diffText}
          onChange={(event) => setDiffText(event.target.value)}
          placeholder={'--- a/contracts/Token.sol\n+++ b/contracts/Token.sol\n@@ -23,6 +23,6 @@\n ...'}
          spellCheck={false}
        />
      </Modal>

      <Drawer
        open={compareOpen}
        onClose={() => setCompareOpen(false)}
        title={`对比 #${picked[0] ?? '?'} → #${picked[1] ?? '?'}`}
        width={760}
      >
        {compare.isLoading && <Spinner size="sm" />}
        {compare.data && (
          <div className={styles['rt-compare']}>
            <div className={styles['rt-compare-summary']}>
              #{compare.data.base.run_id}（审 {compare.data.base.functions_audited}，{compare.data.base.findings} 条）
              {' → '}
              #{compare.data.head.run_id}（审 {compare.data.head.functions_audited}，{compare.data.head.findings} 条）
            </div>
            <div className={styles['rt-compare-grid']}>
              <FindingColumn title="新增" items={compare.data.added} tone="tone-added" />
              <FindingColumn title="消失" items={compare.data.removed} tone="tone-removed" />
              <FindingColumn title="仍存在" items={compare.data.persisted} tone="tone-persisted" />
            </div>
          </div>
        )}
      </Drawer>
    </div>
  );
}
