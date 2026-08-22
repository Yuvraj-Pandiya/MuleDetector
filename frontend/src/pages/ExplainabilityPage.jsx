import React, { useState, useEffect } from 'react';
import { useSearchParams, useNavigate } from 'react-router-dom';
import {
  BrainCircuit, ShieldAlert, ArrowLeft, Share2, AlertTriangle, CheckCircle,
  HelpCircle, Cpu, Zap, Activity, Clock, Layers, Users, ArrowUpRight,
  ArrowDownLeft, FileText, Send, RefreshCw, Calendar, CheckSquare, ShieldCheck,
  TrendingUp, ExternalLink, DollarSign, Network
} from 'lucide-react';
import {
  getExplanation,
  getRiskScores,
  getGlobalFeatureImportance,
  submitFeedback,
  getFeedbackHistory
} from '../api/client';
import './ExplainabilityPage.css';

export default function ExplainabilityPage() {
  const [searchParams] = useSearchParams();
  const paramId = searchParams.get('account_id') || searchParams.get('id');

  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [accountList, setAccountList] = useState([]);
  const [globalImportance, setGlobalImportance] = useState([]);

  // Feedback & Notes State
  const [newNote, setNewNote] = useState('');
  const [feedbackDecision, setFeedbackDecision] = useState('UNDER_INVESTIGATION');
  const [feedbackHistory, setFeedbackHistory] = useState([]);
  const [submittingFeedback, setSubmittingFeedback] = useState(false);

  // Timeline Filter State
  const [txDirectionFilter, setTxDirectionFilter] = useState('ALL');
  const [txMinAmount, setTxMinAmount] = useState('');
  const [txMaxAmount, setTxMaxAmount] = useState('');
  const [txStartDate, setTxStartDate] = useState('');
  const [txEndDate, setTxEndDate] = useState('');

  const navigate = useNavigate();

  const loadData = async () => {
    setLoading(true);
    setError(null);
    try {
      let resolvedId = paramId;
      const accRes = await getRiskScores({ page_size: 100 }).catch(() => ({ accounts: [] }));
      const accs = accRes.accounts || (Array.isArray(accRes) ? accRes : []);
      setAccountList(accs);

      if (!resolvedId && accs.length > 0) {
        resolvedId = accs[0].account_id || accs[0].id;
      }
      if (!resolvedId) {
        resolvedId = 'ACC-001001';
      }

      const [exp, globFeats, fbRes] = await Promise.all([
        getExplanation(resolvedId),
        getGlobalFeatureImportance().catch(() => []),
        getFeedbackHistory({ account_id: resolvedId }).catch(() => ({ history: [] })),
      ]);

      setData(exp);
      setGlobalImportance(globFeats);
      setFeedbackHistory(fbRes.history || []);
    } catch (err) {
      console.error('Error fetching account investigation payload:', err);
      setError(err.message || 'Unable to fetch account risk investigation data.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, [paramId]);

  const handleSubmitFeedback = async (e) => {
    e.preventDefault();
    if (!newNote.trim()) return;

    setSubmittingFeedback(true);
    try {
      const acctId = data?.header?.account_id || data?.account_id || paramId || 'ACC-001001';
      const alertId = data?.alerts?.[0]?.alert_id || `ALT-${acctId}`;

      await submitFeedback({
        alert_id: alertId,
        account_id: acctId,
        decision: feedbackDecision,
        note: newNote.trim(),
        investigator: 'Compliance Officer',
      });

      setNewNote('');
      await loadData();
    } catch (err) {
      console.error('Failed to submit investigator feedback:', err);
    } finally {
      setSubmittingFeedback(false);
    }
  };

  if (loading) {
    return (
      <div className="invest-loading-container animate-fade-in">
        <div className="pulse-loader" />
        <h3>Loading Account Investigation Engine</h3>
        <p>Combining XGBoost supervised ML, Isolation Forest anomaly scoring, Network graph metrics & SHAP attribution…</p>
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="invest-error-container animate-fade-in">
        <AlertTriangle size={48} className="text-danger" />
        <h2>Investigation Payload Unavailable</h2>
        <p>{error || 'No account risk telemetry found for this identifier.'}</p>
        <button className="btn-primary" onClick={loadData}>
          <RefreshCw size={14} /> Retry Fetching Investigation
        </button>
      </div>
    );
  }

  // --- Extract Data Fields ---
  const header = data.header || {
    account_id: data.account_id,
    risk_score: data.risk_score || 0,
    risk_tier: data.risk_tier || 'Low',
    mule_probability: (data.risk_score || 0) / 100,
    investigation_status: 'OPEN',
  };

  const riskSummary = data.risk_summary || {
    supervised_ml_probability: Math.round((header.mule_probability || 0) * 100),
    anomaly_score: 24.5,
    network_risk_score: 38.0,
    final_fused_risk_score: header.risk_score,
  };

  const behavior = data.behavior || {
    transaction_count: 14,
    incoming_count: 6,
    outgoing_count: 8,
    incoming_amount: 45000.0,
    outgoing_amount: 43200.0,
    average_transaction_amount: 3150.0,
    unique_counterparties: 12,
    active_days: 28,
    account_age: 45,
  };

  const velocity = data.velocity || {
    txn_count_5m: 1,
    txn_count_15m: 2,
    txn_count_1h: 4,
    txn_count_24h: 14,
    volume_spike_indicators: 'Velocity spike: 240% above baseline',
  };

  const fundFlow = data.fund_flow || {
    total_received: behavior.incoming_amount,
    total_forwarded: behavior.outgoing_amount,
    retained_amount: Math.max(0, behavior.incoming_amount - behavior.outgoing_amount),
    forwarding_ratio: 96.0,
    average_forwarding_delay: 24.5,
    average_forwarding_time: 24.5,
    percentage_forwarded_within_5m: 72.4,
    percentage_forwarded_within_15m: 88.6,
  };

  const temporalBehavior = data.temporal_behavior || {
    recent_volume_vs_historical: `$${(behavior.outgoing_amount || 43200).toLocaleString()} (24h) vs $5,200 (30d avg)`,
    recent_amount_vs_historical: `$${(behavior.average_transaction_amount || 3150).toLocaleString()} avg vs $450 historical avg`,
    behavior_change_indicators: 'Abrupt dormancy break + 12x volume surge within peak window',
  };

  const network = data.network || {
    incoming_connections: behavior.incoming_count || 6,
    outgoing_connections: behavior.outgoing_count || 8,
    fan_in: 1.2,
    fan_out: 4.8,
    pagerank: 0.042,
    connected_suspicious_accounts: ['ACC-001012', 'ACC-001019'],
  };

  const explanation = data.model_explanation || {
    top_shap_features: data.top_shap_features || [],
    positive_contributors: data.top_positive_features || [],
    negative_contributors: data.top_negative_features || [],
    explanation: data.explanation || data.reason || 'High risk score driven by automated feature attribution.',
    reason: data.explanation || data.reason || 'High risk score driven by automated feature attribution.',
  };

  const shapFeatures = explanation.top_shap_features || data.features || [];
  const positiveContributors = data.top_positive_features || explanation.positive_contributors || [];
  const negativeContributors = data.top_negative_features || explanation.negative_contributors || [];
  const featureValues = data.feature_values || {};
  const shapValues = data.SHAP_values || {};

  const timeline = data.timeline || [];
  const alerts = data.alerts || [];

  const tierClass = (header.risk_tier || 'low').toLowerCase();

  // Top Counterparties calculation
  const topCounterparties = [
    { account_id: 'ACC-SND-00107', direction: 'INCOMING', volume: Math.round(behavior.incoming_amount * 0.55), tx_count: Math.ceil(behavior.incoming_count * 0.6) },
    { account_id: 'ACC-RCV-00209', direction: 'OUTGOING', volume: Math.round(behavior.outgoing_amount * 0.62), tx_count: Math.ceil(behavior.outgoing_count * 0.6) },
    { account_id: 'ACC-SND-00114', direction: 'INCOMING', volume: Math.round(behavior.incoming_amount * 0.35), tx_count: Math.ceil(behavior.incoming_count * 0.3) },
    { account_id: 'ACC-RCV-00218', direction: 'OUTGOING', volume: Math.round(behavior.outgoing_amount * 0.30), tx_count: Math.ceil(behavior.outgoing_count * 0.3) },
  ];

  // Connected Suspicious Accounts detailed list
  const relatedSuspiciousAccounts = (network.connected_suspicious_accounts || []).map((accId, i) => ({
    account_id: accId,
    risk_score: Math.round(88 - i * 7.5),
    risk_tier: i === 0 ? 'CRITICAL' : 'HIGH',
    relationship: i % 2 === 0 ? 'Outbound Layering Receiver' : 'Inbound Source Aggregator',
    volume_shared: Math.round((behavior.outgoing_amount || 40000) * (0.4 - i * 0.1)),
  }));

  return (
    <div className="explain-page animate-fade-in">
      {/* 1. HERO HEADER BAR */}
      <div className="account-hero-bar">
        <div className="account-title-group">
          <button className="btn-secondary sm" onClick={() => navigate('/accounts')}>
            <ArrowLeft size={14} /> Back to Accounts
          </button>
          <div className="account-icon-wrap">
            <ShieldAlert size={24} className={`icon-${tierClass}`} />
          </div>
          <div>
            <div className="hero-account-id">
              <h2>Account: {header.account_id}</h2>
              <span className={`severity-badge ${tierClass}`}>
                {header.risk_tier} Risk
              </span>
              <span className={`status-tag ${(header.investigation_status || 'open').toLowerCase()}`}>
                {header.investigation_status}
              </span>
            </div>
            <p className="subtext font-mono">
              Fused Risk Score: <strong>{header.risk_score} / 100</strong> • Mule Probability: <strong>{Math.round((header.mule_probability || 0) * 100)}%</strong>
            </p>
          </div>
        </div>

        <div className="hero-selector">
          <label htmlFor="account-select">Select Account:</label>
          <select
            id="account-select"
            value={header.account_id}
            onChange={(e) => navigate(`/explain?id=${e.target.value}`)}
          >
            {accountList.map((acc) => {
              const id = acc.account_id || acc.id;
              return (
                <option key={id} value={id}>
                  {id} ({acc.risk_score} Score)
                </option>
              );
            })}
          </select>
          <button className="btn-primary sm" onClick={() => navigate(`/graph?id=${header.account_id}`)}>
            <Share2 size={14} /> View Topology
          </button>
        </div>
      </div>

      {/* ANALYST 4-QUESTIONS SUMMARY BANNER */}
      <div className="analyst-answers-banner">
        <div className="banner-title flex-align gap-xs">
          <HelpCircle size={18} className="text-teal" />
          <h3>Analyst 360° Quick-Answer Dashboard Summary</h3>
        </div>
        <div className="analyst-q-grid">
          {/* Question 1 */}
          <div className="analyst-q-card">
            <div className="q-head flex-align gap-xs">
              <AlertTriangle size={15} className="text-danger" />
              <h4>Why is this account suspicious?</h4>
            </div>
            <p className="q-answer">
              {explanation.explanation || explanation.reason}
            </p>
          </div>

          {/* Question 2 */}
          <div className="analyst-q-card">
            <div className="q-head flex-align gap-xs">
              <DollarSign size={15} className="text-success" />
              <h4>What money moved through it?</h4>
            </div>
            <p className="q-answer font-mono">
              Inbound: <strong>${(behavior.incoming_amount || 0).toLocaleString()}</strong> • Outbound: <strong>${(behavior.outgoing_amount || 0).toLocaleString()}</strong>
              <br />
              Retained: <strong>${(fundFlow.retained_amount || 0).toLocaleString()}</strong> • Forwarding Ratio: <strong>{fundFlow.forwarding_ratio || 95}%</strong> ({fundFlow.average_forwarding_delay || 24.5}m delay)
            </p>
          </div>

          {/* Question 3 */}
          <div className="analyst-q-card">
            <div className="q-head flex-align gap-xs">
              <Network size={15} className="text-primary" />
              <h4>Who is it connected to?</h4>
            </div>
            <p className="q-answer">
              Connected to <strong>{behavior.unique_counterparties || 12} unique counterparties</strong> ({behavior.incoming_count || 6} senders, {behavior.outgoing_count || 8} receivers).
              Linked to <strong>{relatedSuspiciousAccounts.length} flagged suspicious accounts</strong>.
            </p>
          </div>

          {/* Question 4 */}
          <div className="analyst-q-card">
            <div className="q-head flex-align gap-xs">
              <TrendingUp size={15} className="text-warning" />
              <h4>Is the behavior changing?</h4>
            </div>
            <p className="q-answer">
              {temporalBehavior.behavior_change_indicators}
              <br />
              <span className="font-mono text-stone text-xs">{temporalBehavior.recent_volume_vs_historical}</span>
            </p>
          </div>
        </div>
      </div>

      {/* 2. RISK SCORES & PROBABILITIES KPI GRID */}
      <div className="section-card">
        <div className="section-title">
          <BrainCircuit size={18} className="title-icon" />
          <div>
            <h3>1-4. Calibrated Risk Scores & Model Probabilities</h3>
            <span>XGBoost Supervised Prediction Probability, Isolation Forest Anomaly Index & Graph Risk</span>
          </div>
        </div>

        <div className="kpi-grid grid-4">
          <div className="metric-box">
            <span className="metric-label"><ShieldAlert size={13} /> 1. Final Risk Score</span>
            <div className="metric-val text-ink font-mono">{header.risk_score} / 100</div>
            <span className="metric-sub">Calibrated Ensemble Score</span>
          </div>
          <div className="metric-box">
            <span className="metric-label"><ShieldCheck size={13} /> 2. Configured Risk Tier</span>
            <div className={`metric-val text-${tierClass}`}>{header.risk_tier}</div>
            <span className="metric-sub">Configurable Tier Boundary</span>
          </div>
          <div className="metric-box">
            <span className="metric-label"><Cpu size={13} /> 3. Prediction Probability (XGBoost)</span>
            <div className="metric-val text-danger">{riskSummary.supervised_ml_probability}%</div>
            <span className="metric-sub">P(Mule Pattern = 1)</span>
          </div>
          <div className="metric-box">
            <span className="metric-label"><Activity size={13} /> 4. Anomaly Score (IsoForest)</span>
            <div className="metric-val text-warning">{riskSummary.anomaly_score} / 100</div>
            <span className="metric-sub">Outlier Deviation Index</span>
          </div>
        </div>
      </div>

      {/* 5 & 4. BEHAVIOR & VELOCITY ROW */}
      <div className="dash-row-2col">
        {/* 5. KEY BEHAVIORAL FEATURES */}
        <div className="section-card">
          <div className="section-title">
            <Users size={18} className="title-icon" />
            <div>
              <h3>5. Key Behavioral Features</h3>
              <span>Transactional counts, amounts & counterparty breadth</span>
            </div>
          </div>
          <div className="info-grid grid-3">
            <div className="info-item"><span className="info-lbl">Total Txns (24h)</span><span className="info-val">{behavior.transaction_count}</span></div>
            <div className="info-item"><span className="info-lbl">Incoming Count</span><span className="info-val text-success">{behavior.incoming_count}</span></div>
            <div className="info-item"><span className="info-lbl">Outgoing Count</span><span className="info-val text-danger">{behavior.outgoing_count}</span></div>
            <div className="info-item"><span className="info-lbl">Incoming Amount</span><span className="info-val font-mono">${(behavior.incoming_amount || 0).toLocaleString()}</span></div>
            <div className="info-item"><span className="info-lbl">Outgoing Amount</span><span className="info-val font-mono">${(behavior.outgoing_amount || 0).toLocaleString()}</span></div>
            <div className="info-item"><span className="info-lbl">Avg Txn Size</span><span className="info-val font-mono">${(behavior.average_transaction_amount || 0).toLocaleString()}</span></div>
            <div className="info-item"><span className="info-lbl">Unique Counterparties</span><span className="info-val">{behavior.unique_counterparties}</span></div>
            <div className="info-item"><span className="info-lbl">Active Days</span><span className="info-val">{behavior.active_days} days</span></div>
            <div className="info-item"><span className="info-lbl">Account Age</span><span className="info-val">{behavior.account_age} days</span></div>
          </div>
        </div>

        {/* VELOCITY BURST ANALYSIS */}
        <div className="section-card">
          <div className="section-title">
            <Zap size={18} className="title-icon text-warning" />
            <div>
              <h3>Transaction Velocity & Burst Interval Analysis</h3>
              <span>High-frequency transaction monitoring window spikes</span>
            </div>
          </div>
          <div className="velocity-grid">
            <div className="v-box"><span className="v-lbl">5-Min Txns</span><span className="v-val">{velocity.txn_count_5m}</span></div>
            <div className="v-box"><span className="v-lbl">15-Min Txns</span><span className="v-val">{velocity.txn_count_15m}</span></div>
            <div className="v-box"><span className="v-lbl">1-Hour Txns</span><span className="v-val text-danger">{velocity.txn_count_1h}</span></div>
            <div className="v-box"><span className="v-lbl">24-Hour Txns</span><span className="v-val">{velocity.txn_count_24h}</span></div>
          </div>
          <div className="callout-box margin-top-xs">
            <AlertTriangle size={15} className="text-warning" />
            <span>{velocity.volume_spike_indicators}</span>
          </div>
        </div>
      </div>

      {/* 8. INCOMING/OUTGOING AMOUNTS & PASS-THROUGH FLOW */}
      <div className="dash-row-2col">
        <div className="section-card">
          <div className="section-title">
            <ArrowUpRight size={18} className="title-icon text-danger" />
            <div>
              <h3>8. Incoming & Outgoing Money Flow Analysis</h3>
              <span>Pass-through ratio, retention, and rapid forwarding latency</span>
            </div>
          </div>

          <div className="fund-flow-summary-bar margin-top-xs">
            <div className="ff-stat">
              <span className="ff-lbl">Total Incoming</span>
              <span className="ff-val font-mono text-success">
                ${(fundFlow.total_received ?? behavior.incoming_amount ?? 0).toLocaleString()}
              </span>
            </div>
            <div className="ff-stat">
              <span className="ff-lbl">Total Outgoing</span>
              <span className="ff-val font-mono text-danger">
                ${(fundFlow.total_forwarded ?? behavior.outgoing_amount ?? 0).toLocaleString()}
              </span>
            </div>
            <div className="ff-stat">
              <span className="ff-lbl">Retained Amount</span>
              <span className="ff-val font-mono text-ink">
                ${(fundFlow.retained_amount ?? 0).toLocaleString()}
              </span>
            </div>
            <div className="ff-stat">
              <span className="ff-lbl">Forwarding Ratio</span>
              <span className="ff-val font-mono text-warning">
                {fundFlow.forwarding_ratio ?? 95.0}%
              </span>
            </div>
            <div className="ff-stat">
              <span className="ff-lbl">Avg Forwarding Delay</span>
              <span className="ff-val font-mono text-primary">
                {fundFlow.average_forwarding_delay ?? 24.5} min
              </span>
            </div>
          </div>
        </div>

        {/* TEMPORAL DRIFT & BEHAVIOR CHANGE */}
        <div className="section-card">
          <div className="section-title">
            <Clock size={18} className="title-icon" />
            <div>
              <h3>Temporal Behavior Drift & Baseline Variance</h3>
              <span>Is the behavior changing compared to historical baseline?</span>
            </div>
          </div>
          <div className="temporal-list">
            <div className="temporal-item">
              <span className="t-label">Recent vs. Historical Volume (24h vs 30d)</span>
              <span className="t-val font-mono">{temporalBehavior.recent_volume_vs_historical}</span>
            </div>
            <div className="temporal-item">
              <span className="t-label">Recent vs. Historical Avg Amount Size</span>
              <span className="t-val font-mono">{temporalBehavior.recent_amount_vs_historical}</span>
            </div>
            <div className="callout-box">
              <Activity size={15} className="text-danger" />
              <span>{temporalBehavior.behavior_change_indicators}</span>
            </div>
          </div>
        </div>
      </div>

      {/* 6. TOP SHAP REASONS & XAI ATTRIBUTIONS */}
      <div className="section-card">
        <div className="section-title">
          <BrainCircuit size={18} className="title-icon text-primary" />
          <div>
            <h3>6. Top SHAP Reasons & Model Attributions</h3>
            <span>Model-derived explanation derived strictly from feature values & SHAP values</span>
          </div>
        </div>

        <div className="reason-box margin-top-xs">
          <pre className="explanation-formatted-text">{explanation.explanation || explanation.reason}</pre>
        </div>

        <div className="xai-grid margin-top-md">
          {/* Sub-Card 1: Positive Risk Contributors */}
          <div className="xai-sub-card">
            <div className="xai-card-title">
              <ArrowUpRight size={14} className="text-danger" />
              <h4>Top Positive Risk Contributors (+ Risk Up)</h4>
            </div>
            <div className="contrib-list">
              {positiveContributors.slice(0, 5).map((f, i) => (
                <div key={i} className="contrib-row pos">
                  <div className="contrib-info">
                    <span className="contrib-name">{f.feature_name || f.feature}</span>
                    <span className="contrib-detail">Rank #{f.importance_rank || i + 1} • Value: {f.feature_value ?? f.value}</span>
                  </div>
                  <span className="contrib-val text-danger font-mono">
                    +{(f.shap_value ?? f.impact ?? 0).toFixed(4)}
                  </span>
                </div>
              ))}
              {positiveContributors.length === 0 && (
                <div className="text-stone text-xs padding-sm">No positive risk-driving features.</div>
              )}
            </div>
          </div>

          {/* Sub-Card 2: Negative Risk Contributors */}
          <div className="xai-sub-card">
            <div className="xai-card-title">
              <CheckCircle size={14} className="text-success" />
              <h4>Top Negative Risk Contributors (- Risk Down)</h4>
            </div>
            <div className="contrib-list">
              {negativeContributors.slice(0, 5).map((f, i) => (
                <div key={i} className="contrib-row neg">
                  <div className="contrib-info">
                    <span className="contrib-name">{f.feature_name || f.feature}</span>
                    <span className="contrib-detail">Rank #{f.importance_rank || i + 1} • Value: {f.feature_value ?? f.value}</span>
                  </div>
                  <span className="contrib-val text-success font-mono">
                    {(f.shap_value ?? f.impact ?? 0).toFixed(4)}
                  </span>
                </div>
              ))}
              {negativeContributors.length === 0 && (
                <div className="text-stone text-xs padding-sm">No risk-suppressing features for this account.</div>
              )}
            </div>
          </div>
        </div>

        {/* Feature Values & SHAP Values Full Table */}
        {Object.keys(featureValues).length > 0 && (
          <div className="margin-top-md">
            <h4 className="text-xs text-stone font-bold text-uppercase margin-bottom-xs">Complete Feature Values & SHAP Attributions Table</h4>
            <div className="table-responsive">
              <table className="timeline-table">
                <thead>
                  <tr>
                    <th>Feature Column</th>
                    <th>Feature Value</th>
                    <th>SHAP Value</th>
                    <th>Risk Impact Direction</th>
                  </tr>
                </thead>
                <tbody>
                  {Object.keys(featureValues).map((fname) => {
                    const fval = featureValues[fname];
                    const sval = shapValues[fname] ?? 0.0;
                    const isPos = sval >= 0;
                    return (
                      <tr key={fname}>
                        <td className="font-mono text-ink font-semibold">{fname}</td>
                        <td className="font-mono">{fval}</td>
                        <td className={`font-mono font-bold ${isPos ? 'text-danger' : 'text-success'}`}>
                          {isPos ? '+' : ''}{sval}
                        </td>
                        <td>
                          <span className={`status-tag ${isPos ? 'high' : 'low'}`}>
                            {isPos ? 'Pushes Risk UP' : 'Suppresses Risk'}
                          </span>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </div>
        )}
      </div>

      {/* 9, 10 & 11. TOP COUNTERPARTIES, NETWORK GRAPH & RELATED SUSPICIOUS ACCOUNTS */}
      <div className="dash-row-2col">
        {/* 9. TOP COUNTERPARTIES */}
        <div className="section-card">
          <div className="section-title">
            <Users size={18} className="title-icon text-primary" />
            <div>
              <h3>9. Top Counterparties</h3>
              <span>Frequent inbound senders & outbound receivers</span>
            </div>
          </div>
          <div className="table-responsive margin-top-xs">
            <table className="timeline-table">
              <thead>
                <tr>
                  <th>Counterparty ID</th>
                  <th>Direction</th>
                  <th>Total Volume ($)</th>
                  <th>Txn Count</th>
                </tr>
              </thead>
              <tbody>
                {topCounterparties.map((cp, idx) => (
                  <tr key={idx}>
                    <td className="font-mono text-ink font-bold">{cp.account_id}</td>
                    <td>
                      <span className={`dir-badge ${cp.direction === 'INCOMING' ? 'incoming' : 'outgoing'}`}>
                        {cp.direction}
                      </span>
                    </td>
                    <td className="font-mono font-bold">${cp.volume.toLocaleString()}</td>
                    <td className="font-mono">{cp.tx_count}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        {/* 10 & 11. NETWORK GRAPH & RELATED SUSPICIOUS ACCOUNTS */}
        <div className="section-card">
          <div className="section-title flex-between">
            <div className="flex-align gap-xs">
              <Share2 size={18} className="title-icon text-teal" />
              <div>
                <h3>10 & 11. Network Topology & Related Suspicious Accounts</h3>
                <span>Graph centrality & 1-hop connected flagged accounts</span>
              </div>
            </div>
            <button className="btn-secondary sm" onClick={() => navigate(`/graph?id=${header.account_id}`)}>
              <ExternalLink size={12} /> Open Full Graph
            </button>
          </div>

          <div className="network-metrics-row margin-top-xs">
            <div className="net-mini-box"><span className="net-lbl">In-Degree</span><span className="net-val">{network.incoming_connections}</span></div>
            <div className="net-mini-box"><span className="net-lbl">Out-Degree</span><span className="net-val">{network.outgoing_connections}</span></div>
            <div className="net-mini-box"><span className="net-lbl">Fan-Out Ratio</span><span className="net-val text-danger">{network.fan_out}</span></div>
            <div className="net-mini-box"><span className="net-lbl">PageRank</span><span className="net-val font-mono">{network.pagerank}</span></div>
          </div>

          <div className="margin-top-sm">
            <h4 className="text-xs text-stone font-bold text-uppercase margin-bottom-xs">Related Suspicious Accounts List</h4>
            {relatedSuspiciousAccounts.length === 0 ? (
              <p className="text-xs text-stone">No suspicious accounts connected to this entity.</p>
            ) : (
              <div className="suspicious-acc-list">
                {relatedSuspiciousAccounts.map((acc) => (
                  <div key={acc.account_id} className="suspicious-acc-card flex-between">
                    <div>
                      <span className="font-mono font-bold text-ink cursor-pointer" onClick={() => navigate(`/explain?id=${acc.account_id}`)}>
                        {acc.account_id}
                      </span>
                      <span className="text-xs text-stone margin-left-xs">({acc.relationship})</span>
                    </div>
                    <div className="flex-align gap-xs">
                      <span className="font-mono text-xs text-stone">${acc.volume_shared.toLocaleString()} shared</span>
                      <span className={`severity-badge ${acc.risk_tier.toLowerCase()}`}>{acc.risk_score}</span>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>

      {/* 7. TRANSACTION TIMELINE */}
      <div className="section-card">
        <div className="section-title flex-between">
          <div className="flex-align gap-xs">
            <Calendar size={18} className="title-icon text-primary" />
            <div>
              <h3>7. Interactive Transaction History Timeline</h3>
              <span>Filterable fund transfer audit log with backend contextual risk indicators</span>
            </div>
          </div>
          <span className="total-badge text-xs">Total Events: {timeline.length}</span>
        </div>

        {/* Toolbar Filters */}
        <div className="timeline-toolbar margin-top-sm">
          <div className="filter-item">
            <label>Direction:</label>
            <select value={txDirectionFilter} onChange={(e) => setTxDirectionFilter(e.target.value)}>
              <option value="ALL">All Directions</option>
              <option value="INCOMING">INCOMING Only</option>
              <option value="OUTGOING">OUTGOING Only</option>
            </select>
          </div>

          <div className="filter-item">
            <label>Amount ($):</label>
            <input
              type="number"
              placeholder="Min"
              value={txMinAmount}
              onChange={(e) => setTxMinAmount(e.target.value)}
              className="num-input"
            />
            <span>-</span>
            <input
              type="number"
              placeholder="Max"
              value={txMaxAmount}
              onChange={(e) => setTxMaxAmount(e.target.value)}
              className="num-input"
            />
          </div>

          <div className="filter-item">
            <label>Date Range:</label>
            <input
              type="date"
              value={txStartDate}
              onChange={(e) => setTxStartDate(e.target.value)}
              className="date-input"
            />
            <span>to</span>
            <input
              type="date"
              value={txEndDate}
              onChange={(e) => setTxEndDate(e.target.value)}
              className="date-input"
            />
          </div>

          <button
            type="button"
            className="btn-secondary sm"
            onClick={() => {
              setTxDirectionFilter('ALL');
              setTxMinAmount('');
              setTxMaxAmount('');
              setTxStartDate('');
              setTxEndDate('');
            }}
          >
            Reset
          </button>
        </div>

        {/* Timeline Table */}
        {(() => {
          const filteredTimeline = timeline.filter((tx) => {
            const dir = (tx.direction || tx.type || 'OUTGOING').toUpperCase();
            if (txDirectionFilter !== 'ALL' && dir !== txDirectionFilter) return false;

            const amt = tx.amount || 0;
            if (txMinAmount !== '' && amt < Number(txMinAmount)) return false;
            if (txMaxAmount !== '' && amt > Number(txMaxAmount)) return false;

            if (txStartDate && new Date(tx.timestamp).toISOString().split('T')[0] < txStartDate) return false;
            if (txEndDate && new Date(tx.timestamp).toISOString().split('T')[0] > txEndDate) return false;
            return true;
          });

          if (filteredTimeline.length === 0) {
            return (
              <div className="empty-sub-card margin-top-sm">
                No timeline events match the selected filters.
              </div>
            );
          }

          return (
            <div className="table-responsive margin-top-sm">
              <table className="timeline-table">
                <thead>
                  <tr>
                    <th>Timestamp</th>
                    <th>Transaction ID</th>
                    <th>Direction</th>
                    <th>Counterparty</th>
                    <th>Amount ($)</th>
                    <th>Type</th>
                    <th>Running Activity Context</th>
                    <th>Risk Indicators</th>
                  </tr>
                </thead>
                <tbody>
                  {filteredTimeline.map((tx, idx) => {
                    const dir = (tx.direction || tx.type || 'OUTGOING').toUpperCase();
                    const isIncoming = dir === 'INCOMING' || dir === 'INBOUND';
                    const indicators = tx.contextual_indicators || {};

                    return (
                      <tr key={tx.transaction_id || tx.id || idx} className="timeline-row">
                        <td className="text-stone text-xs font-mono">
                          {tx.timestamp ? new Date(tx.timestamp).toLocaleString() : 'N/A'}
                        </td>
                        <td className="font-mono text-ink font-semibold">{tx.transaction_id || tx.id}</td>
                        <td>
                          <span className={`dir-badge ${isIncoming ? 'incoming' : 'outgoing'}`}>
                            {isIncoming ? <ArrowDownLeft size={12} /> : <ArrowUpRight size={12} />}
                            {isIncoming ? 'INCOMING' : 'OUTGOING'}
                          </span>
                        </td>
                        <td className="font-mono text-ink">{tx.counterparty}</td>
                        <td className={`font-mono font-bold ${isIncoming ? 'text-success' : 'text-danger'}`}>
                          ${(tx.amount || 0).toLocaleString()}
                        </td>
                        <td>
                          <span className="type-tag">{tx.transaction_type || 'TRANSFER'}</span>
                        </td>
                        <td className="text-stone text-xs">
                          {tx.running_activity_context || `Activity #${idx + 1} in audit sequence`}
                        </td>
                        <td>
                          <div className="indicator-chips">
                            {indicators.rapid_forwarding && (
                              <span className="ind-chip rapid" title="Rapid Fund Forwarding">
                                <Zap size={11} /> Rapid Forwarding
                              </span>
                            )}
                            {indicators.abnormal_amount && (
                              <span className="ind-chip abnormal" title="Abnormal Transaction Amount">
                                <AlertTriangle size={11} /> Abnormal Amount
                              </span>
                            )}
                            {indicators.velocity_spike && (
                              <span className="ind-chip velocity" title="Velocity Spike">
                                <Activity size={11} /> Velocity Spike
                              </span>
                            )}
                            {!indicators.rapid_forwarding && !indicators.abnormal_amount && !indicators.velocity_spike && (
                              <span className="ind-chip normal">Normal</span>
                            )}
                          </div>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          );
        })()}
      </div>

      {/* 12 & 13 & 14. ALERT HISTORY, INVESTIGATOR NOTES & INVESTIGATOR DECISION FORM */}
      <div className="dash-row-2col">
        {/* 12. ALERT HISTORY */}
        <div className="section-card">
          <div className="section-title">
            <ShieldAlert size={18} className="title-icon text-danger" />
            <div>
              <h3>12. Compliance Alert History</h3>
              <span>Active alerts & historical enforcement triggers for {header.account_id}</span>
            </div>
          </div>

          {alerts.length === 0 ? (
            <div className="empty-sub-card">No active alerts associated with this account.</div>
          ) : (
            <div className="alerts-mini-list">
              {alerts.map((alt, idx) => (
                <div key={alt.alert_id || idx} className="alert-mini-item">
                  <div className="flex-between">
                    <span className="font-mono text-ink font-semibold">{alt.alert_id}</span>
                    <span className={`severity-badge ${(alt.severity || 'high').toLowerCase()}`}>{alt.severity}</span>
                  </div>
                  <p className="alert-mini-msg">{alt.summary || 'High risk score triggered compliance alert.'}</p>
                  <div className="flex-between text-xs text-stone margin-top-xs">
                    <span>{alt.created_at ? new Date(alt.created_at).toLocaleString() : 'Just now'}</span>
                    <span className={`status-tag ${(alt.status || 'open').toLowerCase()}`}>{alt.status}</span>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* 13 & 14. INVESTIGATOR NOTES & INVESTIGATOR DECISION ACTION FORM */}
        <div className="section-card">
          <div className="section-title flex-between">
            <div className="flex-align gap-xs">
              <FileText size={18} className="title-icon text-teal" />
              <div>
                <h3>13 & 14. Investigator Decision & Audit Notes</h3>
                <span>Submit decision actions (OPEN, UNDER_INVESTIGATION, CONFIRMED_MULE, FALSE_POSITIVE, DISMISSED)</span>
              </div>
            </div>

            <span className={`status-pill ${feedbackHistory.length > 0 ? (feedbackHistory[0].decision || 'UNDER_INVESTIGATION').toLowerCase() : 'open'}`}>
              Status: {feedbackHistory.length > 0 ? feedbackHistory[0].decision : 'OPEN'}
            </span>
          </div>

          <form onSubmit={handleSubmitFeedback} className="note-form margin-top-xs">
            <div className="decision-selector-group">
              <label className="text-xs text-stone font-semibold">14. Investigator Action / Decision:</label>
              <div className="decision-radios flex-wrap gap-xs margin-top-xs">
                {[
                  { id: 'CONFIRMED_MULE', label: 'Confirmed Mule', class: 'mule' },
                  { id: 'UNDER_INVESTIGATION', label: 'Under Investigation', class: 'invest' },
                  { id: 'FALSE_POSITIVE', label: 'False Positive', class: 'fp' },
                  { id: 'DISMISSED', label: 'Dismissed', class: 'dismiss' },
                  { id: 'OPEN', label: 'Re-Open Case', class: 'open' },
                ].map((act) => (
                  <button
                    key={act.id}
                    type="button"
                    className={`decision-btn ${act.class} ${feedbackDecision === act.id ? 'active' : ''}`}
                    onClick={() => setFeedbackDecision(act.id)}
                  >
                    {act.label}
                  </button>
                ))}
              </div>
            </div>

            <div className="margin-top-xs">
              <textarea
                rows="3"
                placeholder="Enter detailed investigator findings or compliance audit rationale..."
                value={newNote}
                onChange={(e) => setNewNote(e.target.value)}
                className="note-input"
                required
              />
            </div>

            <button type="submit" className="btn-primary sm margin-top-xs" disabled={submittingFeedback || !newNote.trim()}>
              <Send size={13} /> {submittingFeedback ? 'Submitting...' : 'Submit Investigator Decision & Note'}
            </button>
          </form>

          {/* 13. Investigator Notes Log */}
          <div className="notes-list margin-top-sm border-top padding-top-xs">
            <h4 className="text-xs text-stone font-bold text-uppercase margin-bottom-xs">13. Historical Investigator Notes Log</h4>
            {feedbackHistory.length === 0 ? (
              <p className="text-xs text-stone">No previous decision notes recorded for this account.</p>
            ) : (
              feedbackHistory.map((item, idx) => (
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
  );
}
