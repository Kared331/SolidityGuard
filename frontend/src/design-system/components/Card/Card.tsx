import React from 'react';
import styles from './Card.module.css';

export interface CardProps {
  title?: string;
  extra?: React.ReactNode;
  children: React.ReactNode;
  hoverable?: boolean;
  className?: string;
  padding?: 'default' | 'compact';
}

const Card: React.FC<CardProps> = ({
  title,
  extra,
  children,
  hoverable = false,
  className,
  padding = 'default',
}) => {
  const wrapperClass = [
    styles['ds-card'],
    styles[`ds-card--padding-${padding}`],
    hoverable ? styles['ds-card--hoverable'] : '',
    className ?? '',
  ]
    .filter(Boolean)
    .join(' ');

  return (
    <div className={wrapperClass}>
      {(title || extra) && (
        <div className={styles['ds-card__header']}>
          {title && <h3 className={styles['ds-card__title']}>{title}</h3>}
          {extra && <div className={styles['ds-card__extra']}>{extra}</div>}
        </div>
      )}
      <div className={styles['ds-card__body']}>{children}</div>
    </div>
  );
};

Card.displayName = 'Card';
export default Card;
