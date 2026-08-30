import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';

import { Layout } from './components/layout/Layout';
import { DashboardPage } from './pages/DashboardPage';
import { DatasetsPage } from './pages/DatasetsPage';
import { AlertsPage } from './pages/AlertsPage';
import { EntitySearchPage } from './pages/EntitySearchPage';
import { EntityDetailPage } from './pages/EntityDetailPage';
import { GraphExplorerPage } from './pages/GraphExplorerPage';
import { ClustersPage } from './pages/ClustersPage';
import { ModelsPage } from './pages/ModelsPage';
import { ReportsPage } from './pages/ReportsPage';
import { SettingsPage } from './pages/SettingsPage';

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      refetchOnWindowFocus: false,
      staleTime: 5000,
      retry: 1,
    },
  },
});

export const App: React.FC = () => {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<Layout />}>
            <Route index element={<DashboardPage />} />
            <Route path="datasets" element={<DatasetsPage />} />
            <Route path="alerts" element={<AlertsPage />} />
            <Route path="search" element={<EntitySearchPage />} />
            <Route path="entities/:entityId" element={<EntityDetailPage />} />
            <Route path="graph" element={<GraphExplorerPage />} />
            <Route path="clusters" element={<ClustersPage />} />
            <Route path="models" element={<ModelsPage />} />
            <Route path="reports" element={<ReportsPage />} />
            <Route path="settings" element={<SettingsPage />} />
            <Route path="*" element={<Navigate to="/" replace />} />
          </Route>
        </Routes>
      </BrowserRouter>
    </QueryClientProvider>
  );
};
