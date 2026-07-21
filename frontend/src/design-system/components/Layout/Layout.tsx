import React from 'react';
import styles from './Layout.module.css';

export interface LayoutProps {
  children?: React.ReactNode;
  className?: string;
}

export interface HeaderProps {
  children?: React.ReactNode;
  className?: string;
}

export interface SiderProps {
  children?: React.ReactNode;
  width?: number;
  className?: string;
}

export interface ContentProps {
  children?: React.ReactNode;
  className?: string;
}

const Header: React.FC<HeaderProps> = ({ children, className }) => {
  const cls = [styles['ds-layout-header'], className].filter(Boolean).join(' ');
  return <header className={cls}>{children}</header>;
};

const Sider: React.FC<SiderProps> = ({ children, width = 240, className }) => {
  const cls = [styles['ds-layout-sider'], className].filter(Boolean).join(' ');
  return (
    <aside className={cls} style={{ width: `${width}px` }}>
      {children}
    </aside>
  );
};

const Content: React.FC<ContentProps> = ({ children, className }) => {
  const cls = [styles['ds-layout-content'], className].filter(Boolean).join(' ');
  return <main className={cls}>{children}</main>;
};

const Layout: React.FC<LayoutProps> & {
  Header: typeof Header;
  Sider: typeof Sider;
  Content: typeof Content;
} = ({ children, className }) => {
  const cls = [styles['ds-layout'], className].filter(Boolean).join(' ');
  return <div className={cls}>{children}</div>;
};

Layout.Header = Header;
Layout.Sider = Sider;
Layout.Content = Content;

export default Layout;
