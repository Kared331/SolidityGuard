import React, { useCallback, useEffect, useRef } from 'react';
import styles from './Drawer.module.css';

export interface DrawerProps {
  open: boolean;
  onClose: () => void;
  title?: string;
  children?: React.ReactNode;
  width?: number;
  placement?: 'right';
  className?: string;
}

const Drawer: React.FC<DrawerProps> = ({
  open,
  onClose,
  title,
  children,
  width = 420,
  placement = 'right',
  className,
}) => {
  const panelRef = useRef<HTMLDivElement>(null);
  const previousFocusRef = useRef<HTMLElement | null>(null);

  // Trap focus and handle escape key
  useEffect(() => {
    if (open) {
      previousFocusRef.current = document.activeElement as HTMLElement;
      // Focus the panel after animation frame
      requestAnimationFrame(() => {
        panelRef.current?.focus();
      });
    } else if (previousFocusRef.current) {
      previousFocusRef.current.focus();
      previousFocusRef.current = null;
    }
  }, [open]);

  useEffect(() => {
    if (!open) return;

    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        onClose();
        return;
      }
      // Basic focus trapping
      if (e.key === 'Tab' && panelRef.current) {
        const focusable = panelRef.current.querySelectorAll<HTMLElement>(
          'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
        );
        const first = focusable[0];
        const last = focusable[focusable.length - 1];

        if (e.shiftKey) {
          if (document.activeElement === first) {
            e.preventDefault();
            last?.focus();
          }
        } else {
          if (document.activeElement === last) {
            e.preventDefault();
            first?.focus();
          }
        }
      }
    };

    document.addEventListener('keydown', handleKeyDown);
    // Prevent body scroll
    document.body.style.overflow = 'hidden';

    return () => {
      document.removeEventListener('keydown', handleKeyDown);
      document.body.style.overflow = '';
    };
  }, [open, onClose]);

  const handleOverlayClick = useCallback(
    (e: React.MouseEvent) => {
      if (e.target === e.currentTarget) {
        onClose();
      }
    },
    [onClose]
  );

  if (!open) return null;

  const panelClass = [
    styles['ds-drawer-panel'],
    styles[`ds-drawer-panel--${placement}`],
    styles['ds-drawer-panel--open'],
    className,
  ]
    .filter(Boolean)
    .join(' ');

  return (
    <>
      <div
        className={styles['ds-drawer-overlay']}
        onClick={handleOverlayClick}
        aria-hidden="true"
      />
      <div
        ref={panelRef}
        className={panelClass}
        role="dialog"
        aria-modal="true"
        aria-label={title}
        tabIndex={-1}
        style={{ width: `${width}px` }}
      >
        <div className={styles['ds-drawer-header']}>
          <h2 className={styles['ds-drawer-title']}>{title}</h2>
          <button
            className={styles['ds-drawer-close']}
            onClick={onClose}
            type="button"
            aria-label="Close"
          >
            <svg
              width="14"
              height="14"
              viewBox="0 0 14 14"
              fill="none"
              stroke="currentColor"
              strokeWidth="1.5"
              strokeLinecap="round"
            >
              <line x1="1" y1="1" x2="13" y2="13" />
              <line x1="13" y1="1" x2="1" y2="13" />
            </svg>
          </button>
        </div>
        <div className={styles['ds-drawer-body']}>{children}</div>
      </div>
    </>
  );
};

export default Drawer;
