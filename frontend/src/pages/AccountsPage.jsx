import React, { useState, useEffect } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import {
  Search, Filter, ArrowUpDown, BrainCircuit, Share2, ChevronLeft, ChevronRight,
  ShieldAlert, Activity, AlertTriangle, RefreshCw, Calendar, Zap, Layers
} from 'lucide-react';
import { getRiskScores } from '../api/client';
import './AccountsPage.css';

export default function AccountsPage() {
  const [searchParams] = useSearchParams();
  const initialTier = searchParams.get('tier') || '';

  // Data & Pagination State
  const [accounts, setAccounts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(10);
  const [totalPages, setTotalPages] = useState(1);
  const [totalAccounts, setTotalAccounts] = useState(0);

  // Filters State
  const [search, setSearch] = useState('');
  const [tier, setTier] = useState(initialTier);
  const [minScore, setMinScore] = useState('');
  const [maxScore, setMaxScore] = useState('');
  const [anomalyOnly, setAnomalyOnly] = useState(false);
  const [minNetworkRisk, setMinNetworkRisk] = useState('');
  const [status, setStatus] = useState('');
  const [startDate, setStartDate] = useState('');
  const [endDate, setEndDate] = useState('');

  // Sorting State
  const [sort, setSort] = useState('highest_risk');

  const navigate = useNavigate();

  const loadAccounts = async () => {
    setLoading(true);
    setError(null);
    try {
      const params = {
        page,
        page_size: pageSize,
        sort_by: sort,
        search: search.trim() || undefined,
        tier: tier || undefined,
        min_score: minScore !== '' ? Number(minScore) : undefined,
        max_score: maxScore !== '' ? Number(maxScore) : undefined,
        anomaly_only: anomalyOnly || undefined,
        min_network_risk: minNetworkRisk !== '' ? Number(minNetworkRisk) : undefined,
        status: status || undefined,
        start_date: startDate || undefined,
        end_date: endDate || undefined,
      };

      const res = await getRiskScores(params);
      setAccounts(res.accounts || []);
      setTotalAccounts(res.total || 0);
      setTotalPages(res.total_pages || 1);
    } catch (err) {
      console.error('Failed to load accounts:', err);
      setError(err.message || 'Error querying account risk directory.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadAccounts();
    const handleDatasetChange = () => {
      loadAccounts();
    };
    window.addEventListener('dataset-changed', handleDatasetChange);
    return () => window.removeEventListener('dataset-changed', handleDatasetChange);
  }, [page, pageSize, sort, tier, anomalyOnly, status, startDate, endDate]);

  // Debounced search & numeric filter submission
  const handleApplyFilters = (e) => {
    if (e) e.preventDefault();
    setPage(1);
    loadAccounts();
  };

  const handleResetFilters = () => {
    setSearch('');
    setTier('');
    setMinScore('');
    setMaxScore('');
    setAnomalyOnly(false);
    setMinNetworkRisk('');
    setStatus('');
    setStartDate('');
    setEndDate('');
    setSort('highest_risk');
    setPage(1);
  };

  const handleRowClick = (accountId) => {
    navigate(`/explain?id=${accountId}`);
  };

  return (
    <div className="accounts-page animate-fade-in">
      {/* Page Header */}
      <div className="page-head flex-between">
        <div>
          <h2>Account-Level Mule Detection Directory</h2>
          <p>Backend-driven risk-ranked roster, PaySim metrics & ML anomaly evaluations.</p>
        </div>
        <div className="flex-align gap-sm">
          <span className="total-badge">Total Accounts: <strong>{totalAccounts.toLocaleString()}</strong></span>
          <button className="btn-secondary sm" onClick={loadAccounts} title="Reload Data">
            <RefreshCw size={14} /> Refresh
          </button>
        </div>
      </div>

      {/* Advanced Filter Toolbar */}
      <form className="toolbar-card" onSubmit={handleApplyFilters}>
        <div className="toolbar-row primary-row">
          {/* Search across Account ID / Sender ID / Receiver ID */}
          <div className="search-box">
            <Search size={15} className="search-icon" />
            <input
              type="text"
              placeholder="Search Account ID, Sender ID, or Receiver ID..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              id="account-search-input"
            />
          </div>

          {/* Risk Tier Select */}
          <div className="select-wrap">
            <Filter size={13} />
            <select value={tier} onChange={(e) => { setTier(e.target.value); setPage(1); }} id="tier-filter-select">
              <option value="">All Risk Tiers</option>
              <option value="critical">Critical Risk (&gt;85)</option>
              <option value="high">High Risk (70 - 85)</option>
              <option value="medium">Medium Risk (30 - 70)</option>
              <option value="low">Low Risk (&lt;30)</option>
            </select>
          </div>

          {/* Sorting Dropdown */}
          <div className="select-wrap">
            <ArrowUpDown size={13} />
            <select value={sort} onChange={(e) => { setSort(e.target.value); setPage(1); }} id="sort-filter-select">
              <option value="highest_risk">Sort: Highest Risk Score</option>
              <option value="highest_anomaly">Sort: Highest Anomaly Score</option>
              <option value="highest_velocity">Sort: Highest Txn Velocity</option>
              <option value="highest_network_risk">Sort: Highest Network Risk</option>
              <option value="newest_alerts">Sort: Newest Alerts</option>
            </select>
          </div>

          <button type="submit" className="btn-primary sm">Apply Filters</button>
          <button type="button" className="btn-secondary sm" onClick={handleResetFilters}>Reset</button>
        </div>

        {/* Secondary Filters Row */}
        <div className="toolbar-row secondary-row margin-top-xs">
          {/* Score Range */}
          <div className="filter-item">
            <label>Score Range:</label>
            <input
              type="number"
              placeholder="Min"
              value={minScore}
              onChange={(e) => setMinScore(e.target.value)}
              className="num-input"
              min="0"
              max="100"
            />
            <span>-</span>
            <input
              type="number"
              placeholder="Max"
              value={maxScore}
              onChange={(e) => setMaxScore(e.target.value)}
              className="num-input"
              min="0"
              max="100"
            />
          </div>

          {/* Anomaly Only Checkbox */}
          <label className="checkbox-label">
            <input
              type="checkbox"
              checked={anomalyOnly}
              onChange={(e) => { setAnomalyOnly(e.target.checked); setPage(1); }}
            />
            <span>Anomalous Accounts Only (&ge;0.5)</span>
          </label>

          {/* Min Network Risk */}
          <div className="filter-item">
            <label>Min Net Risk:</label>
            <input
              type="number"
              placeholder="0-100"
              value={minNetworkRisk}
              onChange={(e) => setMinNetworkRisk(e.target.value)}
              className="num-input"
            />
          </div>

          {/* Investigation Status Filter */}
          <div className="filter-item">
            <label>Status:</label>
            <select value={status} onChange={(e) => { setStatus(e.target.value); setPage(1); }}>
              <option value="">All Statuses</option>
              <option value="OPEN">OPEN</option>
              <option value="REVIEWED">REVIEWED</option>
              <option value="DISMISSED">DISMISSED</option>
              <option value="NONE">NONE</option>
            </select>
          </div>

          {/* Date Range */}
          <div className="filter-item">
            <label><Calendar size={12} /> Date Range:</label>
            <input
              type="date"
              value={startDate}
              onChange={(e) => { setStartDate(e.target.value); setPage(1); }}
              className="date-input"
            />
            <span>to</span>
            <input
              type="date"
              value={endDate}
              onChange={(e) => { setEndDate(e.target.value); setPage(1); }}
              className="date-input"
            />
          </div>
        </div>
      </form>

      {/* Backend-Driven Account Table */}
      <div className="table-card">
        {loading ? (
          <div className="table-loading">
            <div className="pulse-loader-sm" />
            <span>Querying Backend Mule Risk Scores & Telemetry…</span>
          </div>
        ) : error ? (
          <div className="table-error">
            <AlertTriangle size={24} className="text-danger" />
            <span>{error}</span>
            <button className="btn-secondary sm" onClick={loadAccounts}>Retry</button>
          </div>
        ) : (
          <>
            <div className="table-responsive">
              <table className="accounts-table">
                <thead>
                  <tr>
                    <th>Account ID</th>
                    <th>Risk Score</th>
                    <th>Risk Tier</th>
                    <th>Mule Prob</th>
                    <th>Anomaly Score</th>
                    <th>Network Risk</th>
                    <th>Txn Count</th>
                    <th>Incoming ($)</th>
                    <th>Outgoing ($)</th>
                    <th>Counterparties</th>
                    <th>Account Age</th>
                    <th>Last Activity</th>
                    <th>Alerts</th>
                    <th>Status</th>
                    <th>Action</th>
                  </tr>
                </thead>
                <tbody>
                  {accounts.length === 0 ? (
                    <tr>
                      <td colSpan="15" className="table-empty">
                        No account records match the selected backend search & filter criteria.
                      </td>
                    </tr>
                  ) : (
                    accounts.map((acc) => {
                      const scoreVal = acc.risk_score;
                      const tierClass = (acc.risk_tier || 'low').toLowerCase();
                      const statusClass = (acc.investigation_status || 'none').toLowerCase();
                      const muleProbPct = Math.round((acc.mule_probability || 0) * 100);
                      const lastActiveStr = acc.last_activity ? new Date(acc.last_activity).toLocaleDateString() : 'N/A';

                      return (
                        <tr
                          key={acc.account_id}
                          onClick={() => handleRowClick(acc.account_id)}
                          className="account-row"
                        >
                          <td className="font-mono text-ink font-semibold">{acc.account_id}</td>
                          <td>
                            <div className="score-cell">
                              <span className="score-val font-mono">{scoreVal}</span>
                              <div className="score-bar-bg">
                                <div
                                  className={`score-bar-fill ${tierClass}`}
                                  style={{ width: `${Math.min(100, scoreVal)}%` }}
                                />
                              </div>
                            </div>
                          </td>
                          <td>
                            <span className={`severity-badge ${tierClass}`}>
                              {acc.risk_tier}
                            </span>
                          </td>
                          <td className="font-mono text-xs">{muleProbPct}%</td>
                          <td className="font-mono text-xs">{(acc.anomaly_score || 0).toFixed(2)}</td>
                          <td className="font-mono text-xs">{acc.network_risk_score} / 100</td>
                          <td className="font-mono">{acc.transaction_count}</td>
                          <td className="font-mono text-xs">${(acc.incoming_amount || 0).toLocaleString()}</td>
                          <td className="font-mono text-xs">${(acc.outgoing_amount || 0).toLocaleString()}</td>
                          <td className="font-mono">{acc.unique_counterparties}</td>
                          <td className="font-mono text-xs">{acc.account_age} days</td>
                          <td className="text-stone text-xs">{lastActiveStr}</td>
                          <td>
                            <span className={`alert-count-badge ${acc.alert_count > 0 ? 'has-alerts' : ''}`}>
                              {acc.alert_count}
                            </span>
                          </td>
                          <td>
                            <span className={`status-tag ${statusClass}`}>{acc.investigation_status}</span>
                          </td>
                          <td>
                            <div className="action-btns" onClick={(e) => e.stopPropagation()}>
                              <button
                                className="btn-table-action"
                                title="Investigate XAI"
                                onClick={() => navigate(`/explain?id=${acc.account_id}`)}
                              >
                                <BrainCircuit size={14} />
                              </button>
                              <button
                                className="btn-table-action"
                                title="Graph Topology"
                                onClick={() => navigate(`/graph?id=${acc.account_id}`)}
                              >
                                <Share2 size={14} />
                              </button>
                            </div>
                          </td>
                        </tr>
                      );
                    })
                  )}
                </tbody>
              </table>
            </div>

            {/* Server-Side Pagination Bar */}
            <div className="pagination-bar">
              <div className="pagination-info">
                Showing Page <strong>{page}</strong> of <strong>{totalPages}</strong> ({totalAccounts.toLocaleString()} total accounts)
              </div>
              <div className="pagination-controls">
                <div className="page-size-select">
                  <label>Rows per page:</label>
                  <select value={pageSize} onChange={(e) => { setPageSize(Number(e.target.value)); setPage(1); }}>
                    <option value={10}>10</option>
                    <option value={20}>20</option>
                    <option value={50}>50</option>
                  </select>
                </div>
                <button
                  className="btn-pagination"
                  disabled={page <= 1}
                  onClick={() => setPage((p) => Math.max(1, p - 1))}
                >
                  <ChevronLeft size={16} /> Prev
                </button>
                <span className="page-number-display">{page}</span>
                <button
                  className="btn-pagination"
                  disabled={page >= totalPages}
                  onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                >
                  Next <ChevronRight size={16} />
                </button>
              </div>
            </div>
          </>
        )}
      </div>
    </div>
  );
}
