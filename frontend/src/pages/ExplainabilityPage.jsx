import React, { useState, useEffect } from 'react';
import { useSearchParams, useNavigate } from 'react-router-dom';
import {
  BrainCircuit, ShieldAlert, ArrowLeft, Share2, AlertTriangle, CheckCircle,
  HelpCircle, Cpu, Zap, Activity, Clock, Layers, Users, ArrowUpRight,
  ArrowDownLeft, FileText, Send, RefreshCw, Calendar
} from 'lucide-react';
import { getExplanation, getRiskScores, getGlobalFeatureImportance } from '../api/client';
import './ExplainabilityPage.css';

export default function ExplainabilityPage() {
  const [searchParams] = useSearchParams();
  const paramId = searchParams.get('id');

  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [accountList, setAccountList] = useState([]);
  const [globalImportance, setGlobalImportance] = useState([]);
  const [newNote, setNewNote] = useState('');
  const [notesList, setNotesList] = useState([]);

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
      const [accountsRes, gImp] = await Promise.all([
        getRiskScores({ page_size: 100 }).catch(() => ({ accounts: [] })),
        getGlobalFeatureImportance().catch(() => []),
      ]);
      const accList = accountsRes.accounts || (Array.isArray(accountsRes) ? accountsRes : []);
      setAccountList(accList);
      setGlobalImportance(gImp);

      const resolvedId = paramId || (accList.length > 0 ? (accList[0].account_id || accList[0].id) : 'ACC-001001');
      if (!resolvedId) {
        setLoading(false);
        return;
      }

      const exp = await getExplanation(resolvedId);
      setData(exp);
      setNotesList(exp.notes || []);
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

  const handleAddNote = (e) => {
    e.preventDefault();
    if (!newNote.trim()) return;
    const noteObj = {
      id: `NOTE-${Date.now()}`,
      author: 'Current Investigator',
      timestamp: new Date().toISOString(),
      text: newNote.trim(),
    };
    setNotesList([noteObj, ...notesList]);
    setNewNote('');
  };

  if (loading) {
    return (
      <div className="invest-loading-container animate-fade-in">
        <div className="pulse-loader" />
        <h3>Fusing Multi-Model Investigation Engine</h3>
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

  // Section extractions
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
    average_forwarding_time: 24.5,
    median_forwarding_time: 18.0,
    percentage_forwarded_within_5m: 72.4,
    percentage_forwarded_within_15m: 88.6,
    retention_ratio: 0.04,
    incoming_outgoing_ratio: 1.04,
  };

  const temporalBehavior = data.temporal_behavior || {
    recent_volume_vs_historical: '$43,200 (24h) vs $5,200 (30d avg)',
    recent_amount_vs_historical: '$3,150 avg vs $450 historical avg',
    behavior_change_indicators: 'Abrupt dormancy break + volume surge',
  };

  const network = data.network || {
    incoming_connections: 6,
    outgoing_connections: 8,
    fan_in: 1.2,
    fan_out: 4.8,
    pagerank: 0.042,
    connected_suspicious_accounts: ['ACC-001012', 'ACC-001019'],
  };

  const explanation = data.model_explanation || {
    top_shap_features: data.top_shap_features || [],
    reason: data.reason || 'High risk score driven by automated feature attribution.',
  };

  const shapFeatures = explanation.top_shap_features || data.features || [];
  const maxImpact = Math.max(...shapFeatures.map((f) => Math.abs(f.shap_value ?? f.impact ?? 0.1)), 0.01);

  const timeline = data.timeline || [];
  const alerts = data.alerts || [];

  const tierClass = (header.risk_tier || 'low').toLowerCase();

  return (
    <div className="explain-page animate-fade-in">
      {/* 1. HEADER */}
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

      {/* 2. RISK SUMMARY SECTION */}
      <div className="section-card">
        <div className="section-title">
          <BrainCircuit size={18} className="title-icon" />
          <div>
            <h3>2. Fused Multi-Model Risk Summary</h3>
            <span>XGBoost Supervised ML, Isolation Forest Anomaly Engine & Graph Network Risk</span>
          </div>
        </div>

        <div className="kpi-grid grid-4">
          <div className="metric-box">
            <span className="metric-label"><Cpu size={13} /> Supervised ML Prob (XGBoost)</span>
            <div className="metric-val text-danger">{riskSummary.supervised_ml_probability}%</div>
            <span className="metric-sub">P(Mule Pattern = 1)</span>
          </div>
          <div className="metric-box">
            <span className="metric-label"><Activity size={13} /> Anomaly Score (IsoForest / Z)</span>
            <div className="metric-val text-warning">{riskSummary.anomaly_score} / 100</div>
            <span className="metric-sub">Outlier Deviation Metric</span>
          </div>
          <div className="metric-box">
            <span className="metric-label"><Layers size={13} /> Graph Network Risk Score</span>
            <div className="metric-val text-danger">{riskSummary.network_risk_score} / 100</div>
            <span className="metric-sub">Centrality & Cycle Membership</span>
          </div>
          <div className="metric-box">
            <span className="metric-label"><ShieldAlert size={13} /> Final Fused Risk Index</span>
            <div className="metric-val text-ink font-mono">{riskSummary.final_fused_risk_score} / 100</div>
            <span className="metric-sub">Ensemble Weighted Fusion</span>
          </div>
        </div>
      </div>

      {/* 3 & 4. BEHAVIOR & VELOCITY ROW */}
      <div className="dash-row-2col">
        {/* 3. BEHAVIOR */}
        <div className="section-card">
          <div className="section-title">
            <Users size={18} className="title-icon" />
            <div>
              <h3>3. Account Behavioral Metrics</h3>
              <span>Transactional counts, amounts & counterparty breadth</span>
            </div>
          </div>
          <div className="info-grid grid-3">
            <div className="info-item"><span className="info-lbl">Total Txns (24h)</span><span className="info-val">{behavior.transaction_count}</span></div>
            <div className="info-item"><span className="info-lbl">Incoming Count</span><span className="info-val text-success">{behavior.incoming_count}</span></div>
            <div className="info-item"><span className="info-lbl">Outgoing Count</span><span className="info-val text-danger">{behavior.outgoing_count}</span></div>
            <div className="info-item"><span className="info-lbl">Incoming Amount</span><span className="info-val font-mono">${behavior.incoming_amount.toLocaleString()}</span></div>
            <div className="info-item"><span className="info-lbl">Outgoing Amount</span><span className="info-val font-mono">${behavior.outgoing_amount.toLocaleString()}</span></div>
            <div className="info-item"><span className="info-lbl">Avg Txn Size</span><span className="info-val font-mono">${behavior.average_transaction_amount.toLocaleString()}</span></div>
            <div className="info-item"><span className="info-lbl">Unique Counterparties</span><span className="info-val">{behavior.unique_counterparties}</span></div>
            <div className="info-item"><span className="info-lbl">Active Days</span><span className="info-val">{behavior.active_days} days</span></div>
            <div className="info-item"><span className="info-lbl">Account Age</span><span className="info-val">{behavior.account_age} days</span></div>
          </div>
        </div>

        {/* 4. VELOCITY */}
        <div className="section-card">
          <div className="section-title">
            <Zap size={18} className="title-icon text-warning" />
            <div>
              <h3>4. Transaction Velocity & Burst Analysis</h3>
              <span>High-frequency transaction monitoring intervals</span>
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

      {/* 5 & 6. FUND FLOW & TEMPORAL BEHAVIOR ROW */}
      <div className="dash-row-2col">
        {/* 5. FUND FLOW VISUALIZATION */}
        <div className="section-card">
          <div className="section-title">
            <ArrowUpRight size={18} className="title-icon text-danger" />
            <div>
              <h3>5. Pass-Through Fund Flow Visualization</h3>
              <span>Backend-analyzed incoming to outgoing fund forwarding chains & latency</span>
            </div>
          </div>

          {/* Fund Flow Summary Bar */}
          <div className="fund-flow-summary-bar margin-top-xs">
            <div className="ff-stat">
              <span className="ff-lbl">Total Received</span>
              <span className="ff-val font-mono text-success">
                ${(fundFlow.total_received ?? behavior.incoming_amount ?? 0).toLocaleString()}
              </span>
            </div>
            <div className="ff-stat">
              <span className="ff-lbl">Total Forwarded</span>
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
                {fundFlow.average_forwarding_delay ?? fundFlow.average_forwarding_time ?? 0} min
              </span>
            </div>
          </div>

          {/* Matched Pass-Through Chains Visualization */}
          <div className="fund-flow-chains-list margin-top-sm">
            {(fundFlow.flow_chains || []).map((chain, cIdx) => {
              const inTx = chain.incoming || {};
              const outTx = chain.outgoing || {};
              const isRapid = chain.is_rapid_forwarding;

              return (
                <div key={chain.chain_id || cIdx} className={`flow-chain-card ${isRapid ? 'rapid-highlight' : ''}`}>
                  <div className="chain-header flex-between">
                    <span className="chain-id font-mono font-bold">Pass-Through Chain #{cIdx + 1} ({chain.chain_id})</span>
                    {isRapid && (
                      <span className="rapid-badge">
                        <Zap size={12} /> RAPID FORWARDING EVENT ({chain.time_difference_label})
                      </span>
                    )}
                  </div>

                  {/* Flow Diagram */}
                  <div className="flow-diagram-vertical margin-top-xs">
                    {/* Node 1: Incoming Transaction */}
                    <div className="flow-node incoming-node">
                      <div className="node-icon"><ArrowDownLeft size={14} className="text-success" /></div>
                      <div className="node-content">
                        <span className="node-title">INCOMING TRANSACTION</span>
                        <div className="node-details">
                          <span className="font-mono font-semibold">From: {inTx.sender_account}</span>
                          <span className="font-mono text-success font-bold">${(inTx.amount || 0).toLocaleString()}</span>
                        </div>
                        <span className="node-time text-xs text-stone font-mono">
                          {inTx.timestamp ? new Date(inTx.timestamp).toLocaleString() : 'N/A'}
                        </span>
                      </div>
                    </div>

                    {/* Transition 1: Latency Arrow */}
                    <div className="flow-connector">
                      <div className="connector-line" />
                      <div className={`connector-pill ${isRapid ? 'rapid' : ''}`}>
                        <Clock size={11} />
                        <span>Latency: {chain.time_difference_label || `${chain.time_difference_minutes} min`}</span>
                      </div>
                      <div className="connector-line" />
                    </div>

                    {/* Node 2: Target Account */}
                    <div className="flow-node account-node">
                      <div className="node-icon"><Layers size={14} className="text-primary" /></div>
                      <div className="node-content">
                        <span className="node-title">ACCOUNT UNDER AUDIT</span>
                        <div className="node-details">
                          <span className="font-mono font-bold text-ink">{header.account_id}</span>
                          <span className="text-xs text-stone">Retained Fee: ${(chain.retained_fee || 0).toLocaleString()}</span>
                        </div>
                      </div>
                    </div>

                    {/* Transition 2: Outbound Arrow */}
                    <div className="flow-connector">
                      <div className="connector-line" />
                      <div className="connector-pill outbound">
                        <ArrowUpRight size={11} />
                        <span>Outbound Transfer</span>
                      </div>
                      <div className="connector-line" />
                    </div>

                    {/* Node 3: Outgoing Transaction */}
                    <div className="flow-node outgoing-node">
                      <div className="node-icon"><ArrowUpRight size={14} className="text-danger" /></div>
                      <div className="node-content">
                        <span className="node-title">OUTGOING TRANSACTION</span>
                        <div className="node-details">
                          <span className="font-mono font-danger font-bold">${(outTx.amount || 0).toLocaleString()}</span>
                          <span className="node-time text-xs text-stone font-mono">
                            {outTx.timestamp ? new Date(outTx.timestamp).toLocaleString() : 'N/A'}
                          </span>
                        </div>
                      </div>
                    </div>

                    {/* Transition 3: Receiver Arrow */}
                    <div className="flow-connector">
                      <div className="connector-line" />
                      <div className="connector-pill receiver">
                        <span>Destination</span>
                      </div>
                      <div className="connector-line" />
                    </div>

                    {/* Node 4: Receiver */}
                    <div className="flow-node receiver-node">
                      <div className="node-icon"><Users size={14} className="text-warning" /></div>
                      <div className="node-content">
                        <span className="node-title">RECEIVER COUNTERPARTY</span>
                        <div className="node-details">
                          <span className="font-mono font-semibold text-ink">To: {outTx.receiver_account}</span>
                        </div>
                      </div>
                    </div>
                  </div>

                  {isRapid && chain.rapid_forwarding_reason && (
                    <div className="rapid-reason-box margin-top-xs">
                      <AlertTriangle size={13} className="text-warning" />
                      <span>{chain.rapid_forwarding_reason}</span>
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        </div>


        {/* 6. TEMPORAL BEHAVIOR */}
        <div className="section-card">
          <div className="section-title">
            <Clock size={18} className="title-icon" />
            <div>
              <h3>6. Temporal Behavior & Drift Analysis</h3>
              <span>Recent vs. historical baseline variance</span>
            </div>
          </div>
          <div className="temporal-list">
            <div className="temporal-item">
              <span className="t-label">Recent vs. Historical Volume</span>
              <span className="t-val font-mono">{temporalBehavior.recent_volume_vs_historical}</span>
            </div>
            <div className="temporal-item">
              <span className="t-label">Recent vs. Historical Avg Amount</span>
              <span className="t-val font-mono">{temporalBehavior.recent_amount_vs_historical}</span>
            </div>
            <div className="callout-box">
              <Activity size={15} className="text-danger" />
              <span>{temporalBehavior.behavior_change_indicators}</span>
            </div>
          </div>
        </div>
      </div>

      {/* 7. NETWORK GRAPH METRICS */}
      <div className="section-card">
        <div className="section-title">
          <Share2 size={18} className="title-icon" />
          <div>
            <h3>7. Network Topology & Counterparty Risk</h3>
            <span>Graph centrality, fan-in/fan-out ratios, and connected flagged accounts</span>
          </div>
        </div>
        <div className="kpi-grid grid-4">
          <div className="metric-box">
            <span className="metric-label"><ArrowDownLeft size={13} /> Incoming Connections</span>
            <div className="metric-val">{network.incoming_connections} (Fan-In: {network.fan_in})</div>
            <span className="metric-sub">In-Degree Centrality</span>
          </div>
          <div className="metric-box">
            <span className="metric-label"><ArrowUpRight size={13} /> Outgoing Connections</span>
            <div className="metric-val">{network.outgoing_connections} (Fan-Out: {network.fan_out})</div>
            <span className="metric-sub">Out-Degree Centrality</span>
          </div>
          <div className="metric-box">
            <span className="metric-label"><Layers size={13} /> PageRank Score</span>
            <div className="metric-val font-mono">{network.pagerank}</div>
            <span className="metric-sub">Network Importance Score</span>
          </div>
          <div className="metric-box">
            <span className="metric-label"><ShieldAlert size={13} /> Connected Suspicious Accounts</span>
            <div className="metric-val text-danger">
              {network.connected_suspicious_accounts.length > 0
                ? network.connected_suspicious_accounts.join(', ')
                : 'None Flagged'}
            </div>
            <span className="metric-sub">Flagged 1-Hop Neighbors</span>
          </div>
        </div>
      </div>

      {/* 8. MODEL EXPLANATION (SHAP & XAI) */}
      <div className="section-card">
        <div className="section-title">
          <BrainCircuit size={18} className="title-icon text-primary" />
          <div>
            <h3>8. Explainable AI (XAI) & SHAP Model Explanations</h3>
            <span>Backend-generated game-theoretic feature attributions for {header.account_id}</span>
          </div>
        </div>

        <div className="reason-box margin-top-xs">
          <p><strong>Backend Reason Statement:</strong> {explanation.reason}</p>
        </div>

        {/* 4-Tab / 4-Sub-Card XAI Grid */}
        <div className="xai-grid margin-top-md">
          {/* Sub-Card 1: Account-Specific Explanation */}
          <div className="xai-sub-card">
            <div className="xai-card-title">
              <Zap size={14} className="text-warning" />
              <h4>Account-Specific Explanation ({header.account_id})</h4>
            </div>
            <div className="why-high-risk-box">
              <span className="why-title">Why this account is {header.risk_tier} risk:</span>
              <div className="why-list">
                {shapFeatures.slice(0, 5).map((f, i) => {
                  const sVal = f.shap_value ?? f.impact ?? 0;
                  const isPos = f.impact_direction ? f.impact_direction === 'positive' : sVal >= 0;
                  const signStr = isPos ? '+' : '';
                  return (
                    <div key={i} className="why-row">
                      <span className="why-rank">#{f.importance_rank || i + 1}</span>
                      <span className="why-name">{f.feature_name || f.feature}</span>
                      <span className="why-val font-mono">Val: {f.feature_value ?? f.value}</span>
                      <span className={`why-shap font-mono ${isPos ? 'text-danger' : 'text-success'}`}>
                        {signStr}{sVal.toFixed(2)}
                      </span>
                    </div>
                  );
                })}
              </div>
            </div>
          </div>

          {/* Sub-Card 2: Global Feature Importance View */}
          <div className="xai-sub-card">
            <div className="xai-card-title">
              <BrainCircuit size={14} className="text-primary" />
              <h4>Global Model Feature Importance</h4>
            </div>
            <div className="global-importance-list">
              {globalImportance.slice(0, 5).map((g, i) => (
                <div key={i} className="global-imp-row">
                  <span className="imp-rank">#{g.importance_rank}</span>
                  <span className="imp-name">{g.feature_name}</span>
                  <div className="imp-bar-track">
                    <div className="imp-bar-fill" style={{ width: `${Math.round(g.importance * 100)}%` }} />
                  </div>
                  <span className="imp-weight font-mono">{(g.importance * 100).toFixed(1)}%</span>
                </div>
              ))}
            </div>
          </div>

          {/* Sub-Card 3: Top Positive Risk Contributors */}
          <div className="xai-sub-card">
            <div className="xai-card-title">
              <ArrowUpRight size={14} className="text-danger" />
              <h4>Top Positive Risk Contributors (+ SHAP)</h4>
            </div>
            <div className="contrib-list">
              {(data.model_explanation?.positive_contributors || data.positive_contributors || shapFeatures.filter(f => (f.shap_value ?? f.impact ?? 0) >= 0)).slice(0, 4).map((f, i) => (
                <div key={i} className="contrib-row pos">
                  <div className="contrib-info">
                    <span className="contrib-name">{f.feature_name || f.feature}</span>
                    <span className="contrib-detail">Rank #{f.importance_rank || i + 1} • Val: {f.feature_value ?? f.value}</span>
                  </div>
                  <span className="contrib-val text-danger font-mono">
                    +{(f.shap_value ?? f.impact ?? 0).toFixed(4)}
                  </span>
                </div>
              ))}
            </div>
          </div>

          {/* Sub-Card 4: Top Negative Risk Contributors */}
          <div className="xai-sub-card">
            <div className="xai-card-title">
              <CheckCircle size={14} className="text-success" />
              <h4>Top Negative Risk Contributors (- SHAP)</h4>
            </div>
            <div className="contrib-list">
              {(data.model_explanation?.negative_contributors || data.negative_contributors || shapFeatures.filter(f => (f.shap_value ?? f.impact ?? 0) < 0)).slice(0, 4).map((f, i) => (
                <div key={i} className="contrib-row neg">
                  <div className="contrib-info">
                    <span className="contrib-name">{f.feature_name || f.feature}</span>
                    <span className="contrib-detail">Rank #{f.importance_rank || i + 1} • Val: {f.feature_value ?? f.value}</span>
                  </div>
                  <span className="contrib-val text-success font-mono">
                    {(f.shap_value ?? f.impact ?? 0).toFixed(4)}
                  </span>
                </div>
              ))}
              {(data.model_explanation?.negative_contributors || []).length === 0 && (
                <div className="text-stone text-xs padding-sm">No risk-suppressing features for this account.</div>
              )}
            </div>
          </div>
        </div>
      </div>


      {/* 9. TRANSACTION TIMELINE */}
      <div className="section-card">
        <div className="section-title flex-between">
          <div className="flex-align gap-xs">
            <Calendar size={18} className="title-icon text-primary" />
            <div>
              <h3>9. Account Transaction History Timeline</h3>
              <span>Chronological fund transfer audit with backend contextual risk indicators</span>
            </div>
          </div>
          <span className="total-badge text-xs">Total Events: {timeline.length}</span>
        </div>

        {/* Timeline Toolbar Filters */}
        <div className="timeline-toolbar margin-top-sm">
          {/* Direction Filter */}
          <div className="filter-item">
            <label>Direction:</label>
            <select value={txDirectionFilter} onChange={(e) => setTxDirectionFilter(e.target.value)}>
              <option value="ALL">All Directions</option>
              <option value="INCOMING">INCOMING Only</option>
              <option value="OUTGOING">OUTGOING Only</option>
            </select>
          </div>

          {/* Amount Range Filter */}
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

          {/* Date Range Filter */}
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

        {/* Filtered Timeline List */}
        {(() => {
          const filteredTimeline = timeline.filter((tx) => {
            const dir = (tx.direction || tx.type || 'OUTGOING').toUpperCase();
            if (txDirectionFilter !== 'ALL' && dir !== txDirectionFilter) return false;

            const amt = tx.amount || 0;
            if (txMinAmount !== '' && amt < Number(txMinAmount)) return false;
            if (txMaxAmount !== '' && amt > Number(txMaxAmount)) return false;

            if (txStartDate) {
              const txDate = new Date(tx.timestamp).toISOString().split('T')[0];
              if (txDate < txStartDate) return false;
            }
            if (txEndDate) {
              const txDate = new Date(tx.timestamp).toISOString().split('T')[0];
              if (txDate > txEndDate) return false;
            }
            return true;
          });

          if (filteredTimeline.length === 0) {
            return (
              <div className="empty-sub-card margin-top-sm">
                No timeline events match the selected direction, amount, or date range filters.
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
                    <th>Backend Indicators</th>
                  </tr>
                </thead>
                <tbody>
                  {filteredTimeline.map((tx, idx) => {
                    const dir = (tx.direction || tx.type || 'OUTGOING').toUpperCase();
                    const isIncoming = dir === 'INCOMING' || dir === 'INBOUND';
                    const indicators = tx.contextual_indicators || {};
                    const labels = indicators.indicator_labels || [];

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
                              <span className="ind-chip rapid" title="Backend Analysis: Rapid Fund Forwarding">
                                <Zap size={11} /> Rapid Forwarding
                              </span>
                            )}
                            {indicators.abnormal_amount && (
                              <span className="ind-chip abnormal" title="Backend Analysis: Abnormal Transaction Amount">
                                <AlertTriangle size={11} /> Abnormal Amount
                              </span>
                            )}
                            {indicators.velocity_spike && (
                              <span className="ind-chip velocity" title="Backend Analysis: Velocity Spike">
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

      {/* 10 & 11. ALERTS & INVESTIGATOR NOTES ROW */}

      <div className="dash-row-2col">
        {/* 10. ALERTS & HISTORY */}
        <div className="section-card">
          <div className="section-title">
            <ShieldAlert size={18} className="title-icon text-danger" />
            <div>
              <h3>10. Related Compliance Alerts</h3>
              <span>Active alerts & historical enforcement triggers</span>
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

        {/* 11. INVESTIGATOR NOTES */}
        <div className="section-card">
          <div className="section-title">
            <FileText size={18} className="title-icon" />
            <div>
              <h3>11. Investigator Audit Notes</h3>
              <span>Compliance reviewer log & case notes</span>
            </div>
          </div>

          <form onSubmit={handleAddNote} className="note-form">
            <textarea
              rows="3"
              placeholder="Add investigator note or compliance findings..."
              value={newNote}
              onChange={(e) => setNewNote(e.target.value)}
              className="note-input"
            />
            <button type="submit" className="btn-primary sm margin-top-xs">
              <Send size={13} /> Save Note
            </button>
          </form>

          <div className="notes-list margin-top-sm">
            {notesList.map((note) => (
              <div key={note.id} className="note-card">
                <div className="flex-between text-xs text-stone">
                  <strong>{note.author}</strong>
                  <span>{new Date(note.timestamp).toLocaleString()}</span>
                </div>
                <p className="note-text">{note.text}</p>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
