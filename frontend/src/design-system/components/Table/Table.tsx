import React, { useCallback, useMemo, useState } from 'react';
import styles from './Table.module.css';

export interface TableColumn<T = Record<string, any>> {
  key: string;
  title: string;
  dataIndex: string;
  sortable?: boolean;
  render?: (value: any, record: T, index: number) => React.ReactNode;
  width?: string;
}

export interface PaginationConfig {
  current: number;
  pageSize: number;
  total: number;
  onChange: (page: number, pageSize: number) => void;
}

export interface TableProps<T = Record<string, any>> {
  columns: TableColumn<T>[];
  dataSource: T[];
  loading?: boolean;
  emptyText?: string;
  onRowClick?: (record: T, index: number) => void;
  rowKey?: string | ((record: T) => string);
  pagination?: PaginationConfig;
  className?: string;
}

type SortDirection = 'asc' | 'desc' | null;

interface SortState {
  key: string;
  direction: SortDirection;
}

function getRowKey<T>(record: T, index: number, rowKey?: string | ((record: T) => string)): string {
  if (typeof rowKey === 'function') {
    return rowKey(record);
  }
  if (typeof rowKey === 'string' && typeof record === 'object' && record !== null) {
    return String((record as any)[rowKey] ?? index);
  }
  return String(index);
}

function TableComponent<T extends Record<string, any>>({
  columns,
  dataSource,
  loading = false,
  emptyText = '暂无数据',
  onRowClick,
  rowKey,
  pagination,
  className,
}: TableProps<T>) {
  const [sortState, setSortState] = useState<SortState>({ key: '', direction: null });

  const handleSort = useCallback(
    (column: TableColumn<T>) => {
      if (!column.sortable) return;

      setSortState((prev) => {
        if (prev.key !== column.key) {
          return { key: column.key, direction: 'asc' };
        }
        if (prev.direction === 'asc') {
          return { key: column.key, direction: 'desc' };
        }
        return { key: '', direction: null };
      });
    },
    []
  );

  const sortedData = useMemo(() => {
    if (!sortState.key || !sortState.direction) return dataSource;

    return [...dataSource].sort((a, b) => {
      const aVal = a[sortState.key];
      const bVal = b[sortState.key];

      if (aVal == null && bVal == null) return 0;
      if (aVal == null) return 1;
      if (bVal == null) return -1;

      let comparison = 0;
      if (typeof aVal === 'number' && typeof bVal === 'number') {
        comparison = aVal - bVal;
      } else if (typeof aVal === 'string' && typeof bVal === 'string') {
        comparison = aVal.localeCompare(bVal);
      } else {
        comparison = String(aVal).localeCompare(String(bVal));
      }

      return sortState.direction === 'desc' ? -comparison : comparison;
    });
  }, [dataSource, sortState]);

  const totalPages = pagination ? Math.ceil(pagination.total / pagination.pageSize) : 0;

  const pageNumbers = useMemo(() => {
    if (totalPages <= 7) {
      return Array.from({ length: totalPages }, (_, i) => i + 1);
    }
    const pages: (number | 'ellipsis')[] = [];
    const current = pagination!.current;

    pages.push(1);
    if (current > 3) pages.push('ellipsis');

    const start = Math.max(2, current - 1);
    const end = Math.min(totalPages - 1, current + 1);
    for (let i = start; i <= end; i++) {
      pages.push(i);
    }

    if (current < totalPages - 2) pages.push('ellipsis');
    pages.push(totalPages);

    return pages;
  }, [totalPages, pagination]);

  const sortIndicator = (column: TableColumn<T>) => {
    if (!column.sortable) return null;
    const isActive = sortState.key === column.key;
    const isAsc = isActive && sortState.direction === 'asc';
    const isDesc = isActive && sortState.direction === 'desc';

    return (
      <span className={styles['ds-table-sort']}>
        <span
          className={`${styles['ds-table-sort-arrow']} ${
            isAsc ? styles['ds-table-sort-arrow--active'] : ''
          }`}
        >
          ▲
        </span>
        <span
          className={`${styles['ds-table-sort-arrow']} ${
            isDesc ? styles['ds-table-sort-arrow--active'] : ''
          }`}
        >
          ▼
        </span>
      </span>
    );
  };

  const tableClass = className
    ? `${styles['ds-table-wrapper']} ${className}`
    : styles['ds-table-wrapper'];

  const hasData = sortedData.length > 0;

  return (
    <div className={tableClass}>
      <div className={styles['ds-table-container']}>
        <table className={styles['ds-table']}>
          <thead>
            <tr>
              {columns.map((col) => (
                <th
                  key={col.key}
                  className={`${styles['ds-table-th']} ${
                    col.sortable ? styles['ds-table-th--sortable'] : ''
                  }`}
                  style={col.width ? { width: col.width } : undefined}
                  onClick={() => handleSort(col)}
                >
                  <span className={styles['ds-table-th-content']}>
                    {col.title}
                    {sortIndicator(col)}
                  </span>
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {!hasData && !loading && (
              <tr>
                <td colSpan={columns.length} className={styles['ds-table-empty']}>
                  {emptyText}
                </td>
              </tr>
            )}
            {hasData &&
              sortedData.map((record, index) => (
                <tr
                  key={getRowKey(record, index, rowKey)}
                  className={`${styles['ds-table-row']} ${
                    onRowClick ? styles['ds-table-row--clickable'] : ''
                  }`}
                  onClick={() => onRowClick?.(record, index)}
                >
                  {columns.map((col) => (
                    <td key={col.key} className={styles['ds-table-td']}>
                      {col.render
                        ? col.render(record[col.dataIndex], record, index)
                        : record[col.dataIndex] ?? ''}
                    </td>
                  ))}
                </tr>
              ))}
          </tbody>
        </table>

        {loading && (
          <div className={styles['ds-table-loading-overlay']}>
            <div className={styles['ds-table-spinner']} />
          </div>
        )}
      </div>

      {pagination && totalPages > 1 && (
        <div className={styles['ds-table-pagination']}>
          <span className={styles['ds-table-pagination-info']}>
            共 {pagination.total} 条
          </span>
          <div className={styles['ds-table-pagination-buttons']}>
            <button
              className={styles['ds-table-pagination-btn']}
              disabled={pagination.current <= 1}
              onClick={() => pagination.onChange(pagination.current - 1, pagination.pageSize)}
              type="button"
            >
              ‹
            </button>
            {pageNumbers.map((page, idx) =>
              page === 'ellipsis' ? (
                <span key={`ellipsis-${idx}`} className={styles['ds-table-pagination-ellipsis']}>
                  …
                </span>
              ) : (
                <button
                  key={page}
                  className={`${styles['ds-table-pagination-btn']} ${
                    page === pagination.current
                      ? styles['ds-table-pagination-btn--active']
                      : ''
                  }`}
                  onClick={() => pagination.onChange(page as number, pagination.pageSize)}
                  type="button"
                >
                  {page}
                </button>
              )
            )}
            <button
              className={styles['ds-table-pagination-btn']}
              disabled={pagination.current >= totalPages}
              onClick={() => pagination.onChange(pagination.current + 1, pagination.pageSize)}
              type="button"
            >
              ›
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

export default TableComponent;
