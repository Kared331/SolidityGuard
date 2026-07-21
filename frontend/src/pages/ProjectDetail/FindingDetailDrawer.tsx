import { Drawer, Tag, Button } from '../../design-system';
import { getSeverityConfig, toSeverityTagVariant } from '../../utils/severity';
import styles from './FindingDetailDrawer.module.css';

interface FindingDetailDrawerProps {
  open: boolean;
  onClose: () => void;
  finding: Record<string, unknown> | null;
  findingType: 'slither' | 'fuzz' | 'llm' | 'vulnerability' | null;
}


function getTitle(findingType: FindingDetailDrawerProps['findingType']): string {
  switch (findingType) {
    case 'slither':
      return 'Slither 检测详情';
    case 'fuzz':
      return 'Fuzzing 测试详情';
    case 'llm':
      return 'LLM 审计详情';
    default:
      return '详情';
  }
}

export default function FindingDetailDrawer({
  open,
  onClose,
  finding,
  findingType,
}: FindingDetailDrawerProps) {
  if (!finding) return null;

  const impact = finding.impact as string | undefined;
  const confidence = finding.confidence as string | undefined;

  return (
    <Drawer
      open={open}
      onClose={onClose}
      title={getTitle(findingType)}
      width={440}
    >
      <div className={styles['fdd-detail']}>
        {/* === SLITHER === */}
        {findingType === 'slither' && (
          <>
            <div className={styles['fdd-row']}>
              <Tag variant={toSeverityTagVariant(String(finding.impact ?? finding.check_name ?? ''))}>
                {getSeverityConfig(String(finding.impact ?? '')).label}
              </Tag>
            </div>

            <div className={styles['fdd-section']}>
              <h4 className={styles['fdd-section-title']}>Detection Check</h4>
              <span className={styles['fdd-field-value']}>
                {String(finding.check_name ?? '-')}
              </span>
            </div>

            <div className={styles['fdd-section']}>
              <h4 className={styles['fdd-section-title']}>Description</h4>
              <p className={styles['fdd-text']}>
                {String(finding.description ?? 'No description available')}
              </p>
            </div>

            {(impact || confidence) && (
              <div className={styles['fdd-section']}>
                {impact && (
                  <div className={styles['fdd-meta-field']}>
                    <h4 className={styles['fdd-section-title']}>Impact</h4>
                    <span className={styles['fdd-field-value']}>
                      {impact}
                    </span>
                  </div>
                )}
                {confidence && (
                  <div className={styles['fdd-meta-field']}>
                    <h4 className={styles['fdd-section-title']}>Confidence</h4>
                    <span className={styles['fdd-field-value']}>
                      {confidence}
                    </span>
                  </div>
                )}
              </div>
            )}
          </>
        )}

        {/* === FUZZ === */}
        {findingType === 'fuzz' && (
          <>
            <div className={styles['fdd-row']}>
              <Tag variant={Number(finding.failures_count ?? 0) === 0 ? 'success' : 'critical'}>
                {Number(finding.failures_count ?? 0) === 0 ? '通过' : `${finding.failures_count} 失败`}
              </Tag>
            </div>

            {finding.raw_output && (
              <div className={styles['fdd-section']}>
                <h4 className={styles['fdd-section-title']}>Output</h4>
                <pre className={styles['fdd-code-block']}>
                  <code>{String(finding.raw_output)}</code>
                </pre>
              </div>
            )}
          </>
        )}

        {/* === LLM === */}
        {findingType === 'llm' && (
          <>
            <div className={styles['fdd-row']}>
              <Tag variant={toSeverityTagVariant(String(finding.severity ?? ''))}>
                {getSeverityConfig(String(finding.severity ?? '')).label}
              </Tag>
            </div>

            <div className={styles['fdd-meta-grid']}>
              <div className={styles['fdd-meta-field']}>
                <h4 className={styles['fdd-section-title']}>Contract</h4>
                <span className={styles['fdd-field-value']}>
                  {String(finding.contract_name ?? '-')}
                </span>
              </div>
              <div className={styles['fdd-meta-field']}>
                <h4 className={styles['fdd-section-title']}>Function</h4>
                <span className={styles['fdd-field-value']}>
                  {String(finding.function_name ?? '-')}
                </span>
              </div>
            </div>

            <div className={styles['fdd-section']}>
              <h4 className={styles['fdd-section-title']}>Vulnerability Description</h4>
              <p className={styles['fdd-text']}>
                {String(finding.vulnerability_description ?? 'No description')}
              </p>
            </div>

            {finding.suggested_fix && (
              <div className={styles['fdd-section']}>
                <h4 className={styles['fdd-section-title']}>Suggested Fix</h4>
                <pre className={styles['fdd-code-block']}>
                  <code>{String(finding.suggested_fix)}</code>
                </pre>
              </div>
            )}

            {finding.gas_optimization && (
              <div className={styles['fdd-section']}>
                <h4 className={styles['fdd-section-title']}>Gas Optimization</h4>
                <pre className={styles['fdd-code-block']}>
                  <code>{String(finding.gas_optimization)}</code>
                </pre>
              </div>
            )}

            {/* Confidence indicator */}
            {(() => {
              const rawConfidence = finding.confidence ?? finding.confidence_score;
              let filledBars = 0;
              let label = 'No confidence data';

              if (typeof rawConfidence === 'number') {
                // Assume 0-1 or 0-100 scale, normalize to 0-5
                filledBars = rawConfidence <= 1
                  ? Math.round(rawConfidence * 5)
                  : Math.round((rawConfidence / 100) * 5);
                filledBars = Math.min(5, Math.max(0, filledBars));
                if (filledBars >= 4) label = 'High confidence';
                else if (filledBars >= 2) label = 'Medium confidence';
                else label = 'Low confidence';
              } else if (typeof rawConfidence === 'string') {
                const s = rawConfidence.toLowerCase();
                if (s === 'high') { filledBars = 4; label = 'High confidence'; }
                else if (s === 'medium') { filledBars = 2; label = 'Medium confidence'; }
                else if (s === 'low') { filledBars = 1; label = 'Low confidence'; }
              }

              return (
                <div className={styles['fdd-confidence']}>
                  <h4 className={styles['fdd-section-title']}>Confidence</h4>
                  <div className={styles['fdd-confidence-bar']}>
                    {[0, 1, 2, 3, 4].map((i) => (
                      <span
                        key={i}
                        className={`${styles['fdd-confidence-segment']} ${
                          i < filledBars ? styles['fdd-confidence-segment--filled'] : ''
                        }`}
                      />
                    ))}
                  </div>
                  <span className={styles['fdd-confidence-label']}>{label}</span>
                </div>
              );
            })()}
          </>
        )}

        {/* Footer: Mark False Positive */}
        <div className={styles['fdd-footer']}>
          <Button variant="ghost" size="sm">
            标记误报
          </Button>
        </div>
      </div>
    </Drawer>
  );
}
