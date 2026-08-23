import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  AlertTriangle, CheckCircle, XCircle, Eye,
  Clock, ShieldAlert, Filter, Check, Search, Calendar,
  ArrowUpDown, CheckSquare, Square, Layers, Sparkles, BrainCircuit, RefreshCw, ChevronLeft, ChevronRight,
  FileText, Send, X, ShieldCheck
} from 'lucide-react';
import { getAlerts, patchAlert, bulkPatchAlerts, submitFeedback, getFeedbackHistory } from '../api/client';
import SarModal from '../components/ui/SarModal';
import './AlertsPage.css';

const ALL_STATUSES = [
  { id: 'ALL', label: 'All Statuses' },
  { id: 'OPEN', label: 'Open' },
  { id: 'UNDER_INVESTIGATION', label: 'Under Investigation' },
  { id: 'CONFIRMED_MULE', label: 'Confirmed Mule' },
  { id: 'FALSE_POSITIVE', label: 'False Positive' },
  { id: 'DISMISSED', label: 'Dismissed' },
];

export default function AlertsPage() {
  const [alerts, setAlerts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(10);
  const [totalPages, setTotalPages] = useState(1);

  // Filters & Sorting
  const [activeStatus, setActiveStatus] = useState('ALL');
  const [riskTier, setRiskTier] = useState('ALL');
  const [search, setSearch] = useState('');
  const [startDate, setStartDate] = useState('');
  const [endDate, setEndDate] = useState('');
  const [sortBy, setSortBy] = useState('risk_desc');

  // Bulk Selection
  const [selectedIds, setSelectedIds] = useState([]);
  const [bulkActionStatus, setBulkActionStatus] = useState('UNDER_INVESTIGATION');

  // Feedback Modal State
  const [activeFeedbackAlert, setActiveFeedbackAlert] = useState(null);
  const [modalDecision, setModalDecision] = useState('UNDER_INVESTIGATION');
  const [modalNote, setModalNote] = useState('');
  const [modalHistory, setModalHistory] = useState([]);
  const [submittingModal, setSubmittingModal] = useState(false);

  // SAR Modal State
  const [selectedSarAccountId, setSelectedSarAccountId] = useState(null);

  const navigate = useNavigate();

  const loadAlerts = async () => {
    setLoading(true);
    try {
      const params = {
        page,
        page_size: pageSize,
        sort_by: sortBy,
      };
      if (activeStatus !== 'ALL') params.status = activeStatus;
      if (riskTier !== 'ALL') params.risk_tier = riskTier;
      if (search.trim()) params.search = search.trim();
      if (startDate) params.start_date = startDate;
      if (endDate) params.end_date = endDate;

      const res = await getAlerts(params);
      setAlerts(res.alerts || []);
      setTotal(res.total || 0);
      setTotalPages(res.total_pages || 1);
    } catch (err) {
      console.error('Failed to load backend alerts:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadAlerts();
    const handleDatasetChange = () => {
      loadAlerts();
    };
    window.addEventListener('dataset-changed', handleDatasetChange);
    return () => window.removeEventListener('dataset-changed', handleDatasetChange);
  }, [page, pageSize, activeStatus, riskTier, sortBy, startDate, endDate]);

  const handleSearchSubmit = (e) => {
    e.preventDefault();
    setPage(1);
    loadAlerts();
  };

  const handleUpdateStatus = async (alertId, newStatus) => {
    try {
      await patchAlert(alertId, { status: newStatus });
      loadAlerts();
    } catch (err) {
      console.error('Failed to update alert:', err);
    }
  };

  const handleBulkUpdate = async () => {
    if (!selectedIds.length) return;
    try {
      await bulkPatchAlerts(selectedIds, bulkActionStatus);
      setSelectedIds([]);
      loadAlerts();
    } catch (err) {
      console.error('Failed bulk update:', err);
    }
  };

  const openFeedbackModal = async (alt) => {
    setActiveFeedbackAlert(alt);
    setModalDecision(alt.status || 'UNDER_INVESTIGATION');
    setModalNote('');
    try {
      const fbRes = await getFeedbackHistory({ account_id: alt.account_id, alert_id: alt.alert_id });
      setModalHistory(fbRes.history || []);
    } catch (err) {
      setModalHistory([]);
    }
  };

  const handleSubmitModalFeedback = async (e) => {
    e.preventDefault();
    if (!modalNote.trim() || !activeFeedbackAlert) return;

    setSubmittingModal(true);
    try {
      await submitFeedback({
        alert_id: activeFeedbackAlert.alert_id,
        account_id: activeFeedbackAlert.account_id,
        decision: modalDecision,
        note: modalNote.trim(),
        investigator: 'Compliance Analyst',
      });

      setModalNote('');
      setActiveFeedbackAlert(null);
      // Re-fetch backend alerts without calling POST /train
      await loadAlerts();
    } catch (err) {
      console.error('Failed to submit investigator feedback modal:', err);
    } finally {
      setSubmittingModal(false);
    }
  };

  const toggleSelectAll = () => {
    if (selectedIds.length === alerts.length) {
      setSelectedIds([]);
    } else {
      setSelectedIds(alerts.map((a) => a.alert_id));
    }
  };

  const toggleSelectAlert = (alertId) => {
    setSelectedIds((prev) =>
      prev.includes(alertId) ? prev.filter((id) => id !== alertId) : [...prev, alertId]
    );
  };

  return (
    <div className="alerts-page animate-fade-in">
      {/* Page Header */}
      <div className="page-head flex-between">
        <div>
          <h2>Compliance Alerts & Case Queue</h2>
          <p>Backend-scored account risk alerts driven by XGBoost and Isolation Forest attribution signals.</p>
        </div>

        <button className="btn-secondary flex-align gap-xs" onClick={loadAlerts}>
          <RefreshCw size={14} /> Refresh Queue
        </button>
      </div>

      {/* Status Filter Tabs */}
      <div className="alerts-toolbar margin-top-xs">
        <div className="status-tabs flex-align flex-wrap">
          {ALL_STATUSES.map((st) => (
            <button
              key={st.id}
              className={`tab-btn ${activeStatus === st.id ? 'active' : ''}`}
              onClick={() => {
                setActiveStatus(st.id);
                setPage(1);
              }}
            >
              {st.label}
            </button>
          ))}
        </div>
      </div>

      {/* Filter & Search Bar */}
      <div className="alerts-filter-bar margin-top-xs">
        {/* Search */}
        <form onSubmit={handleSearchSubmit} className="search-box">
          <Search size={14} className="search-icon" />
          <input
            type="text"
            placeholder="Search Account ID or Alert ID..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        </form>

        {/* Risk Tier */}
        <div className="filter-item">
          <label>Risk Tier:</label>
          <select value={riskTier} onChange={(e) => { setRiskTier(e.target.value); setPage(1); }}>
            <option value="ALL">All Tiers</option>
            <option value="CRITICAL">Critical</option>
            <option value="HIGH">High</option>
            <option value="MEDIUM">Medium</option>
            <option value="LOW">Low</option>
          </select>
        </div>

        {/* Sorting */}
        <div className="filter-item">
          <label>Sort By:</label>
          <select value={sortBy} onChange={(e) => setSortBy(e.target.value)}>
            <option value="risk_desc">Highest Risk Score</option>
            <option value="risk_asc">Lowest Risk Score</option>
            <option value="newest">Newest First</option>
            <option value="oldest">Oldest First</option>
          </select>
        </div>

        {/* Date Filter */}
        <div className="filter-item">
          <label>Created Date:</label>
          <input type="date" value={startDate} onChange={(e) => { setStartDate(e.target.value); setPage(1); }} className="date-input" />
          <span>to</span>
          <input type="date" value={endDate} onChange={(e) => { setEndDate(e.target.value); setPage(1); }} className="date-input" />
        </div>
      </div>

      {/* Bulk Review Action Bar */}
      {selectedIds.length > 0 && (
        <div className="bulk-bar margin-top-xs flex-between animate-fade-in">
          <div className="flex-align gap-xs">
            <span className="font-semibold text-ink">{selectedIds.length} alert(s) selected</span>
          </div>

          <div className="flex-align gap-sm">
            <select
              value={bulkActionStatus}
              onChange={(e) => setBulkActionStatus(e.target.value)}
              className="bulk-select"
            >
              <option value="UNDER_INVESTIGATION">Set: Under Investigation</option>
              <option value="CONFIRMED_MULE">Set: Confirmed Mule</option>
              <option value="FALSE_POSITIVE">Set: False Positive</option>
              <option value="DISMISSED">Set: Dismissed</option>
              <option value="OPEN">Set: Open</option>
            </select>

            <button className="btn-primary sm" onClick={handleBulkUpdate}>
              Apply Bulk Status Change
            </button>
          </div>
        </div>
      )}

      {/* Alert Cards List */}
      <div className="alerts-list margin-top-xs">
        {loading ? (
          <div className="loading-state">Fetching backend compliance alerts...</div>
        ) : alerts.length === 0 ? (
          <div className="empty-alerts">
            <CheckCircle size={32} className="text-success" />
            <p>No compliance alerts match the selected filter criteria.</p>
          </div>
        ) : (
          <>
            {/* Table/List Select All Header */}
            <div className="list-select-header flex-align gap-xs padding-xs">
              <button className="btn-checkbox" onClick={toggleSelectAll}>
                {selectedIds.length === alerts.length ? <CheckSquare size={16} className="text-teal" /> : <Square size={16} className="text-stone" />}
              </button>
              <span className="text-xs text-stone">Select All ({alerts.length})</span>
            </div>

            {alerts.map((alt) => {
              const isSelected = selectedIds.includes(alt.alert_id);
              const tierClass = alt.risk_tier.toLowerCase();
              return (
                <div key={alt.alert_id} className={`alert-card-item ${tierClass} ${isSelected ? 'selected' : ''}`}>
                  <div className="alert-card-left">
                    {/* Checkbox */}
                    <button className="btn-checkbox" onClick={() => toggleSelectAlert(alt.alert_id)}>
                      {isSelected ? <CheckSquare size={16} className="text-teal" /> : <Square size={16} className="text-stone" />}
                    </button>

                    {/* Risk Tier Badge */}
                    <div className="alert-badge-col">
                      <span className={`severity-badge ${tierClass}`}>
                        {alt.risk_tier} ({alt.risk_score})
                      </span>
                    </div>

                    {/* Card Body */}
                    <div className="alert-body">
                      <div className="alert-head flex-align gap-xs flex-wrap">
                        <span className="alert-id font-mono font-bold text-ink">{alt.alert_id}</span>
                        <span
                          className="acct-tag cursor-pointer flex-align gap-xs"
                          onClick={() => navigate(`/explain?id=${alt.account_id}`)}
                          title="Open Account Investigation"
                        >
                          <BrainCircuit size={13} className="text-teal" />
                          <strong className="text-teal">{alt.account_id}</strong>
                        </span>

                        <span className="model-ver-tag font-mono text-xs">{alt.model_version}</span>
                      </div>

                      {/* Summary Message */}
                      <p className="alert-msg">{alt.summary}</p>

                      {/* Model-Derived Reasons Tags */}
                      {alt.top_reasons && alt.top_reasons.length > 0 && (
                        <div className="reasons-tags-box margin-top-xs">
                          <span className="reasons-label flex-align gap-xs">
                            <Sparkles size={12} className="text-teal" /> Top Model Signals:
                          </span>
                          <div className="reasons-pills flex-wrap">
                            {alt.top_reasons.map((reason, rIdx) => (
                              <span key={rIdx} className="reason-pill">
                                {reason}
                              </span>
                            ))}
                          </div>
                        </div>
                      )}

                      {/* Detailed Metric Badges */}
                      <div className="alert-metrics-bar margin-top-xs">
                        <span className="m-chip">Prob: <strong>{alt.mule_probability}</strong></span>
                        <span className="m-chip">Anomaly: <strong>{alt.anomaly_score}</strong></span>
                        <span className="m-chip">Net Risk: <strong>{alt.network_risk}</strong></span>
                      </div>

                      {/* Meta Footer */}
                      <div className="alert-meta margin-top-xs">
                        <span className="meta-time">
                          <Clock size={12} /> Created: {new Date(alt.created_at).toLocaleString()}
                        </span>
                      </div>
                    </div>
                  </div>

                  {/* Card Right Action Panel */}
                  <div className="alert-card-right flex-column gap-xs">
                    {/* Status Dropdown */}
                    <div className="status-change-box">
                      <label className="text-xs text-stone">Status:</label>
                      <select
                        value={alt.status}
                        onChange={(e) => handleUpdateStatus(alt.alert_id, e.target.value)}
                        className={`status-select ${alt.status.toLowerCase()}`}
                      >
                        <option value="OPEN">OPEN</option>
                        <option value="UNDER_INVESTIGATION">UNDER INVESTIGATION</option>
                        <option value="CONFIRMED_MULE">CONFIRMED MULE</option>
                        <option value="FALSE_POSITIVE">FALSE POSITIVE</option>
                        <option value="DISMISSED">DISMISSED</option>
                      </select>
                    </div>

                    <button
                      className="btn-secondary sm"
                      style={{ width: '100%', justifyContent: 'center' }}
                      onClick={() => openFeedbackModal(alt)}
                    >
                      <FileText size={13} /> Feedback & Notes
                    </button>

                    <button
                      className="btn-info sm"
                      style={{ width: '100%', justifyContent: 'center', display: 'flex', alignItems: 'center', gap: '4px', backgroundColor: 'rgba(99, 102, 241, 0.1)', color: '#818cf8', border: '1px solid rgba(99, 102, 241, 0.2)' }}
                      onClick={() => setSelectedSarAccountId(alt.account_id)}
                    >
                      <FileText size={13} /> Generate SAR
                    </button>

                    <button
                      className="btn-primary sm"
                      style={{ width: '100%', justifyContent: 'center' }}
                      onClick={() => navigate(`/explain?id=${alt.account_id}`)}
                    >
                      <Eye size={13} /> Investigate Account
                    </button>
                  </div>
                </div>
              );
            })}
          </>
        )}
      </div>

      {/* Pagination Footer */}
      {!loading && total > 0 && (
        <div className="pagination-bar margin-top-sm flex-between">
          <span className="text-xs text-stone font-mono">
            Showing Page {page} of {totalPages} (Total: {total} alerts)
          </span>

          <div className="flex-align gap-xs">
            <button
              className="btn-secondary sm"
              disabled={page <= 1}
              onClick={() => setPage((p) => Math.max(1, p - 1))}
            >
              <ChevronLeft size={14} /> Previous
            </button>
            <button
              className="btn-secondary sm"
              disabled={page >= totalPages}
              onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
            >
              Next <ChevronRight size={14} />
            </button>
          </div>
        </div>
      )}

      {/* Investigator Feedback & Decision Modal */}
      {activeFeedbackAlert && (
        <div className="modal-backdrop animate-fade-in" onClick={() => setActiveFeedbackAlert(null)}>
          <div className="modal-content-card" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header flex-between">
              <div className="flex-align gap-xs">
                <FileText size={18} className="text-teal" />
                <h3>Investigator Case Feedback — {activeFeedbackAlert.alert_id}</h3>
              </div>
              <button className="btn-close" onClick={() => setActiveFeedbackAlert(null)}>
                <X size={16} />
              </button>
            </div>

            <div className="modal-body">
              <div className="info-box margin-bottom-xs flex-between">
                <span>Account: <strong className="font-mono text-ink">{activeFeedbackAlert.account_id}</strong></span>
                <span className={`status-pill ${activeFeedbackAlert.status.toLowerCase()}`}>
                  Current Status: {activeFeedbackAlert.status}
                </span>
              </div>

              <form onSubmit={handleSubmitModalFeedback} className="note-form">
                <div className="margin-bottom-xs">
                  <label className="text-xs text-stone font-semibold">Investigator Action / Decision:</label>
                  <div className="decision-radios flex-wrap gap-xs margin-top-xs">
                    {[
                      { id: 'CONFIRMED_MULE', label: 'Confirmed Mule', class: 'mule' },
                      { id: 'LEGITIMATE', label: 'Legitimate Account', class: 'legit' },
                      { id: 'FALSE_POSITIVE', label: 'False Positive Alert', class: 'fp' },
                      { id: 'UNDER_INVESTIGATION', label: 'Under Investigation', class: 'invest' },
                    ].map((act) => (
                      <button
                        key={act.id}
                        type="button"
                        className={`decision-btn ${act.class} ${modalDecision === act.id ? 'active' : ''}`}
                        onClick={() => setModalDecision(act.id)}
                      >
                        {act.label}
                      </button>
                    ))}
                  </div>
                </div>

                <div className="margin-bottom-xs">
                  <label className="text-xs text-stone font-semibold">Investigator Rationale & Case Notes:</label>
                  <textarea
                    rows="3"
                    placeholder="Enter compliance justification or audit notes..."
                    value={modalNote}
                    onChange={(e) => setModalNote(e.target.value)}
                    className="note-input margin-top-xs"
                    required
                  />
                </div>

                <button type="submit" className="btn-primary sm margin-top-xs" disabled={submittingModal || !modalNote.trim()}>
                  <Send size={13} /> {submittingModal ? 'Submitting...' : 'Submit Decision & Refresh'}
                </button>
              </form>

              {/* History */}
              <div className="notes-list margin-top-sm border-top padding-top-xs">
                <h4 className="text-xs text-stone font-bold text-uppercase margin-bottom-xs">Audit History & Past Decisions</h4>
                {modalHistory.length === 0 ? (
                  <p className="text-xs text-stone">No previous decision notes recorded for this alert.</p>
                ) : (
                  modalHistory.map((item, idx) => (
                    <div key={item.feedback_id || idx} className="note-card margin-bottom-xs">
                      <div className="flex-between text-xs text-stone">
                        <span className="font-bold text-ink flex-align gap-xs">
                          <ShieldCheck size={13} className="text-teal" />
                          {item.investigator || 'Analyst'}
                        </span>
                        <span className="font-mono">{item.timestamp ? new Date(item.timestamp).toLocaleString() : 'N/A'}</span>
                      </div>
                      <div className="flex-between margin-top-xs">
                        <span className={`decision-badge ${(item.decision || '').toLowerCase()}`}>
                          {item.decision}
                        </span>
                      </div>
                      <p className="note-text margin-top-xs">{item.note}</p>
                    </div>
                  ))
                )}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* SAR Modal */}
      {selectedSarAccountId && (
        <SarModal
          accountId={selectedSarAccountId}
          onClose={() => setSelectedSarAccountId(null)}
          onSaveSuccess={() => loadAlerts()}
        />
      )}
    </div>
  );
}


