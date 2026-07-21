import React from 'react';
import styles from './Badge.module.css';

export interface BadgeProps {
  count: number;
  variant?: 'neutral' | 'brand' | 'critical';
  size?: 'sm' | 'md';
  className?: string;
}

const Badge: React.FC<BadgeProps> = ({
  count,
  variant = 'neutral',
  size = 'md',
  className,
}) => {
  const classNames = [
    styles['ds-badge'],
    styles[`ds-badge--${variant}`],
    styles[`ds-badge--${size}`],
    className,
  ]
    .filter(Boolean)
    .join(' ');

  return <span className={classNames}>{count}</span>;
};

export default Badge;
