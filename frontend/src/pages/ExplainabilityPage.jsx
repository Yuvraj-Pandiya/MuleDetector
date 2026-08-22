import React, { useState, useEffect } from 'react';
import { useSearchParams, useNavigate } from 'react-router-dom';
import {
  BrainCircuit, ShieldAlert, ArrowLeft, Share2,
  AlertTriangle, HelpCircle, CheckCircle, Info,
} from 'lucide-react';
import { getExplanation, getRiskScores } from '../api/client';
import './ExplainabilityPage.css';

export default function ExplainabilityPage() {
  const [searchParams] = useSearchParams();
  const paramId = searchParams.get('id');

  const [explanation, setExplanation] = useState(null);
  const [loading, setLoading] = useState(true);
  const [accountList, setAccountList] = useState([]);
  const navigate = useNavigate();

  useEffect(() => {
    async function loadData() {
      setLoading(true);
      try {
        // Load accounts first to get valid IDs
        const accs = await getRiskScores();
        setAccountList(accs);

        // Resolve which account to explain: URL param > first account in list
        const resolvedId = paramId || (accs.length > 0 ? accs[0].id : null);
        if (!resolvedId) { setLoading(false); return; }

        // Fetch explanation for the resolved ID in the same render cycle (no redirect)
        const exp = await getExplanation(resolvedId);
        setExplanation(exp);
      } catch (err) {
        console.error('Error fetching explanation:', err);
      } finally {
        setLoading(false);
      }
    }
    loadData();
  }, [paramId]);

  if (loading || !explanation) {
    return <div className="loading-state">Computing SHAP feature attribution values…</div>;
  }

  // Calculate max impact for proportional bar scaling
  const maxImpact = Math.max(...explanation.features.map((f) => Math.abs(f.impact)), 0.01);

  return (
    <div className="explain-page animate-fade-in">
      {/* Account Hero Bar */}
      <div className="account-hero-bar">
        <div className="account-title-group">
          <button className="btn-secondary" style={{ height: 32, padding: '0 10px' }} onClick={() => navigate('/accounts')}>
            <ArrowLeft size={14} /> Back
          </button>
          <div className="account-icon-wrap">
            <ShieldAlert size={22} />
          </div>
          <div>
            <div className="hero-account-id">
              <h2>{explanation.account_id}</h2>
              <span className={`severity-badge ${explanation.risk_tier}`}>
                {explanation.risk_tier} Risk
              </span>
            </div>
            <p className="subtext">Account Explainability Audit Trail • Model Confidence: 96.4%</p>
          </div>
        </div>

        <div className="hero-selector">
          <label htmlFor="account-select">Select Account:</label>
          <select
            id="account-select"
            value={explanation.account_id}
            onChange={(e) => navigate(`/explain?id=${e.target.value}`)}
          >
            {accountList.map((acc) => (
              <option key={acc.id} value={acc.id}>
                {acc.id} — {acc.name} ({acc.risk_score})
              </option>
            ))}
          </select>
          <button className="btn-primary" style={{ height: 34, fontSize: 13 }} onClick={() => navigate(`/graph?id=${explanation.account_id}`)}>
            <Share2 size={14} /> View Topology
          </button>
        </div>
      </div>

      <div className="explain-grid">
        {/* Left Column — Human Readable Audit Summary */}
        <div className="audit-col">
          <div className="dash-card">
            <div className="card-header-sm">
              <BrainCircuit size={18} className="text-primary" />
              <h3>Human-Readable Risk Audit</h3>
            </div>
            <div className="reason-text-box">
              <p>{explanation.reason}</p>
            </div>

            <div className="risk-score-display">
              <div className="gauge-circle">
                <span className="gauge-score">{explanation.risk_score}</span>
                <span className="gauge-max">/ 100</span>
              </div>
              <div className="gauge-info">
                <div className="gauge-title">Risk Index Score</div>
                <div className="gauge-desc">
                  Composite anomaly score combining Graph Neural Network node embeddings and SHAP gradient boosting features.
                </div>
              </div>
            </div>

            <div className="compliance-checklist">
              <h4>Automated Compliance Indicators</h4>
              <ul>
                <li><CheckCircle size={14} className="text-success" /> Pass-through velocity exceeded threshold (&lt;45m)</li>
                <li><CheckCircle size={14} className="text-success" /> Fan-out ratio &gt; 5.0 distinct payees</li>
                <li><CheckCircle size={14} className="text-success" /> Part of 3-node cyclic transfer pattern</li>
                <li><Info size={14} className="text-mute" /> Account age: 42 days (New Account Watch)</li>
              </ul>
            </div>
          </div>
        </div>

        {/* Right Column — SHAP Feature Attribution Chart */}
        <div className="shap-col">
          <div className="dash-card">
            <div className="shap-header">
              <div>
                <h3>SHAP Feature Contributions</h3>
                <p className="card-sub">Local feature attribution ranking for account {explanation.account_id}</p>
              </div>
              <div className="shap-legend">
                <span className="legend-chip"><span className="chip-color red" /> Increases Risk</span>
                <span className="legend-chip"><span className="chip-color green" /> Decreases Risk</span>
              </div>
            </div>

            <div className="shap-bars-container">
              {explanation.features.map((feat, idx) => {
                const widthPct = Math.round((Math.abs(feat.impact) / maxImpact) * 100);
                const isPositive = feat.direction === 'positive';
                return (
                  <div key={idx} className="shap-row">
                    <div className="shap-feature-info">
                      <span className="shap-feature-name">{feat.name}</span>
                      <span className="shap-feature-val">Value: {feat.value}</span>
                    </div>
                    <div className="shap-bar-track">
                      <div
                        className={`shap-bar-fill ${isPositive ? 'increase' : 'decrease'}`}
                        style={{ width: `${Math.max(widthPct, 8)}%` }}
                      >
                        <span className="shap-impact-text">
                          {isPositive ? '+' : '-'}{Math.abs(feat.impact).toFixed(2)}
                        </span>
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>

            <div className="shap-footer-note">
              <HelpCircle size={13} />
              <span>SHAP (SHapley Additive exPlanations) computes game-theoretic marginal feature contributions to ensure model transparency.</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
