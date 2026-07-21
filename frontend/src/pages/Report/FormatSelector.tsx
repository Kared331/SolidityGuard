import { Button, Icon } from '../../design-system';
import styles from './FormatSelector.module.css';

export type ReportFormat = 'html' | 'pdf' | 'word';

interface FormatOption {
  format: ReportFormat;
  label: string;
  icon: string;
}

const FORMAT_OPTIONS: FormatOption[] = [
  { format: 'html', label: 'HTML', icon: 'code' },
  { format: 'pdf', label: 'PDF', icon: 'file' },
  { format: 'word', label: 'Word', icon: 'file' },
];

interface Props {
  value: ReportFormat;
  onChange: (format: ReportFormat) => void;
}

export default function FormatSelector({ value, onChange }: Props) {
  return (
    <div className={styles['format-selector']}>
      {FORMAT_OPTIONS.map((opt) => (
        <Button
          key={opt.format}
          variant={value === opt.format ? 'primary' : 'ghost'}
          size="md"
          onClick={() => onChange(opt.format)}
          className={styles['format-btn']}
        >
          <Icon name={opt.icon} size={16} />
          {opt.label}
        </Button>
      ))}
    </div>
  );
}
