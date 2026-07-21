import React from 'react';
import styles from './Spinner.module.css';

export interface SpinnerProps {
  size?: 'sm' | 'md' | 'lg';
  className?: string;
}

const Spinner: React.FC<SpinnerProps> = ({ size = 'md', className }) => {
  const wrapperClass = [
    styles['ds-spinner'],
    styles[`ds-spinner--${size}`],
    className ?? '',
  ]
    .filter(Boolean)
    .join(' ');

  return (
    <span className={wrapperClass} role="status" aria-label="加载中">
      <span className={styles['ds-spinner__sr-only']}>Loading...</span>
    </span>
  );
};

Spinner.displayName = 'Spinner';
export default Spinner;
