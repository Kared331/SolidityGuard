import React from 'react';
import ReactDOM from 'react-dom/client';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import App from './App';
import UploadPage from './pages/UploadPage';
import ProjectDetailPage from './pages/ProjectDetailPage';
import ReportPage from './pages/ReportPage';
import VulnerabilitiesPage from './pages/VulnerabilitiesPage';

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Navigate to="/upload" replace />} />
        <Route element={<App />}>
          <Route path="/upload" element={<UploadPage />} />
          <Route path="/projects/:id" element={<ProjectDetailPage />} />
          <Route path="/projects/:id/report" element={<ReportPage />} />
          <Route path="/vulnerabilities" element={<VulnerabilitiesPage />} />
        </Route>
      </Routes>
    </BrowserRouter>
  </React.StrictMode>
);
