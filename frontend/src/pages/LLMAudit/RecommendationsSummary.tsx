import React, { useMemo } from 'react';
import { Card, Tag, Button } from '../../design-system';
import type { AuditFinding } from '../../api/types';
import { severityRank, getSeverityConfig, SEVERITY_ORDER, toSeverityTagVariant } from '../../utils/severity';
import { useAuditDetailStore } from '../../stores/useAuditDetailStore';
import { generateFindingIds } from './DetailedFindings';
import styles from './RecommendationsSummary.module.css';

interface RecommendationsSummaryProps {
  findings: AuditFinding[];
}

function shortDescription(desc: string, maxLen: number = 60): string {
  if (desc.length <= maxLen) return desc;
  return desc.substring(0, maxLen).trimEnd() + '...';
}

function getFixSummary(finding: AuditFinding): string {
  if (finding.suggested_fix) {
    const lines = finding.suggested_fix.split('\n').filter((l) => l.trim());
    if (lines.length > 0) {
      const first = lines[0].trim();
      if (first.length <= 80) return first;
      return first.substring(0, 80).trimEnd() + '...';
    }
  }
  return '建议参考漏洞详情进行修复';
}

const RecommendationsSummary: React.FC<RecommendationsSummaryProps> = ({ findings }) => {
  const openDrawer = useAuditDetailStore((s) => s.openDrawer);

  const findingIds = useMemo(() => generateFindingIds(findings), [findings]);

  const sorted = useMemo(() => [...findings]
    .filter((f) => {
      const sev = f.severity.toLowerCase();
      return SEVERITY_ORDER.some((s) => s === sev);
    })
    .sort((a, b) => {
      const rankDiff = severityRank(b.severity) - severityRank(a.severity);
      if (rankDiff !== 0) return rankDiff;
      return a.contract_name.localeCompare(b.contract_name);
    }), [findings]);

  if (sorted.length === 0) {
    return (
      <Card title="修复建议清单">
        <p className={styles.empty}>暂无需要修复的漏洞。</p>
      </Card>
    );
  }

  return (
    <Card title="修复建议清单">
      <div className={styles.container}>
        {sorted.map((finding, index) => {
          const sevConfig = getSeverityConfig(finding.severity);
          const findingId = findingIds.get(finding.id) || '--';
          const fixSummary = getFixSummary(finding);

          return (
            <div key={finding.id} className={styles.item}>
              <span className={styles.itemNumber}>{index + 1}</span>
              <div className={styles.itemContent}>
                <div className={styles.itemHeader}>
                  <Tag variant={toSeverityTagVariant(finding.severity)} size="sm">
                    {sevConfig.label}
                  </Tag>
                  <span style={{ fontFamily: 'var(--ds-font-family-metric)', fontSize: 'var(--ds-font-size-sm)', color: 'var(--ds-color-text-tertiary)' }}>
                    [{findingId}]
                  </span>
                  <span style={{ fontSize: 'var(--ds-font-size-base)', color: 'var(--ds-color-text-primary)' }}>
                    {shortDescription(finding.vulnerability_description)}
                  </span>
                </div>
                <p className={styles.itemFix}>{fixSummary}</p>
              </div>
              <div className={styles.itemAction}>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => openDrawer(finding as unknown as Record<string, unknown>, 'llm')}
                >
                  查看详情
                </Button>
              </div>
            </div>
          );
        })}
      </div>
    </Card>
  );
};

export default RecommendationsSummary;
