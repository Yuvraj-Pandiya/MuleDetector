import React from 'react';
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import Layout from './components/layout/Layout';
import HeroPage from './pages/HeroPage';
import DashboardPage from './pages/DashboardPage';
import UploadPage from './pages/UploadPage';
import AccountsPage from './pages/AccountsPage';
import ExplainabilityPage from './pages/ExplainabilityPage';
import GraphPage from './pages/GraphPage';
import AlertsPage from './pages/AlertsPage';
import ModelMetricsPage from './pages/ModelMetricsPage';
import SimulationPage from './pages/SimulationPage';

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route element={<Layout />}>
          <Route path="/" element={<HeroPage />} />
          <Route path="/dashboard" element={<DashboardPage />} />
          <Route path="/upload" element={<UploadPage />} />
          <Route path="/accounts" element={<AccountsPage />} />
          <Route path="/explain" element={<ExplainabilityPage />} />
          <Route path="/graph" element={<GraphPage />} />
          <Route path="/alerts" element={<AlertsPage />} />
          <Route path="/metrics" element={<ModelMetricsPage />} />
          <Route path="/simulation" element={<SimulationPage />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}
