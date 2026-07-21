import React, { useCallback } from 'react';
import styles from './Tabs.module.css';

export interface TabItem {
  key: string;
  label: string;
  content?: React.ReactNode;
}

export interface TabsProps {
  items: TabItem[];
  activeKey?: string;
  onChange?: (key: string) => void;
  className?: string;
}

const Tabs: React.FC<TabsProps> = ({ items, activeKey, onChange, className }) => {
  const [internalActive, setInternalActive] = React.useState<string>(
    activeKey ?? (items.length > 0 ? items[0].key : '')
  );

  const currentKey = activeKey !== undefined ? activeKey : internalActive;

  const handleTabClick = useCallback(
    (key: string) => {
      if (onChange) {
        onChange(key);
      }
      if (activeKey === undefined) {
        setInternalActive(key);
      }
    },
    [onChange, activeKey]
  );

  const activeItem = items.find((item) => item.key === currentKey);

  const tabBarClass = className
    ? `${styles['ds-tabs']} ${className}`
    : styles['ds-tabs'];

  return (
    <div className={tabBarClass}>
      <div className={styles['ds-tabs-bar']} role="tablist">
        {items.map((item) => (
          <button
            key={item.key}
            role="tab"
            aria-selected={item.key === currentKey}
            className={`${styles['ds-tabs-tab']} ${
              item.key === currentKey ? styles['ds-tabs-tab--active'] : ''
            }`}
            onClick={() => handleTabClick(item.key)}
            type="button"
            tabIndex={item.key === currentKey ? 0 : -1}
          >
            {item.label}
          </button>
        ))}
      </div>
      {activeItem?.content !== undefined && (
        <div
          className={styles['ds-tabs-content']}
          role="tabpanel"
          aria-labelledby={activeItem.key}
        >
          {activeItem.content}
        </div>
      )}
    </div>
  );
};

export default Tabs;
