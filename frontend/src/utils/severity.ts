export const SEVERITY_CONFIG = {
  critical:       { color: 'var(--ds-color-critical)', bg: 'var(--ds-color-critical-bg)', border: 'var(--ds-color-critical-border)', label: '严重',   rank: 5 },
  high:           { color: 'var(--ds-color-high)',     bg: 'var(--ds-color-high-bg)',     border: 'var(--ds-color-high-border)',     label: '高危',   rank: 4 },
  medium:         { color: 'var(--ds-color-medium)',   bg: 'var(--ds-color-medium-bg)',   border: 'var(--ds-color-medium-border)',   label: '中危',   rank: 3 },
  low:            { color: 'var(--ds-color-low)',      bg: 'var(--ds-color-low-bg)',      border: 'var(--ds-color-low-border)',      label: '低危',   rank: 2 },
  informational:  { color: 'var(--ds-color-info)',     bg: 'var(--ds-color-info-bg)',     border: 'var(--ds-color-info-border)',     label: '信息',   rank: 1 },
} as const;

export type Severity = keyof typeof SEVERITY_CONFIG;

export type TagVariant = 'neutral' | 'brand' | 'critical' | 'high' | 'medium' | 'low' | 'info' | 'success';

export function toSeverityTagVariant(severity: string): TagVariant {
  const key = severity.toLowerCase();
  if (key === 'informational') return 'info';
  if (SEVERITY_CONFIG[key as Severity]) return key as TagVariant;
  return 'neutral';
}

export function getSeverityConfig(severity: string) {
  const key = severity.toLowerCase() as Severity;
  return SEVERITY_CONFIG[key] ?? { color: 'var(--ds-color-neutral-500)', bg: 'var(--ds-color-neutral-100)', border: 'var(--ds-color-neutral-200)', label: severity, rank: 0 };
}

export function severityRank(severity: string): number {
  return getSeverityConfig(severity).rank;
}

export const SEVERITY_ORDER: Severity[] = ['critical', 'high', 'medium', 'low', 'informational'];
