import React from 'react';
import { useNavigate } from 'react-router-dom';

interface Props {
  children: React.ReactNode;
}

interface State {
  hasError: boolean;
  error: Error | null;
}

/**
 * P1-2: 全局 Error Boundary。
 * 捕获子组件渲染异常，显示降级 UI（错误提示 + 重试 + 返回首页），
 * 防止整页白屏。包裹 <Routes> 整体，懒加载 chunk 失败同样被捕获。
 */
export default class ErrorBoundary extends React.Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, info: React.ErrorInfo) {
    // 预留扩展点：可接入错误上报服务
    console.error('[ErrorBoundary] 渲染异常:', error, info.componentStack);
  }

  handleRetry = () => {
    this.setState({ hasError: false, error: null });
  };

  render() {
    if (this.state.hasError) {
      return <ErrorFallback error={this.state.error} onRetry={this.handleRetry} />;
    }
    return this.props.children;
  }
}

function ErrorFallback({ error, onRetry }: { error: Error | null; onRetry: () => void }) {
  const navigate = useNavigate();

  return (
    <div style={{
      display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center',
      minHeight: '50vh', padding: '2rem', textAlign: 'center',
      color: 'var(--ds-color-text-primary, #1f2937)',
    }}>
      <div style={{
        fontSize: 'var(--ds-font-size-2xl, 1.5rem)', fontWeight: 600,
        marginBottom: '0.75rem',
        color: 'var(--ds-color-text-error, #dc2626)',
      }}>
        页面出现异常
      </div>
      <p style={{
        fontSize: 'var(--ds-font-size-sm, 0.875rem)',
        color: 'var(--ds-color-text-tertiary, #6b7280)',
        maxWidth: '480px', marginBottom: '1.5rem',
      }}>
        {error?.message || '渲染过程中发生了未知错误，请尝试刷新页面。'}
      </p>
      <div style={{ display: 'flex', gap: '0.75rem' }}>
        <button
          onClick={onRetry}
          style={{
            padding: '0.5rem 1.25rem', borderRadius: '6px',
            border: '1px solid var(--ds-color-border-default, #d1d5db)',
            background: 'var(--ds-color-surface-primary, #fff)',
            color: 'var(--ds-color-text-primary, #1f2937)',
            cursor: 'pointer', fontSize: 'var(--ds-font-size-sm, 0.875rem)',
          }}
        >
          重试
        </button>
        <button
          onClick={() => { navigate('/'); onRetry(); }}
          style={{
            padding: '0.5rem 1.25rem', borderRadius: '6px',
            border: 'none',
            background: 'var(--ds-color-action-primary, #2563eb)',
            color: '#fff',
            cursor: 'pointer', fontSize: 'var(--ds-font-size-sm, 0.875rem)',
          }}
        >
          返回首页
        </button>
      </div>
    </div>
  );
}
