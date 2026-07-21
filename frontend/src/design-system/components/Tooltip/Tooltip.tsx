import React from 'react';
import styles from './Tooltip.module.css';

export interface TooltipProps {
  title: string;
  children: React.ReactNode;
  placement?: 'top' | 'bottom' | 'left' | 'right';
  className?: string;
}

const Tooltip: React.FC<TooltipProps> = ({
  title,
  children,
  placement = 'top',
  className,
}) => {
  const wrapperClass = [styles['ds-tooltip-wrapper'], className]
    .filter(Boolean)
    .join(' ');

  return (
    <span className={wrapperClass}>
      {children}
      <span
        className={`${styles['ds-tooltip-bubble']} ${styles[`ds-tooltip--${placement}`]}`}
        role="tooltip"
      >
        <span className={`${styles['ds-tooltip-arrow']} ${styles[`ds-tooltip-arrow--${placement}`]}`} />
        {title}
      </span>
    </span>
  );
};

export default Tooltip;
