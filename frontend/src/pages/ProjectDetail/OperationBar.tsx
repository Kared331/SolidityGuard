import { useNavigate } from 'react-router-dom';
import { Button, Icon } from '../../design-system';
import { useTriggerAnalysis } from '../../api/hooks/useAnalyses';
import { useTriggerFuzz } from '../../api/hooks/useFuzzResults';
import { useTriggerLLMAudit } from '../../api/hooks/useAuditResults';
import { useAppStore } from '../../stores/useAppStore';
import styles from './OperationBar.module.css';

interface OperationBarProps {
  projectId: string;
}

export default function OperationBar({ projectId }: OperationBarProps) {
  const navigate = useNavigate();
  const sseConnected = useAppStore((s) => s.sseConnected);

  const { mutate: triggerAnalysis, isPending: analysisLoading } = useTriggerAnalysis();
  const { mutate: triggerFuzz, isPending: fuzzLoading } = useTriggerFuzz();
  const { mutate: triggerLLMAudit, isPending: llmAuditLoading } = useTriggerLLMAudit();

  return (
    <div className={styles['op-bar']}>
      <div className={styles['op-bar-actions']}>
        <Button
          variant="secondary"
          size="md"
          loading={analysisLoading}
          onClick={() => triggerAnalysis(projectId)}
        >
          <Icon name="play" size={14} />
          Slither 分析
        </Button>

        <Button
          variant="secondary"
          size="md"
          loading={fuzzLoading}
          onClick={() => triggerFuzz(projectId)}
        >
          <Icon name="zap" size={14} />
          Fuzzing 测试
        </Button>

        <Button
          variant="brand"
          size="md"
          loading={llmAuditLoading}
          onClick={() => triggerLLMAudit(projectId)}
        >
          <Icon name="brain" size={14} />
          LLM 审计
        </Button>

        <Button
          variant="secondary"
          size="md"
          onClick={() => navigate(`/projects/${projectId}/report`)}
        >
          <Icon name="file" size={14} />
          生成报告
        </Button>
      </div>

      <div className={styles['op-bar-status']}>
        <span
          className={`${styles['op-bar-status-dot']} ${
            sseConnected ? styles['op-bar-status-dot--connected'] : styles['op-bar-status-dot--disconnected']
          }`}
        />
        <span className={styles['op-bar-status-text']}>
          {sseConnected ? 'SSE Connected' : 'SSE Disconnected'}
        </span>
      </div>
    </div>
  );
}
