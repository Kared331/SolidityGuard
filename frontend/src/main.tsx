import React, { Suspense, lazy } from 'react';
import ReactDOM from 'react-dom/client';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import AppShell from './layouts/AppShell/AppShell';
import ToastContainer from './components/Toast/ToastContainer';

/* ===== Design Tokens & Global Styles ===== */
import './design-system/tokens/index.css';
import './styles/reset.css';
import './styles/global.css';

/* ===== Lazy Loaded Pages ===== */
const DashboardPage = lazy(() => import('./pages/Dashboard/DashboardPage'));
const UploadPage = lazy(() => import('./pages/Upload/UploadPage'));
const ProjectDetailPage = lazy(() => import('./pages/ProjectDetail/ProjectDetailPage'));
const LLMAuditPage = lazy(() => import('./pages/LLMAudit/LLMAuditPage'));
const ReportPage = lazy(() => import('./pages/Report/ReportPage'));
const VulnerabilitiesPage = lazy(() => import('./pages/Vulnerabilities/VulnerabilitiesPage'));

/* ===== React Query Client ===== */
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 30_000,
      retry: 1,
      refetchOnWindowFocus: false,
    },
  },
});

/* ===== Page Loading Fallback ===== */
function PageLoading() {
  return (
    <div style={{
      display: 'flex', alignItems: 'center', justifyContent: 'center',
      height: '60vh', color: 'var(--ds-color-text-tertiary)',
      fontSize: 'var(--ds-font-size-sm)',
    }}>
      加载中...
    </div>
  );
}

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <ToastContainer />
        <Suspense fallback={<PageLoading />}>
          <Routes>
            <Route path="/" element={<Navigate to="/dashboard" replace />} />
            <Route element={<AppShell />}>
              <Route path="/dashboard" element={<DashboardPage />} />
              <Route path="/upload" element={<UploadPage />} />
              <Route path="/projects/:id" element={<ProjectDetailPage />} />
              <Route path="/projects/:id/report" element={<ReportPage />} />
              <Route path="/projects/:id/llm-audit" element={<LLMAuditPage />} />
              <Route path="/vulnerabilities" element={<VulnerabilitiesPage />} />
            </Route>
          </Routes>
        </Suspense>
      </BrowserRouter>
    </QueryClientProvider>
  </React.StrictMode>
);
