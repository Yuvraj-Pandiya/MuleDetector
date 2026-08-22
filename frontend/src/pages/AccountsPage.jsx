import React, { useState, useEffect } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { Search, Filter, ArrowUpDown, BrainCircuit, Share2 } from 'lucide-react';
import { getRiskScores } from '../api/client';
import './AccountsPage.css';

export default function AccountsPage() {
  const [searchParams] = useSearchParams();
  const initialTier = searchParams.get('tier') || '';

  const [accounts, setAccounts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [tier, setTier] = useState(initialTier);
  const [sort, setSort] = useState('score_desc');
  const navigate = useNavigate();

  useEffect(() => {
    async function load() {
      setLoading(true);
      try {
        const data = await getRiskScores({ tier, sort, search });
        setAccounts(data);
      } catch (e) {
        console.error('Failed to load accounts:', e);
      } finally {
        setLoading(false);
      }
    }
    load();
  }, [tier, sort, search]);

  const handleRowClick = (accountId) => {
    navigate(`/explain?id=${accountId}`);
  };

  return (
    <div className="accounts-page animate-fade-in">
      <div className="page-head">
        <h2>Risk-Ranked Accounts Directory</h2>
        <p>Prioritized account roster based on AI mule indicators & anomaly scoring.</p>
      </div>

      {/* Filter Toolbar */}
      <div className="toolbar-card">
        <div className="search-box">
          <Search size={15} className="search-icon" />
          <input
            type="text"
            placeholder="Search account ID or entity name..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            id="account-search-input"
          />
        </div>

        <div className="filter-group">
          <div className="select-wrap">
            <Filter size={13} />
            <select value={tier} onChange={(e) => setTier(e.target.value)} id="tier-filter-select">
              <option value="">All Risk Tiers</option>
              <option value="critical">Critical Risk</option>
              <option value="high">High Risk</option>
              <option value="medium">Medium Risk</option>
              <option value="low">Low Risk</option>
            </select>
          </div>

          <div className="select-wrap">
            <ArrowUpDown size={13} />
            <select value={sort} onChange={(e) => setSort(e.target.value)} id="sort-filter-select">
              <option value="score_desc">Score: Highest First</option>
              <option value="score_asc">Score: Lowest First</option>
            </select>
          </div>
        </div>
      </div>

      {/* Table */}
      <div className="table-card">
        {loading ? (
          <div className="table-loading">Querying Account Risk Scores...</div>
        ) : (
          <div className="table-responsive">
            <table className="accounts-table">
              <thead>
                <tr>
                  <th>Account ID</th>
                  <th>Entity Name</th>
                  <th>Risk Score</th>
                  <th>Risk Tier</th>
                  <th>Txn Count</th>
                  <th>Total Volume</th>
                  <th>Fan In / Out</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {accounts.length === 0 ? (
                  <tr>
                    <td colSpan="8" className="table-empty">No accounts matching filter criteria.</td>
                  </tr>
                ) : (
                  accounts.map((acc) => (
                    <tr
                      key={acc.id}
                      onClick={() => handleRowClick(acc.id)}
                      className="account-row"
                    >
                      <td className="font-mono text-ink font-semibold">{acc.id}</td>
                      <td className="font-medium text-ink">{acc.name}</td>
                      <td>
                        <div className="score-cell">
                          <span className="score-val">{acc.risk_score}</span>
                          <div className="score-bar-bg">
                            <div
                              className={`score-bar-fill ${acc.risk_tier}`}
                              style={{ width: `${acc.risk_score}%` }}
                            />
                          </div>
                        </div>
                      </td>
                      <td>
                        <span className={`severity-badge ${acc.risk_tier}`}>
                          {acc.risk_tier}
                        </span>
                      </td>
                      <td className="font-mono">{acc.txn_count}</td>
                      <td className="font-mono">${acc.total_volume.toLocaleString()}</td>
                      <td>
                        <span className="fan-badge in">In: {acc.fan_in}</span>
                        <span className="fan-badge out">Out: {acc.fan_out}</span>
                      </td>
                      <td>
                        <div className="action-btns" onClick={(e) => e.stopPropagation()}>
                          <button
                            className="btn-table-action"
                            title="Explainability (XAI)"
                            onClick={() => navigate(`/explain?id=${acc.id}`)}
                          >
                            <BrainCircuit size={14} />
                          </button>
                          <button
                            className="btn-table-action"
                            title="Graph Topology"
                            onClick={() => navigate(`/graph?id=${acc.id}`)}
                          >
                            <Share2 size={14} />
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
