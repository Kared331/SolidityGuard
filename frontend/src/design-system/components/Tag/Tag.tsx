import React from 'react';
import styles from './Tag.module.css';

export interface TagProps {
  children: React.ReactNode;
  variant?: 'neutral' | 'brand' | 'critical' | 'high' | 'medium' | 'low' | 'info' | 'success';
  size?: 'sm' | 'md';
  className?: string;
}

const Tag: React.FC<TagProps> = ({
  children,
  variant = 'neutral',
  size = 'md',
  className,
}) => {
  const classNames = [
    styles['ds-tag'],
    styles[`ds-tag--${variant}`],
    styles[`ds-tag--${size}`],
    className,
  ]
    .filter(Boolean)
    .join(' ');

  return <span className={classNames}>{children}</span>;
};

export default Tag;
