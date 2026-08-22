import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  AlertTriangle, CheckCircle, XCircle, Eye,
  Clock, ShieldAlert, Filter, Check,
} from 'lucide-react';
import { getAlerts, patchAlert } from '../api/client';
import './AlertsPage.css';

export default function AlertsPage() {
  const [alerts, setAlerts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState('open');
  const navigate = useNavigate();

  useEffect(() => {
    async function loadData() {
      setLoading(true);
      try {
        const data = await getAlerts();
        setAlerts(data);
      } catch (err) {
        console.error('Failed to load alerts:', err);
      } finally {
        setLoading(false);
      }
    }
    loadData();
  }, []);

  const handleUpdateStatus = async (alertId, newStatus) => {
    try {
      const updated = await patchAlert(alertId, { status: newStatus });
      setAlerts((prev) =>
        prev.map((a) => (a.id === alertId ? { ...a, status: updated.status } : a))
      );
    } catch (err) {
      console.error('Failed to update alert:', err);
    }
  };

  const filteredAlerts = alerts.filter((a) => {
    if (activeTab === 'all') return true;
    return a.status === activeTab;
  });

  const openCount = alerts.filter((a) => a.status === 'open').length;
  const reviewedCount = alerts.filter((a) => a.status === 'reviewed').length;
  const dismissedCount = alerts.filter((a) => a.status === 'dismissed').length;

  return (
    <div className="alerts-page animate-fade-in">
      <div className="page-head">
        <h2>Alerts & Case Management Panel</h2>
        <p>Real-time queue of high-risk mule indicators requiring compliance analyst review.</p>
      </div>

      {/* Tabs */}
      <div className="alerts-toolbar">
        <div className="status-tabs">
          <button
            className={`tab-btn ${activeTab === 'open' ? 'active' : ''}`}
            onClick={() => setActiveTab('open')}
            id="tab-open"
          >
            Open Queue ({openCount})
          </button>
          <button
            className={`tab-btn ${activeTab === 'reviewed' ? 'active' : ''}`}
            onClick={() => setActiveTab('reviewed')}
            id="tab-reviewed"
          >
            Reviewed ({reviewedCount})
          </button>
          <button
            className={`tab-btn ${activeTab === 'dismissed' ? 'active' : ''}`}
            onClick={() => setActiveTab('dismissed')}
            id="tab-dismissed"
          >
            Dismissed ({dismissedCount})
          </button>
          <button
            className={`tab-btn ${activeTab === 'all' ? 'active' : ''}`}
            onClick={() => setActiveTab('all')}
            id="tab-all"
          >
            All Alerts ({alerts.length})
          </button>
        </div>
      </div>

      {/* Alert List */}
      <div className="alerts-list">
        {loading ? (
          <div className="loading-state">Fetching active compliance alerts…</div>
        ) : filteredAlerts.length === 0 ? (
          <div className="empty-alerts">
            <CheckCircle size={32} className="text-success" />
            <p>No alerts in the current view state.</p>
          </div>
        ) : (
          filteredAlerts.map((alt) => (
            <div key={alt.id} className={`alert-card-item ${alt.status}`}>
              <div className="alert-card-left">
                <div className="alert-badge-col">
                  <span className={`severity-badge ${alt.severity}`}>{alt.severity}</span>
                </div>

                <div className="alert-body">
                  <div className="alert-head">
                    <span className="alert-id font-mono">{alt.id}</span>
                    <h3 className="alert-type">{alt.type}</h3>
                    <span
                      className="acct-tag cursor-pointer"
                      onClick={() => navigate(`/explain?id=${alt.account_id}`)}
                    >
                      {alt.account_id}
                    </span>
                  </div>

                  <p className="alert-msg">{alt.message}</p>

                  <div className="alert-meta">
                    <span className="meta-time">
                      <Clock size={12} /> {new Date(alt.created_at).toLocaleString()}
                    </span>
                    <span className={`status-pill ${alt.status}`}>
                      Status: {alt.status}
                    </span>
                  </div>
                </div>
              </div>

              {/* Analyst Action Buttons — Calls /alerts PATCH */}
              <div className="alert-card-right">
                <button
                  className="btn-action inspect"
                  title="Investigate XAI Explainability"
                  onClick={() => navigate(`/explain?id=${alt.account_id}`)}
                >
                  <Eye size={14} /> Explain
                </button>

                {alt.status !== 'reviewed' && (
                  <button
                    className="btn-action review"
                    title="Mark as Reviewed"
                    onClick={() => handleUpdateStatus(alt.id, 'reviewed')}
                  >
                    <Check size={14} /> Mark Reviewed
                  </button>
                )}

                {alt.status !== 'dismissed' && (
                  <button
                    className="btn-action dismiss"
                    title="Dismiss Alert"
                    onClick={() => handleUpdateStatus(alt.id, 'dismissed')}
                  >
                    <XCircle size={14} /> Dismiss
                  </button>
                )}
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
}
