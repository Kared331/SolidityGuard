import React from 'react';
import { Card, Tag } from '../../design-system';
import type { AuditFinding, ProjectResponse } from '../../api/types';
import { SEVERITY_CONFIG, SEVERITY_ORDER, type Severity, toSeverityTagVariant } from '../../utils/severity';
import { getSeverityConfig } from '../../utils/severity';
import styles from './ExecutiveSummary.module.css';

interface ExecutiveSummaryProps {
  project: ProjectResponse;
  findings: AuditFinding[];
}

const SEVERITY_PREFIX_MAP: Record<string, string> = {
  critical: 'C',
  high: 'H',
  medium: 'M',
  low: 'L',
  informational: 'I',
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

function getHighestSeverity(findings: AuditFinding[]): Severity {
  let highest: Severity = 'informational';
  for (const f of findings) {
    const key = f.severity.toLowerCase() as Severity;
    const config = getSeverityConfig(key);
    const current = getSeverityConfig(highest);
    if (config.rank > current.rank) {
      highest = key;
    }
  }
  return highest;
}

const ExecutiveSummary: React.FC<ExecutiveSummaryProps> = ({ project, findings }) => {
  const counts = countBySeverity(findings);
  const total = findings.length;
  const highest = getHighestSeverity(findings);
  const highestConfig = SEVERITY_CONFIG[highest];
  const isCriticalOrHigh = highest === 'critical' || highest === 'high';

  return (
    <Card title="审计概要">
      <div className={styles.summary}>
        <p className={styles.paragraph}>
          本次审计覆盖项目 <strong>{project.name}</strong>，采用 LLM + RAG 增强审计引擎对智能合约进行自动化安全分析。
          审计引擎结合大规模语言模型与 SWC 漏洞知识库，对合约代码进行深度语义理解与模式匹配，
          能够识别重入攻击、整数溢出、访问控制缺陷等常见漏洞类型，并给出修复建议与 Gas 优化方案。
        </p>

        <div className={styles.counts}>
          <span className={styles.countsLabel}>共发现 {total} 个漏洞：</span>
          {SEVERITY_ORDER.map((sev) => {
            if (counts[sev] === 0) return null;
            const sevConfig = SEVERITY_CONFIG[sev];
            return (
              <Tag key={sev} variant={toSeverityTagVariant(sev)} size="sm">
                {sevConfig.label}{counts[sev]}
              </Tag>
            );
          })}
        </div>

        <div className={styles.riskRow}>
          <span className={styles.riskLabel}>总体风险等级：</span>
          <Tag variant={isCriticalOrHigh ? 'brand' : 'medium'} size="md">
            {highestConfig.label}
          </Tag>
        </div>
      </div>
    </Card>
  );
};

export { SEVERITY_PREFIX_MAP };
export default ExecutiveSummary;
