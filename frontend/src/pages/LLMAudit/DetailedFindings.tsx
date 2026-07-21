import React, { useState, useCallback, useMemo } from 'react';
import { Card, Tag, Icon, Button } from '../../design-system';
import type { AuditFinding } from '../../api/types';
import { severityRank, getSeverityConfig, SEVERITY_ORDER, toSeverityTagVariant } from '../../utils/severity';
import { useAuditDetailStore } from '../../stores/useAuditDetailStore';
import styles from './DetailedFindings.module.css';

interface DetailedFindingsProps {
  findings: AuditFinding[];
}

const SEVERITY_ID_PREFIX: Record<string, string> = {
  critical: 'CR',
  high: 'HI',
  medium: 'ME',
  low: 'LO',
  informational: 'IN',
};

function generateFindingIds(findings: AuditFinding[]): Map<number, string> {
  const groups: Record<string, AuditFinding[]> = {};
  for (const sev of SEVERITY_ORDER) {
    groups[sev] = [];
  }
  for (const f of findings) {
    const key = f.severity.toLowerCase();
    if (groups[key]) {
      groups[key].push(f);
    }
  }
  const idMap = new Map<number, string>();
  for (const sev of SEVERITY_ORDER) {
    const group = groups[sev];
    group.sort((a, b) => a.contract_name.localeCompare(b.contract_name));
    group.forEach((f, idx) => {
      const num = String(idx + 1).padStart(2, '0');
      idMap.set(f.id, `${SEVERITY_ID_PREFIX[sev]}-${num}`);
    });
  }
  return idMap;
}

function truncateDescription(desc: string, maxLen: number = 80): string {
  if (desc.length <= maxLen) return desc;
  return desc.substring(0, maxLen).trimEnd() + '...';
}

function extractImpact(desc: string): string {
  const lower = desc.toLowerCase();
  const idx = lower.indexOf('impact');
  if (idx === -1) return '参见描述';
  return desc.substring(idx, Math.min(idx + 200, desc.length));
}

const DetailedFindings: React.FC<DetailedFindingsProps> = ({ findings }) => {
  const [expandedIds, setExpandedIds] = useState<Set<number>>(new Set());
  const openDrawer = useAuditDetailStore((s) => s.openDrawer);

  const sortedFindings = useMemo(() => [...findings].sort((a, b) => {
    const rankDiff = severityRank(b.severity) - severityRank(a.severity);
    if (rankDiff !== 0) return rankDiff;
    return a.contract_name.localeCompare(b.contract_name);
  }), [findings]);

  const findingIds = useMemo(() => generateFindingIds(findings), [findings]);

  const toggleExpand = useCallback((id: number) => {
    setExpandedIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) {
        next.delete(id);
      } else {
        next.add(id);
      }
      return next;
    });
  }, []);

  if (findings.length === 0) {
    return (
      <Card title="详细发现">
        <p style={{ color: 'var(--ds-color-text-tertiary)', margin: 0, fontSize: 'var(--ds-font-size-base)' }}>
          未发现漏洞，合约安全性良好。
        </p>
      </Card>
    );
  }

  return (
    <Card title="详细发现">
      <div className={styles.container}>
        {sortedFindings.map((finding) => {
          const sevConfig = getSeverityConfig(finding.severity);
          const findingId = findingIds.get(finding.id) || '--';
          const isExpanded = expandedIds.has(finding.id);

          return (
            <div key={finding.id} className={styles.findingCard}>
              <div
                className={styles.findingHeader}
                onClick={() => toggleExpand(finding.id)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' || e.key === ' ') {
                    e.preventDefault();
                    toggleExpand(finding.id);
                  }
                }}
                role="button"
                tabIndex={0}
                aria-expanded={isExpanded}
              >
                <Tag variant={toSeverityTagVariant(finding.severity)} size="sm">
                  {sevConfig.label}
                </Tag>
                <span className={styles.findingId}>{findingId}</span>
                <span className={styles.findingTitle}>
                  {truncateDescription(finding.vulnerability_description)}
                </span>
                <span
                  className={`${styles.expandIcon} ${isExpanded ? styles.expandIconExpanded : ''}`}
                >
                  <Icon name="chevron-right" size={14} />
                </span>
              </div>

              {isExpanded && (
                <div className={styles.findingBody}>
                  <div className={styles.metaRow}>
                    {finding.contract_name && (
                      <div className={styles.metaItem}>
                        <span className={styles.metaLabel}>合约：</span>
                        <span className={styles.metaValue}>{finding.contract_name}</span>
                      </div>
                    )}
                    {finding.function_name && (
                      <div className={styles.metaItem}>
                        <span className={styles.metaLabel}>函数：</span>
                        <span className={styles.metaValue}>{finding.function_name}</span>
                      </div>
                    )}
                  </div>

                  <div className={styles.section}>
                    <h4 className={styles.sectionTitle}>漏洞描述</h4>
                    <p className={styles.description}>
                      {finding.vulnerability_description}
                    </p>
                  </div>

                  <div className={styles.section}>
                    <h4 className={styles.sectionTitle}>影响范围</h4>
                    <p className={styles.impact}>
                      {extractImpact(finding.vulnerability_description)}
                    </p>
                  </div>

                  {finding.suggested_fix && (
                    <div className={styles.section}>
                      <h4 className={styles.sectionTitle}>修复建议</h4>
                      <pre className={styles.codeBlock}>
                        <code>{finding.suggested_fix}</code>
                      </pre>
                    </div>
                  )}

                  {finding.gas_optimization && (
                    <div className={styles.section}>
                      <h4 className={styles.sectionTitle}>Gas 优化</h4>
                      <pre className={styles.codeBlock}>
                        <code>{finding.gas_optimization}</code>
                      </pre>
                    </div>
                  )}

                  <div className={styles.findingActions}>
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={(e) => {
                        e.stopPropagation();
                        openDrawer(finding as unknown as Record<string, unknown>, 'llm');
                      }}
                    >
                      在项目中查看
                    </Button>
                  </div>
                </div>
              )}
            </div>
          );
        })}
      </div>
    </Card>
  );
};

export { generateFindingIds };
export default DetailedFindings;
