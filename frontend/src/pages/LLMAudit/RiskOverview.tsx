import React from 'react';
import { Card } from '../../design-system';
import type { AuditFinding } from '../../api/types';
import { SEVERITY_CONFIG, SEVERITY_ORDER } from '../../utils/severity';
import styles from './RiskOverview.module.css';

interface RiskOverviewProps {
  findings: AuditFinding[];
}

const BAR_COLORS: Record<string, string> = {
  critical: '#DC2626',
  high: '#EA580C',
  medium: '#CA8A04',
  low: '#2563EB',
  informational: '#16A34A',
};

function countBySeverity(findings: AuditFinding[]): Record<string, number> {
  const counts: Record<string, number> = {};
  for (const sev of SEVERITY_ORDER) {
    counts[sev] = 0;
  }
  for (const f of findings) {
    const key = f.severity.toLowerCase();
    if (counts[key] !== undefined) {
      counts[key]++;
    }
  }
  return counts;
}

const RiskOverview: React.FC<RiskOverviewProps> = ({ findings }) => {
  const counts = countBySeverity(findings);
  const maxCount = Math.max(...Object.values(counts), 1);

  return (
    <Card title="风险分布">
      <div className={styles.chart}>
        {SEVERITY_ORDER.map((sev) => {
          const sevConfig = SEVERITY_CONFIG[sev];
          const count = counts[sev];
          const barColor = BAR_COLORS[sev];
          const isEmpty = count === 0;
          const widthPercent = isEmpty ? 0 : (count / maxCount) * 100;

          return (
            <div key={sev} className={styles.barRow}>
              <span className={styles.barLabel}>{sevConfig.label}</span>
              <div className={styles.barTrack}>
                <div
                  className={`${styles.barFill} ${isEmpty ? styles.barFillEmpty : ''}`}
                  style={{
                    width: `${widthPercent}%`,
                    backgroundColor: isEmpty ? 'var(--ds-color-neutral-100)' : barColor,
                  }}
                />
                <span
                  className={styles.barCount}
                  style={{ color: isEmpty ? 'var(--ds-color-text-tertiary)' : barColor }}
                >
                  {count}
                </span>
              </div>
            </div>
          );
        })}
      </div>
    </Card>
  );
};

export default RiskOverview;
