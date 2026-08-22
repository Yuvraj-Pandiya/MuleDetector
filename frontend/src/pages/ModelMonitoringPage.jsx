import React, { useState, useEffect } from 'react';
import {
  Activity, ShieldAlert, AlertTriangle, CheckCircle2, XCircle,
  Clock, Calendar, RefreshCw, Layers, TrendingUp, Cpu, BarChart2
} from 'lucide-react';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';
import { getModelMonitoring } from '../api/client';
import './ModelMonitoringPage.css';

export default function ModelMonitoringPage() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);

  const loadMonitoringData = async () => {
    setLoading(true);
    try {
      const res = await getModelMonitoring();
      setData(res);
    } catch (err) {
      console.error('Failed to load model monitoring data:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadMonitoringData();
  }, []);

  if (loading || !data) {
    return (
      <div className="monitoring-page animate-fade-in">
        <div className="loading-state">Fetching model health, PSI feature drift metrics, and prediction shifts...</div>
      </div>
    );
  }

  const getStatusBadge = (status) => {
    switch (status) {
      case 'NORMAL':
        return (
          <span className="status-chip normal flex-align gap-xs">
            <CheckCircle2 size={12} /> NORMAL
          </span>
        );
      case 'WARNING':
        return (
          <span className="status-chip warning flex-align gap-xs">
            <AlertTriangle size={12} /> WARNING
          </span>
        );
      case 'CRITICAL':
        return (
          <span className="status-chip critical flex-align gap-xs">
            <XCircle size={12} /> CRITICAL
          </span>
        );
      default:
        return <span className="status-chip normal">{status}</span>;
    }
  };

  const getSeverityBadge = (severity) => {
    switch (severity) {
      case 'LOW':
        return <span className="severity-tag low">LOW DRIFT SEVERITY</span>;
      case 'MODERATE':
        return <span className="severity-tag moderate">MODERATE DRIFT SEVERITY</span>;
      case 'HIGH':
        return <span className="severity-tag high font-bold">HIGH DRIFT SEVERITY</span>;
      default:
        return <span className="severity-tag low">{severity}</span>;
    }
  };

  return (
    <div className="monitoring-page animate-fade-in">
      {/* Page Header */}
      <div className="page-head flex-between">
        <div>
          <h2>Model Health & Feature Drift Monitoring</h2>
          <p>Real-time population stability index (PSI) tracking and inference prediction distribution shift audit.</p>
        </div>

        <button className="btn-secondary flex-align gap-xs" onClick={loadMonitoringData}>
          <RefreshCw size={14} /> Refresh Monitoring Stats
        </button>
      </div>

      {/* Overview Cards Strip */}
      <div className="monitoring-kpi-grid margin-top-xs">
        <div className="dash-card metric-kpi-card">
          <div className="kpi-inner">
            <div className="kpi-head-sm">
              <span className="label">Current Model Version</span>
              <Cpu size={16} className="text-teal" />
            </div>
            <span className="val font-mono text-teal">{data.model_version}</span>
            <span className="sub flex-align gap-xs">
              <Calendar size={12} /> Trained: {new Date(data.training_date).toLocaleDateString()}
            </span>
          </div>
        </div>

        <div className="dash-card metric-kpi-card">
          <div className="kpi-inner">
            <div className="kpi-head-sm">
              <span className="label">Latest Scoring Date</span>
              <Clock size={16} className="text-purple" />
            </div>
            <span className="val font-mono text-ink text-sm">
              {new Date(data.latest_scoring_date).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
            </span>
            <span className="sub">{new Date(data.latest_scoring_date).toLocaleDateString()}</span>
          </div>
        </div>

        <div className="dash-card metric-kpi-card">
          <div className="kpi-inner">
            <div className="kpi-head-sm">
              <span className="label">Feature Drift Status</span>
              <Activity size={16} className={data.feature_drift_status === 'NORMAL' ? 'text-success' : 'text-warning'} />
            </div>
            <div className="flex-align gap-xs margin-top-xs">
              {getStatusBadge(data.feature_drift_status)}
            </div>
            <span className="sub margin-top-xs">Population Stability Index (PSI)</span>
          </div>
        </div>

        <div className="dash-card metric-kpi-card">
          <div className="kpi-inner">
            <div className="kpi-head-sm">
              <span className="label">Drift Severity & Overall PSI</span>
              <ShieldAlert size={16} className={data.drift_severity === 'HIGH' ? 'text-danger' : 'text-warning'} />
            </div>
            <span className="val font-mono text-stone">{data.overall_psi.toFixed(3)} PSI</span>
            <div className="margin-top-xs">{getSeverityBadge(data.drift_severity)}</div>
          </div>
        </div>
      </div>

      {/* Prediction Distribution Drift Chart */}
      <div className="section-card margin-top-xs">
        <div className="card-head flex-between">
          <div>
            <h3>Prediction Probability Distribution Shift</h3>
            <p className="card-sub">Comparison of inference prediction score frequencies: Baseline Training vs Current Scoring Batch</p>
          </div>
        </div>

        <div className="chart-container margin-top-xs">
          <ResponsiveContainer width="100%" height={260}>
            <BarChart data={data.prediction_distribution} margin={{ top: 15, right: 30, left: 10, bottom: 15 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#242728" vertical={false} />
              <XAxis dataKey="range" stroke="#6a6b6c" fontSize={11} />
              <YAxis stroke="#6a6b6c" fontSize={11} unit="%" />
              <Tooltip contentStyle={{ background: '#0d0d0d', borderColor: 'rgba(255,255,255,0.16)', borderRadius: 8, color: '#f4f4f6', fontSize: 12 }} />
              <Legend wrapperStyle={{ fontSize: 11, paddingTop: 10 }} />
              <Bar dataKey="training_pct" name="Training Baseline (%)" fill="#3b82f6" radius={[4, 4, 0, 0]} />
              <Bar dataKey="current_pct" name="Current Inference (%)" fill="#14b8a6" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Monitored Features Drift Table */}
      <div className="section-card margin-top-xs">
        <div className="card-head flex-between">
          <div>
            <h3>Monitored Feature Population Stability & Drift Audit</h3>
            <p className="card-sub">PSI threshold monitoring: Normal (&lt;0.10), Warning (0.10–0.25), Critical (&ge;0.25)</p>
          </div>
        </div>

        <div className="table-responsive margin-top-xs">
          <table className="mini-table drift-table">
            <thead>
              <tr>
                <th>Feature</th>
                <th>Training Baseline Distribution</th>
                <th>Current Scoring Distribution</th>
                <th>Drift Metric (PSI)</th>
                <th>Status</th>
                <th>Drift Note / Impact</th>
              </tr>
            </thead>
            <tbody>
              {data.monitored_features.map((feat, idx) => {
                const isCrit = feat.status === 'CRITICAL';
                const isWarn = feat.status === 'WARNING';

                return (
                  <tr key={idx} className={isCrit ? 'critical-row' : isWarn ? 'warning-row' : ''}>
                    <td>
                      <div className="feature-cell">
                        <span className="font-mono font-bold text-ink">{feat.feature}</span>
                      </div>
                    </td>
                    <td>
                      <span className="font-mono text-stone text-xs">{feat.training_distribution}</span>
                    </td>
                    <td>
                      <span className="font-mono text-teal text-xs font-semibold">{feat.current_distribution}</span>
                    </td>
                    <td>
                      <div className="metric-bar-cell">
                        <span className="font-mono font-bold text-ink">
                          {feat.drift_metric.toFixed(3)} {feat.metric_name}
                        </span>
                        <div className="mini-progress-bg">
                          <div
                            className={`mini-progress-fill ${isCrit ? 'danger' : isWarn ? 'warning' : 'teal'}`}
                            style={{ width: `${Math.min(100, feat.drift_metric * 300)}%` }}
                          />
                        </div>
                      </div>
                    </td>
                    <td>{getStatusBadge(feat.status)}</td>
                    <td>
                      <p className="drift-desc-text">{feat.description}</p>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
