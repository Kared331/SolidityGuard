import { useToastStore, type ToastType } from '../../stores/useToastStore';
import styles from './ToastContainer.module.css';

const ICON_MAP: Record<ToastType, string> = {
  success: 'check-circle',
  info: 'info',
  warning: 'alert-triangle',
  error: 'x-circle',
};

export default function ToastContainer() {
  const toasts = useToastStore((s) => s.toasts);
  const removeToast = useToastStore((s) => s.removeToast);

  if (toasts.length === 0) return null;

  return (
    <div className={styles['toast-container']} aria-live="polite">
      {toasts.map((toast) => (
        <div
          key={toast.id}
          className={`${styles['toast']} ${styles[`toast--${toast.type}`]}`}
          onClick={() => removeToast(toast.id)}
          role="alert"
        >
          <svg
            className={styles['toast-icon']}
            width="18"
            height="18"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
          >
            {ICON_MAP[toast.type] === 'check-circle' && (
              <>
                <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14" />
                <polyline points="22 4 12 14.01 9 11.01" />
              </>
            )}
            {ICON_MAP[toast.type] === 'info' && (
              <>
                <circle cx="12" cy="12" r="10" />
                <line x1="12" y1="16" x2="12" y2="12" />
                <line x1="12" y1="8" x2="12.01" y2="8" />
              </>
            )}
            {ICON_MAP[toast.type] === 'alert-triangle' && (
              <>
                <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z" />
                <line x1="12" y1="9" x2="12" y2="13" />
                <line x1="12" y1="17" x2="12.01" y2="17" />
              </>
            )}
            {ICON_MAP[toast.type] === 'x-circle' && (
              <>
                <circle cx="12" cy="12" r="10" />
                <line x1="15" y1="9" x2="9" y2="15" />
                <line x1="9" y1="9" x2="15" y2="15" />
              </>
            )}
          </svg>
          <span className={styles['toast-message']}>{toast.message}</span>
        </div>
      ))}
    </div>
  );
}
