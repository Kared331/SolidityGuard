import { Link, useLocation } from 'react-router-dom';
import styles from './Header.module.css';

export default function Header() {
  const location = useLocation();

  return (
    <header className={styles.header}>
      <Link to="/" className={styles.brand}>
        SolidiGuard
      </Link>

      <nav className={styles.actions}>
        <Link
          to="/"
          className={`${styles.navLink} ${location.pathname === '/' || location.pathname.startsWith('/projects') ? styles.navLinkActive : ''}`}
        >
          <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
            <rect x="1" y="1" width="6" height="6" rx="1" stroke="currentColor" strokeWidth="1.5"/>
            <rect x="9" y="1" width="6" height="6" rx="1" stroke="currentColor" strokeWidth="1.5"/>
            <rect x="1" y="9" width="6" height="6" rx="1" stroke="currentColor" strokeWidth="1.5"/>
            <rect x="9" y="9" width="6" height="6" rx="1" stroke="currentColor" strokeWidth="1.5"/>
          </svg>
          项目
        </Link>
        <Link
          to="/upload"
          className={`${styles.navLink} ${location.pathname === '/upload' ? styles.navLinkActive : ''}`}
        >
          <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
            <path d="M8 2v8M4 6l4-4 4 4M2 12v1a1 1 0 001 1h10a1 1 0 001-1v-1"
              stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
          </svg>
          上传
        </Link>
        <Link
          to="/vulnerabilities"
          className={`${styles.navLink} ${location.pathname === '/vulnerabilities' ? styles.navLinkActive : ''}`}
        >
          <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
            <path d="M8 1L1 4l7 3 7-3-7-3zM1 8l7 3 7-3M1 12l7 3 7-3"
              stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
          </svg>
          漏洞库
        </Link>
      </nav>
    </header>
  );
}
