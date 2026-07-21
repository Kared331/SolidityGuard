import { Outlet } from 'react-router-dom';
import Header from '../Header/Header';
import styles from './AppShell.module.css';

export default function AppShell() {
  return (
    <div className={styles.shell}>
      <Header />
      <main className={styles.content}>
        <div className={styles.container}>
          <Outlet />
        </div>
      </main>
    </div>
  );
}
