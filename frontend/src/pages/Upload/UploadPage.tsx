import React, { useState, useRef, useCallback, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';
import { Button, Card, Icon, Spinner, Tag } from '../../design-system';
import { useProjects, useCreateProject } from '../../api/hooks/useProjects';
import { formatDate, formatFileSize } from '../../utils/format';
import styles from './UploadPage.module.css';

type UploadPhase = 'idle' | 'file-selected' | 'uploading' | 'success' | 'error';

export default function UploadPage() {
  const navigate = useNavigate();
  const fileInputRef = useRef<HTMLInputElement>(null);
  const { data: projects } = useProjects();
  const createProject = useCreateProject();

  const [file, setFile] = useState<File | null>(null);
  const [phase, setPhase] = useState<UploadPhase>('idle');
  const [errorMessage, setErrorMessage] = useState('');
  const [isDragOver, setIsDragOver] = useState(false);

  const recentProjects = useMemo(() => {
    if (!projects) return [];
    return [...projects]
      .sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime())
      .slice(0, 5);
  }, [projects]);

  const handleFile = useCallback((f: File | null) => {
    if (!f) return;
    // P2-5: 上传前预校验文件大小（与 nginx client_max_body_size 50m 对齐，避免先传后拒）
    const MAX_UPLOAD_SIZE = 50 * 1024 * 1024; // 50MB
    if (f.size > MAX_UPLOAD_SIZE) {
      setFile(null);
      setPhase('error');
      setErrorMessage(`文件大小 ${formatFileSize(f.size)} 超过 50MB 限制`);
      return;
    }
    setFile(f);
    setPhase('file-selected');
    setErrorMessage('');
  }, []);

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      setIsDragOver(false);
      const dropped = e.dataTransfer?.files?.[0] ?? null;
      handleFile(dropped);
    },
    [handleFile],
  );

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(true);
  }, []);

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(false);
  }, []);

  const handleInputChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const f = e.target?.files?.[0] ?? null;
      handleFile(f);
    },
    [handleFile],
  );

  const handleUpload = useCallback(async () => {
    if (!file) return;
    setPhase('uploading');
    setErrorMessage('');

    const formData = new FormData();
    formData.append('files', file);

    try {
      const result = await createProject.mutateAsync(formData);
      setPhase('success');
      // Navigate after a brief delay so user can see success
      setTimeout(() => {
        navigate(`/projects/${result.id}`);
      }, 800);
    } catch (err: unknown) {
      setPhase('error');

      let message = '上传失败，请重试';

      if (axios.isAxiosError(err) && err.response) {
        const status = err.response.status;
        if (status === 413) {
          message = '文件大小超过限制（最大 50MB）';
        } else if (status === 422) {
          // Try to extract detailed validation errors from response
          const data = err.response.data;
          if (data?.errors && Array.isArray(data.errors) && data.errors.length > 0) {
            message = data.errors.map((e: { field: string; message: string }) => `${e.field}: ${e.message}`).join('; ');
          } else if (data?.detail) {
            message = String(data.detail);
          } else {
            message = '文件格式不支持或请求参数有误';
          }
        } else if (status >= 500) {
          message = '服务端错误，请稍后重试';
        } else if (err.response.data?.detail) {
          message = String(err.response.data.detail);
        }
      } else if (err instanceof TypeError && err.message === 'Failed to fetch') {
        message = '网络连接失败，请检查网络后重试';
      } else if (err instanceof Error) {
        message = err.message;
      }

      setErrorMessage(message);
    }
  }, [file, createProject, navigate]);

  const handleReset = useCallback(() => {
    setFile(null);
    setPhase('idle');
    setErrorMessage('');
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  }, []);

  /* ---- Status mapping for recent project tags ---- */
  const STATUS_TAG_MAP: Record<string, { variant: 'success' | 'info' | 'critical' | 'neutral'; label: string }> = {
    ready: { variant: 'success', label: '就绪' },
    analyzing: { variant: 'info', label: '分析中' },
    failed: { variant: 'critical', label: '失败' },
  };
  function getStatusConfig(status: string) {
    return STATUS_TAG_MAP[status] ?? { variant: 'neutral' as const, label: status };
  }

  /* ---- Render helpers ---- */
  const renderDropzoneContent = () => {
    switch (phase) {
      case 'idle':
        return (
          <>
            <div className={styles['upload__dropzone-icon']}>
              <Icon name="upload" size={48} />
            </div>
            <p className={styles['upload__dropzone-text']}>
              拖拽 .sol / .zip / .tar.gz 文件到此处
            </p>
            <p className={styles['upload__dropzone-sub']}>或点击选择文件</p>
          </>
        );

      case 'file-selected':
        return (
          <div className={styles['upload__file-preview']}>
            <div className={styles['upload__file-name']}>
              <Icon name="file" size={20} />
              <span>{file!.name}</span>
            </div>
            <span className={styles['upload__file-size']}>
              {formatFileSize(file!.size)}
            </span>
            <Button variant="brand" onClick={handleUpload}>
              上传
            </Button>
          </div>
        );

      case 'uploading':
        return (
          <div className={styles['upload__uploading']}>
            <Spinner size="lg" />
            <span>正在上传...</span>
          </div>
        );

      case 'success':
        return (
          <div className={styles['upload__success']}>
            <Icon name="check" size={32} color="var(--ds-color-success)" />
            <span>上传成功，正在跳转...</span>
          </div>
        );

      case 'error':
        return (
          <div className={styles['upload__error']}>
            <Icon name="alert-circle" size={32} color="var(--ds-color-critical)" />
            <span>{errorMessage}</span>
            <div style={{ display: 'flex', gap: 'var(--ds-space-2)' }}>
              <Button variant="secondary" onClick={handleReset}>
                重新选择
              </Button>
              <Button variant="primary" onClick={handleUpload}>
                重试
              </Button>
            </div>
          </div>
        );

      default:
        return null;
    }
  };

  return (
    <div>
      <h1 className={`ds-text-2xl ${styles['upload__title']}`}>上传智能合约</h1>

      {/* ---- Dropzone ---- */}
      <Card padding="default">
        <div
          className={`${styles['upload__dropzone']} ${
            isDragOver ? styles['upload__dropzone--active'] : ''
          }`}
          onDragOver={handleDragOver}
          onDragLeave={handleDragLeave}
          onDrop={handleDrop}
          onClick={() => {
            if (phase === 'idle' || phase === 'error') {
              fileInputRef.current?.click();
            }
          }}
          role="button"
          tabIndex={0}
          onKeyDown={(e) => {
            if (e.key === 'Enter' || e.key === ' ') {
              e.preventDefault();
              fileInputRef.current?.click();
            }
          }}
        >
          {renderDropzoneContent()}
        </div>
        <input
          ref={fileInputRef}
          type="file"
          accept=".sol,.zip,.tar.gz,application/x-gzip"
          style={{ display: 'none' }}
          onChange={handleInputChange}
        />
      </Card>

      {/* ---- Recent Projects ---- */}
      <div className={styles['upload__recent']}>
        <h2 className={styles['upload__recent-title']}>最近项目</h2>
        {recentProjects.length === 0 ? (
          <div className={styles['upload__recent-empty']}>暂无项目</div>
        ) : (
          <div className={styles['upload__recent-list']}>
            {recentProjects.map((project) => {
              const sc = getStatusConfig(project.status);
              return (
                <div key={project.id} className={styles['upload__recent-item']}>
                  <span
                    className={styles['upload__recent-item-name']}
                    onClick={() => navigate(`/projects/${project.id}`)}
                    role="link"
                    tabIndex={0}
                    onKeyDown={(e) => {
                      if (e.key === 'Enter' || e.key === ' ') {
                        e.preventDefault();
                        navigate(`/projects/${project.id}`);
                      }
                    }}
                  >
                    {project.name}
                  </span>
                  <div className={styles['upload__recent-item-right']}>
                    <span className={styles['upload__recent-item-date']}>
                      {formatDate(project.created_at)}
                    </span>
                    <Tag variant={sc.variant} size="sm">
                      {sc.label}
                    </Tag>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}
