import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  AlertTriangle, Activity, ShieldAlert, BarChart3, Users,
  TrendingUp, ArrowUpDown, ChevronRight, RefreshCw, Zap, Layers, Search
} from 'lucide-react';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Cell } from 'recharts';
import { getAnomalySummary } from '../api/client';
import './AnomalyDetectionPage.css';

export default function AnomalyDetectionPage() {
  const navigate = useNavigate();
  const [summary, setSummary] = useState(null);
  const [loading, setLoading] = useState(true);
  const [sortBy, setSortBy] = useState('highest_anomaly');
  const [minAnomaly, setMinAnomaly] = useState('');
  const [page, setPage] = useState(1);

  const loadAnomalyData = async () => {
    setLoading(true);
    try {
      const params = {
        page,
        page_size: 15,
        sort_by: sortBy,
      };
      if (minAnomaly !== '') {
        params.min_anomaly = parseFloat(minAnomaly);
      }
      const data = await getAnomalySummary(params);
      setSummary(data);
    } catch (err) {
      console.error('Failed to load anomaly detection summary:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadAnomalyData();
  }, [page, sortBy, minAnomaly]);

  const handleAccountClick = (accountId) => {
    navigate(`/explain?account_id=${accountId}`);
  };

  if (loading || !summary) {
    return (
      <div className="anomaly-page animate-fade-in">
        <div className="loading-state">Evaluating Isolation Forest unsupervised anomaly distribution...</div>
      </div>
    );
  }

  const kpis = [
    {
      label: 'Total Accounts Analyzed',
      val: summary.total_accounts_analyzed.toLocaleString(),
      sub: 'Isolation Forest feature space audit',
      icon: Users,
      color: 'teal',
    },
    {
      label: 'Anomalous Accounts',
      val: summary.anomalous_accounts.toLocaleString(),
      sub: 'Score >= 0.50 (Unsupervised flag)',
      icon: AlertTriangle,
      color: 'warning',
    },
    {
      label: 'Anomaly Rate',
      val: `${summary.anomaly_rate.toFixed(2)}%`,
      sub: 'Proportion of population flagged',
      icon: Activity,
      color: 'purple',
    },
    {
      label: 'Average Anomaly Score',
      val: summary.average_anomaly_score.toFixed(3),
      sub: 'Mean distance from baseline cluster',
      icon: BarChart3,
      color: 'blue',
    },
    {
      label: 'High Anomaly Accounts',
      val: summary.high_anomaly_accounts.toLocaleString(),
      sub: 'Critical outliers (Score >= 0.70)',
      icon: ShieldAlert,
      color: 'danger',
    },
  ];

  return (
    <div className="anomaly-page animate-fade-in">
      {/* Header */}
      <div className="page-head flex-between">
        <div>
          <h2>Unsupervised Anomaly Detection Intelligence</h2>
          <p>Isolation Forest multivariate outlier scoring and account behavior variance analysis.</p>
        </div>

        <button className="btn-secondary flex-align gap-xs" onClick={loadAnomalyData}>
          <RefreshCw size={14} /> Refresh Anomaly Data
        </button>
      </div>

      {/* KPI Cards Strip */}
      <div className="anomaly-kpi-grid margin-top-xs">
        {kpis.map((k, i) => {
          const Icon = k.icon;
          return (
            <div key={i} className="dash-card metric-kpi-card">
              <div className="kpi-inner">
                <div className="kpi-head-sm">
                  <span className="label">{k.label}</span>
                  <Icon size={16} className={`text-${k.color}`} />
                </div>
                <span className={`val text-${k.color}`}>{k.val}</span>
                <span className="sub">{k.sub}</span>
              </div>
            </div>
          );
        })}
      </div>

      {/* Anomaly Distribution Chart Section */}
      <div className="section-card margin-top-xs">
        <div className="card-head flex-between">
          <div>
            <h3>Isolation Forest Anomaly Score Distribution</h3>
            <p className="card-sub">Frequency histogram of account anomaly scores (0.0 = Normal, 1.0 = Outlier)</p>
          </div>
        </div>

        <div className="chart-container margin-top-xs">
          <ResponsiveContainer width="100%" height={240}>
            <BarChart data={summary.distribution} margin={{ top: 10, right: 30, left: 10, bottom: 10 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#242728" vertical={false} />
              <XAxis dataKey="range" stroke="#6a6b6c" fontSize={11} />
              <YAxis stroke="#6a6b6c" fontSize={11} />
              <Tooltip contentStyle={{ background: '#0d0d0d', borderColor: 'rgba(255,255,255,0.16)', borderRadius: 8, color: '#f4f4f6', fontSize: 12 }} />
              <Bar dataKey="count" radius={[4, 4, 0, 0]}>
                {summary.distribution.map((entry, index) => {
                  let fill = '#14b8a6';
                  if (entry.tier === 'Medium') fill = '#f59e0b';
                  if (entry.tier === 'High' || entry.tier === 'Critical') fill = '#ef4444';
                  return <Cell key={index} fill={fill} />;
                })}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Control Bar for Account Table */}
      <div className="controls-card margin-top-xs flex-between wrap-gap">
        <div className="flex-align gap-sm">
          <span className="filter-label flex-align gap-xs">
            <Activity size={14} className="text-teal" /> Filter Minimum Anomaly:
          </span>
          <select
            value={minAnomaly}
            onChange={(e) => {
              setMinAnomaly(e.target.value);
              setPage(1);
            }}
            className="select-input"
          >
            <option value="">All Anomaly Scores (&ge; 0.0)</option>
            <option value="0.4">Moderate Anomalies (&ge; 0.40)</option>
            <option value="0.6">Elevated Anomalies (&ge; 0.60)</option>
            <option value="0.75">Critical Anomalies (&ge; 0.75)</option>
          </select>
        </div>

        <div className="flex-align gap-sm">
          <span className="filter-label flex-align gap-xs">
            <ArrowUpDown size={14} className="text-stone" /> Sort By:
          </span>
          <select
            value={sortBy}
            onChange={(e) => {
              setSortBy(e.target.value);
              setPage(1);
            }}
            className="select-input"
          >
            <option value="highest_anomaly">Highest Anomaly Score</option>
            <option value="highest_risk">Highest Fused Risk Score</option>
            <option value="highest_velocity">Highest Transaction Velocity</option>
            <option value="highest_behavior">Highest Behavior Change</option>
          </select>
        </div>
      </div>

      {/* Account Anomaly Table */}
      <div className="section-card margin-top-xs">
        <div className="card-head flex-between">
          <div>
            <h3>Anomalous Accounts Register</h3>
            <p className="card-sub">
              Showing page {summary.page} of {summary.total_pages} ({summary.accounts.length} accounts rendered)
            </p>
          </div>
        </div>

        <div className="table-responsive margin-top-xs">
          <table className="mini-table anomaly-table">
            <thead>
              <tr>
                <th>Account ID</th>
                <th>Anomaly Score</th>
                <th>Fused Risk Score</th>
                <th>Transaction Velocity</th>
                <th>Behavior Change</th>
                <th>Network Risk Score</th>
                <th>Action</th>
              </tr>
            </thead>
            <tbody>
              {summary.accounts.map((acct, idx) => {
                const isHigh = acct.anomaly_score >= 0.70;
                const isMed = acct.anomaly_score >= 0.50 && acct.anomaly_score < 0.70;

                return (
                  <tr
                    key={idx}
                    className="clickable-row"
                    onClick={() => handleAccountClick(acct.account_id)}
                  >
                    <td className="font-mono font-semibold text-ink flex-align gap-xs">
                      {acct.account_id}
                      {isHigh && <span className="anomaly-tag critical">CRITICAL OUTLIER</span>}
                      {isMed && <span className="anomaly-tag elevated">ELEVATED</span>}
                    </td>
                    <td>
                      <div className="metric-bar-cell">
                        <span className="font-mono font-bold text-teal">{acct.anomaly_score.toFixed(3)}</span>
                        <div className="mini-progress-bg">
                          <div
                            className={`mini-progress-fill ${isHigh ? 'danger' : isMed ? 'warning' : 'teal'}`}
                            style={{ width: `${Math.min(100, acct.anomaly_score * 100)}%` }}
                          />
                        </div>
                      </div>
                    </td>
                    <td>
                      <span className="font-mono font-semibold text-ink">{acct.risk_score.toFixed(1)}/100</span>
                    </td>
                    <td className="font-mono">{acct.transaction_velocity} txns/hr</td>
                    <td className="font-mono text-stone">{acct.behavior_change.toFixed(2)}x baseline</td>
                    <td className="font-mono">{acct.network_risk.toFixed(1)}</td>
                    <td>
                      <button
                        className="btn-link flex-align gap-xs text-xs"
                        onClick={(e) => {
                          e.stopPropagation();
                          handleAccountClick(acct.account_id);
                        }}
                      >
                        Investigate <ChevronRight size={13} />
                      </button>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>

        {/* Pagination Bar */}
        <div className="pagination-bar flex-between margin-top-xs">
          <button
            className="btn-secondary text-xs"
            disabled={page <= 1}
            onClick={() => setPage((p) => Math.max(1, p - 1))}
          >
            Previous Page
          </button>
          <span className="text-xs font-mono text-stone">
            Page {summary.page} / {summary.total_pages}
          </span>
          <button
            className="btn-secondary text-xs"
            disabled={page >= summary.total_pages}
            onClick={() => setPage((p) => p + 1)}
          >
            Next Page
          </button>
        </div>
      </div>
    </div>
  );
}
