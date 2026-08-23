import React from 'react';
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { AuthProvider } from './context/AuthContext';
import { DatasetProvider } from './context/DatasetContext';
import Layout from './components/layout/Layout';
import HeroPage from './pages/HeroPage';
import DashboardPage from './pages/DashboardPage';
import UploadPage from './pages/UploadPage';
import AccountsPage from './pages/AccountsPage';
import ExplainabilityPage from './pages/ExplainabilityPage';
import GraphPage from './pages/GraphPage';
import AlertsPage from './pages/AlertsPage';
import ModelMetricsPage from './pages/ModelMetricsPage';
import FeatureIntelligencePage from './pages/FeatureIntelligencePage';
import AnomalyDetectionPage from './pages/AnomalyDetectionPage';
import ModelMonitoringPage from './pages/ModelMonitoringPage';
import RealTimeDetectionPage from './pages/RealTimeDetectionPage';
import SimulationPage from './pages/SimulationPage';

export default function App() {
  return (
    <AuthProvider>
      <DatasetProvider>
        <BrowserRouter>
          <Routes>
            <Route element={<Layout />}>
              <Route path="/" element={<HeroPage />} />
              <Route path="/dashboard" element={<DashboardPage />} />
              <Route path="/stream" element={<RealTimeDetectionPage />} />
              <Route path="/upload" element={<UploadPage />} />
              <Route path="/accounts" element={<AccountsPage />} />
              <Route path="/anomaly" element={<AnomalyDetectionPage />} />
              <Route path="/features" element={<FeatureIntelligencePage />} />
              <Route path="/explain" element={<ExplainabilityPage />} />
              <Route path="/graph" element={<GraphPage />} />
              <Route path="/alerts" element={<AlertsPage />} />
              <Route path="/metrics" element={<ModelMetricsPage />} />
              <Route path="/monitoring" element={<ModelMonitoringPage />} />
              <Route path="/simulation" element={<SimulationPage />} />
            </Route>
          </Routes>
        </BrowserRouter>
      </DatasetProvider>
    </AuthProvider>
  );
}



