import React from 'react';
import styles from './Breadcrumb.module.css';

export interface BreadcrumbItem {
  title: string;
  href?: string;
}

export interface BreadcrumbProps {
  items: BreadcrumbItem[];
  separator?: string;
  className?: string;
}

const Breadcrumb: React.FC<BreadcrumbProps> = ({
  items,
  separator = '/',
  className,
}) => {
  const containerClass = [styles['ds-breadcrumb'], className]
    .filter(Boolean)
    .join(' ');

  return (
    <nav className={containerClass} aria-label="Breadcrumb">
      {items.map((item, index) => {
        const isLast = index === items.length - 1;

        return (
          <React.Fragment key={index}>
            {index > 0 && (
              <span
                className={styles['ds-breadcrumb-separator']}
                aria-hidden="true"
              >
                {separator}
              </span>
            )}
            {isLast ? (
              <span className={`${styles['ds-breadcrumb-item']} ${styles['ds-breadcrumb-item--active']}`}>
                {item.title}
              </span>
            ) : item.href ? (
              <a
                href={item.href}
                className={styles['ds-breadcrumb-item']}
              >
                {item.title}
              </a>
            ) : (
              <span className={styles['ds-breadcrumb-item']}>
                {item.title}
              </span>
            )}
          </React.Fragment>
        );
      })}
    </nav>
  );
};

export default Breadcrumb;
