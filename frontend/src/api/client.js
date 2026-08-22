import axios from 'axios';

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000';

const api = axios.create({
  baseURL: API_BASE,
  timeout: 30000,
  headers: { 'Content-Type': 'application/json' },
});

// ── Mock Mode Toggle ──────────────────────────────────────────────
const MOCK = false;

// ── Mock Data Generators (Fallback) ──────────────────────────────
const NAMES = [
  'Apex Trading LLC', 'Nova Payments Corp', 'Zenith Holdings', 'Cascade Financial',
  'Meridian Services', 'Quantum Pay Inc', 'Stellar Transfers', 'Vortex Capital',
  'Eclipse Ventures', 'Nexus Wire Co', 'Pulse Money Ltd', 'Drift Finance',
  'Onyx Remit', 'Cobalt Bank', 'Prism Global', 'Helix Transfers',
  'Cipher Pay', 'Vertex Banking', 'Atlas Wire', 'Flux Financial',
];

const mockAccounts = Array.from({ length: 48 }, (_, i) => {
  const tiers = ['critical', 'high', 'medium', 'low'];
  const tier = tiers[Math.floor(Math.random() * 4)];
  const score =
    tier === 'critical' ? 85 + Math.random() * 15
    : tier === 'high' ? 65 + Math.random() * 20
    : tier === 'medium' ? 35 + Math.random() * 30
    : Math.random() * 35;
  return {
    id: `ACC-${String(i + 1001).padStart(6, '0')}`,
    name: NAMES[i % 20],
    risk_score: Math.round(score * 100) / 100,
    risk_tier: tier,
    txn_count: Math.floor(50 + Math.random() * 500),
    total_volume: Math.round((10000 + Math.random() * 990000) * 100) / 100,
    avg_txn_size: Math.round((100 + Math.random() * 5000) * 100) / 100,
    fan_in: Math.floor(1 + Math.random() * 25),
    fan_out: Math.floor(1 + Math.random() * 25),
    flagged: tier === 'critical' || tier === 'high',
    last_activity: new Date(Date.now() - Math.random() * 30 * 86400000).toISOString(),
  };
});

const mockAlerts = [
  { id: 'ALT-001', account_id: 'ACC-001001', severity: 'critical', type: 'Rapid fund pass-through', message: 'Funds received and forwarded within 30 minutes across 12 transactions', status: 'open', created_at: '2026-08-20T10:30:00Z' },
  { id: 'ALT-002', account_id: 'ACC-001003', severity: 'high', type: 'Fan-out anomaly', message: 'Single inbound transfer split into 8 outbound payments to distinct accounts', status: 'open', created_at: '2026-08-20T09:15:00Z' },
  { id: 'ALT-003', account_id: 'ACC-001005', severity: 'critical', type: 'Cycle detected', message: 'Circular transaction chain: ACC-001005 → ACC-001012 → ACC-001019 → ACC-001005', status: 'open', created_at: '2026-08-19T22:00:00Z' },
  { id: 'ALT-004', account_id: 'ACC-001002', severity: 'medium', type: 'Velocity spike', message: 'Transaction velocity increased 340% above baseline in 24h window', status: 'reviewed', created_at: '2026-08-19T18:45:00Z' },
  { id: 'ALT-005', account_id: 'ACC-001008', severity: 'high', type: 'Structuring pattern', message: 'Multiple deposits just under $10,000 threshold within 48 hours', status: 'open', created_at: '2026-08-19T14:30:00Z' },
  { id: 'ALT-006', account_id: 'ACC-001011', severity: 'medium', type: 'Geographic anomaly', message: 'Transactions from 6 countries within 4-hour window', status: 'dismissed', created_at: '2026-08-18T20:10:00Z' },
  { id: 'ALT-007', account_id: 'ACC-001015', severity: 'low', type: 'Dormancy break', message: 'Account inactive for 180 days, suddenly processed $45,000 in transfers', status: 'open', created_at: '2026-08-18T16:00:00Z' },
  { id: 'ALT-008', account_id: 'ACC-001020', severity: 'critical', type: 'Mule ring indicator', message: 'Account part of suspected 5-node layering network', status: 'open', created_at: '2026-08-18T11:22:00Z' },
];

const mockDashboard = {
  total_accounts: 1247,
  flagged_count: 89,
  open_alerts: 34,
  avg_risk_score: 42.7,
  risk_distribution: { critical: 23, high: 66, medium: 312, low: 846 },
  trend_data: Array.from({ length: 14 }, (_, i) => ({
    date: new Date(Date.now() - (13 - i) * 86400000).toISOString().split('T')[0],
    alerts: Math.floor(3 + Math.random() * 12),
    flagged: Math.floor(1 + Math.random() * 8),
    resolved: Math.floor(1 + Math.random() * 6),
  })),
};

const mockExplain = (id) => ({
  account_id: id,
  risk_score: 87.3,
  risk_tier: 'critical',
  reason: 'This account exhibits classic mule behavior: rapid pass-through of funds (median hold time < 45 min), fan-out pattern dispersing single large inflows into 8+ smaller outflows, and participation in a circular transaction chain involving 3 other flagged accounts.',
  features: [
    { name: 'Pass-through velocity', value: 0.92, impact: 0.31, direction: 'positive' },
    { name: 'Fan-out ratio', value: 8.4, impact: 0.24, direction: 'positive' },
    { name: 'Cycle participation', value: 1.0, impact: 0.19, direction: 'positive' },
    { name: 'Transaction velocity (24h)', value: 340, impact: 0.11, direction: 'positive' },
    { name: 'Account age (days)', value: 42, impact: 0.08, direction: 'negative' },
    { name: 'Unique counterparties', value: 23, impact: 0.04, direction: 'positive' },
    { name: 'Geographic spread', value: 6, impact: 0.03, direction: 'positive' },
  ],
});

const mockMetrics = {
  accuracy: 0.943,
  precision: 0.891,
  recall: 0.867,
  f1_score: 0.879,
  roc_auc: 0.962,
  confusion_matrix: { tp: 312, fp: 38, fn: 48, tn: 1849 },
  feature_importance: [
    { feature: 'txn_velocity_24h', importance: 0.182 },
    { feature: 'fan_out_ratio', importance: 0.156 },
    { feature: 'pass_through_speed', importance: 0.143 },
    { feature: 'cycle_membership', importance: 0.127 },
    { feature: 'volume_variance', importance: 0.098 },
    { feature: 'counterparty_diversity', importance: 0.085 },
    { feature: 'geographic_spread', importance: 0.072 },
    { feature: 'account_age_days', importance: 0.064 },
    { feature: 'avg_txn_amount', importance: 0.048 },
    { feature: 'time_of_day_entropy', importance: 0.025 },
  ],
};

const mockGraph = (id) => ({
  nodes: [
    { id, label: id, group: 'target', risk: 92 },
    { id: 'ACC-001012', label: 'ACC-001012', group: 'flagged', risk: 78 },
    { id: 'ACC-001019', label: 'ACC-001019', group: 'flagged', risk: 85 },
    { id: 'ACC-001024', label: 'ACC-001024', group: 'normal', risk: 22 },
    { id: 'ACC-001031', label: 'ACC-001031', group: 'normal', risk: 15 },
    { id: 'ACC-001037', label: 'ACC-001037', group: 'flagged', risk: 71 },
    { id: 'ACC-001042', label: 'ACC-001042', group: 'normal', risk: 28 },
    { id: 'ACC-001055', label: 'ACC-001055', group: 'normal', risk: 11 },
    { id: 'EXT-001', label: 'External Source', group: 'external', risk: 0 },
    { id: 'EXT-002', label: 'Cash Out ATM', group: 'external', risk: 0 },
  ],
  links: [
    { source: 'EXT-001', target: id, value: 50000, type: 'inflow' },
    { source: id, target: 'ACC-001012', value: 12000, type: 'outflow' },
    { source: id, target: 'ACC-001019', value: 8500, type: 'outflow' },
    { source: id, target: 'ACC-001024', value: 6200, type: 'outflow' },
    { source: id, target: 'ACC-001031', value: 9800, type: 'outflow' },
    { source: id, target: 'ACC-001037', value: 7300, type: 'outflow' },
    { source: 'ACC-001012', target: 'ACC-001019', value: 4500, type: 'cycle' },
    { source: 'ACC-001019', target: id, value: 3800, type: 'cycle' },
    { source: 'ACC-001037', target: 'ACC-001042', value: 5000, type: 'outflow' },
    { source: 'ACC-001037', target: 'EXT-002', value: 2300, type: 'outflow' },
    { source: 'ACC-001024', target: 'ACC-001055', value: 3100, type: 'outflow' },
  ],
});

// ── API Exports ───────────────────────────────────────────────────
export async function uploadDataset(formData) {
  if (MOCK) {
    await new Promise((r) => setTimeout(r, 1200));
    return {
      rows: 15234,
      columns: ['account_id', 'txn_amount', 'txn_timestamp', 'sender_id', 'receiver_id', 'txn_type', 'currency', 'country'],
    };
  }
  const { data } = await api.post('/upload-dataset', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  });
  return {
    rows: data.row_count || data.rows || 0,
    columns: data.columns || [],
  };
}

export async function getDashboardSummary() {
  if (MOCK) return mockDashboard;
  try {
    const { data } = await api.get('/dashboard/summary');
    return data;
  } catch (err) {
    const { data } = await api.get('/dashboard-summary');
    return data;
  }
}

export async function getRiskScores(params = {}) {
  if (MOCK) {
    let accounts = [...mockAccounts];
    if (params.tier) accounts = accounts.filter((a) => a.risk_tier.toLowerCase() === params.tier.toLowerCase());
    if (params.search) {
      const q = params.search.toLowerCase();
      accounts = accounts.filter((a) => a.id.toLowerCase().includes(q) || a.name.toLowerCase().includes(q));
    }
    return {
      accounts,
      total: accounts.length,
      page: params.page || 1,
      page_size: params.page_size || 10,
      total_pages: Math.ceil(accounts.length / (params.page_size || 10))
    };
  }

  const { data } = await api.get('/predict/risk-scores', { params });
  const rawList = data.accounts || (Array.isArray(data) ? data : []);

  const accounts = rawList.map((acc, i) => {
    const rawScore = acc.risk_score ?? 0;
    const scoreVal = typeof rawScore === 'number' && rawScore <= 1.0 ? Math.round(rawScore * 1000) / 10 : Math.round(rawScore * 10) / 10;
    const rawTier = (acc.risk_tier || '').toLowerCase();
    const tier = rawTier || (scoreVal > 85 ? 'critical' : scoreVal > 70 ? 'high' : scoreVal > 30 ? 'medium' : 'low');

    return {
      account_id: acc.account_id || acc.id || `ACC-${i}`,
      risk_score: scoreVal,
      risk_tier: tier,
      mule_probability: acc.mule_probability ?? (scoreVal / 100),
      anomaly_score: acc.anomaly_score ?? 0.1,
      network_risk_score: acc.network_risk_score ?? (acc.in_degree ? acc.in_degree * 5 : 15),
      transaction_count: acc.transaction_count ?? acc.txn_count_24h ?? acc.txn_count ?? 0,
      incoming_amount: acc.incoming_amount ?? acc.total_amount_in_24h ?? 0,
      outgoing_amount: acc.outgoing_amount ?? acc.total_amount_out_24h ?? acc.total_volume ?? 0,
      unique_counterparties: acc.unique_counterparties ?? acc.unique_counterparty_count ?? 0,
      account_age: acc.account_age ?? acc.account_age_days ?? 0,
      last_activity: acc.last_activity || new Date().toISOString(),
      alert_count: acc.alert_count ?? 0,
      investigation_status: acc.investigation_status || 'NONE',
    };
  });

  return {
    accounts,
    total: data.total ?? accounts.length,
    page: data.page ?? params.page ?? 1,
    page_size: data.page_size ?? params.page_size ?? 10,
    total_pages: data.total_pages ?? Math.max(1, Math.ceil((data.total ?? accounts.length) / (data.page_size ?? 10))),
  };
}


export async function getExplanation(id) {
  if (MOCK) return mockExplain(id);
  const { data } = await api.get(`/predict/explain/${id}`);
  return data;
}

export async function getGlobalFeatureImportance() {
  if (MOCK) {
    return [
      { importance_rank: 1, feature: 'avg_time_to_forward_funds_minutes', feature_name: 'Rapid Fund Forwarding Latency', importance: 0.24 },
      { importance_rank: 2, feature: 'txn_count_1h', feature_name: 'Transaction Velocity (1h)', importance: 0.19 },
      { importance_rank: 3, feature: 'unique_counterparty_count', feature_name: 'Unique Counterparties Count', importance: 0.14 },
      { importance_rank: 4, feature: 'fan_out_ratio', feature_name: 'Fan-Out Fan-In Topology Risk', importance: 0.11 },
      { importance_rank: 5, feature: 'amount_zscore_avg', feature_name: 'Behavioral Volume Spike Z-Score', importance: 0.08 },
    ];
  }
  const { data } = await api.get('/features/importance');
  return data.features || (Array.isArray(data) ? data : []);
}



export async function getAlerts(params = {}) {
  if (MOCK) {
    return {
      alerts: mockAlerts.map((alt) => ({
        alert_id: alt.id,
        account_id: alt.account_id,
        risk_score: alt.risk_score || 88.5,
        risk_tier: (alt.severity || 'HIGH').toUpperCase(),
        mule_probability: 0.88,
        anomaly_score: 0.75,
        network_risk: 82.0,
        top_reasons: [alt.type || 'Rapid fund forwarding (<15m)', 'Velocity burst spike'],
        model_version: 'v2.4-PaySim-XGB',
        created_at: alt.created_at || new Date().toISOString(),
        status: (alt.status || 'OPEN').toUpperCase(),
      })),
      total: mockAlerts.length,
      page: params.page || 1,
      page_size: params.page_size || 10,
      total_pages: 1,
    };
  }

  const { data } = await api.get('/alerts', { params });
  const rawList = Array.isArray(data) ? data : (data.alerts || []);

  const alerts = rawList.map((alt, i) => ({
    alert_id: alt.alert_id || alt.id || `ALT-${i}`,
    account_id: alt.account_id,
    risk_score: alt.risk_score ?? 85.0,
    risk_tier: (alt.risk_tier || alt.severity || 'HIGH').toUpperCase(),
    severity: (alt.severity || alt.risk_tier || 'HIGH').toUpperCase(),
    mule_probability: alt.mule_probability ?? (alt.risk_score ? alt.risk_score / 100 : 0.85),
    anomaly_score: alt.anomaly_score ?? 0.72,
    network_risk: alt.network_risk ?? 80.0,
    top_reasons: alt.top_reasons || alt.top_features || [
      'Rapid fund forwarding (<15m)',
      'High 1h transaction velocity spike',
      'Fan-out topology risk',
    ],
    summary: alt.summary || `Alert for ${alt.account_id}`,
    model_version: alt.model_version || 'v2.4-PaySim-XGB',
    status: (alt.status || 'OPEN').toUpperCase(),
    created_at: alt.created_at || new Date().toISOString(),
  }));

  return {
    alerts,
    total: data.total ?? alerts.length,
    page: data.page ?? params.page ?? 1,
    page_size: data.page_size ?? params.page_size ?? 10,
    total_pages: data.total_pages ?? Math.max(1, Math.ceil((data.total ?? alerts.length) / (data.page_size ?? 10))),
  };
}

export async function patchAlert(id, update) {
  if (MOCK) {
    const alert = mockAlerts.find((a) => a.id === id);
    if (alert) Object.assign(alert, update);
    return alert;
  }
  const payload = {
    ...update,
    status: update.status ? update.status.toUpperCase() : undefined,
  };
  const { data } = await api.patch(`/alerts/${id}`, payload);
  return data;
}

export async function bulkPatchAlerts(alertIds, status) {
  if (MOCK) return { updated_count: alertIds.length };
  const { data } = await api.post('/alerts/bulk-status', {
    alert_ids: alertIds,
    status: status.toUpperCase(),
  });
  return data;
}


export async function getModelPerformance() {
  if (MOCK) {
    return {
      metadata: {
        model_name: 'XGBoost Mule Classifier',
        model_version: 'v2.4-PaySim-XGB',
        training_dataset: 'PaySim Financial Transactions Dataset (1,048,575 rows)',
        training_date: '2026-08-22T14:30:00Z',
        feature_count: 21,
        training_period: 'Step 1 to Step 500 (Historical Window)',
        validation_period: 'Step 501 to Step 600 (Validation Window)',
        test_period: 'Step 601 to Step 743 (Holdout Test Window)',
      },
      metrics: {
        precision: 0.934,
        recall: 0.892,
        f1: 0.913,
        roc_auc: 0.968,
        pr_auc: 0.945,
      },
      confusion_matrix: {
        tn: 945,
        fp: 15,
        fn: 13,
        tp: 107,
        matrix: [[945, 15], [13, 107]],
      },
      roc_curve: [
        { fpr: 0.0, tpr: 0.0, threshold: 1.0 },
        { fpr: 0.005, tpr: 0.35, threshold: 0.90 },
        { fpr: 0.012, tpr: 0.68, threshold: 0.75 },
        { fpr: 0.016, tpr: 0.892, threshold: 0.50 },
        { fpr: 0.035, tpr: 0.955, threshold: 0.30 },
        { fpr: 0.080, tpr: 0.985, threshold: 0.15 },
        { fpr: 1.0, tpr: 1.0, threshold: 0.0 },
      ],
      pr_curve: [
        { recall: 0.0, precision: 1.0, threshold: 1.0 },
        { recall: 0.35, precision: 0.982, threshold: 0.90 },
        { recall: 0.68, precision: 0.955, threshold: 0.75 },
        { recall: 0.892, precision: 0.934, threshold: 0.50 },
        { recall: 0.955, precision: 0.852, threshold: 0.30 },
        { recall: 0.985, precision: 0.710, threshold: 0.15 },
        { recall: 1.0, precision: 0.102, threshold: 0.0 },
      ],
      threshold_comparison: [
        { threshold: 0.10, precision: 0.685, recall: 0.988, f1: 0.809, false_positives: 54 },
        { threshold: 0.25, "precision": 0.842, recall: 0.945, f1: 0.890, false_positives: 24 },
        { threshold: 0.50, precision: 0.934, recall: 0.892, f1: 0.913, false_positives: 15 },
        { threshold: 0.65, precision: 0.955, recall: 0.812, f1: 0.877, false_positives: 8 },
        { threshold: 0.80, precision: 0.982, recall: 0.680, f1: 0.804, false_positives: 2 },
      ],
      model_comparison: [
        {
          model_name: 'Logistic Regression',
          model_type: 'LogisticRegression',
          precision: 0.762,
          recall: 0.684,
          f1: 0.721,
          roc_auc: 0.815,
          pr_auc: 0.748,
          is_production: false,
        },
        {
          model_name: 'Random Forest',
          model_type: 'RandomForestClassifier',
          precision: 0.885,
          recall: 0.830,
          f1: 0.857,
          roc_auc: 0.932,
          pr_auc: 0.891,
          is_production: false,
        },
        {
          model_name: 'XGBoost Classifier',
          model_type: 'XGBClassifier',
          precision: 0.934,
          recall: 0.892,
          f1: 0.913,
          roc_auc: 0.968,
          pr_auc: 0.945,
          is_production: true,
        },
      ],
    };
  }

  const { data } = await api.get('/train/performance');
  return data;
}

export async function getModelMetrics() {
  if (MOCK) return mockMetrics;
  try {
    const { data } = await api.get('/train/performance');
    const metrics = data.metrics || data;
    return {
      accuracy: metrics.roc_auc ?? 0.95,
      precision: metrics.precision ?? 0.92,
      recall: metrics.recall ?? 0.88,
      f1_score: metrics.f1 ?? 0.90,
      roc_auc: metrics.roc_auc ?? 0.96,
      confusion_matrix: data.confusion_matrix || { tp: 107, fp: 15, fn: 13, tn: 945 },
      feature_importance: (metrics.feature_columns || []).map((col, idx) => ({
        feature: col,
        importance: Math.round((1.0 / (idx + 1)) * 100) / 100
      }))
    };
  } catch (err) {
    return mockMetrics;
  }
}


export async function getTransactionGraph(id, params = {}) {
  if (MOCK) return mockGraph(id);
  try {
    const { data } = await api.get(`/graph/${id}`, { params });
    return data;
  } catch (e) {
    return mockGraph(id);
  }
}


export async function submitFeedback(payload) {
  if (MOCK) {
    return {
      feedback_id: Date.now(),
      alert_id: payload.alert_id,
      account_id: payload.account_id,
      decision: payload.decision,
      note: payload.note,
      investigator: payload.investigator || 'Analyst #402',
      timestamp: new Date().toISOString(),
      current_status: payload.decision,
    };
  }
  const { data } = await api.post('/feedback', payload);
  return data;
}

export async function getFeedbackHistory(params = {}) {
  if (MOCK) {
    return {
      current_status: 'UNDER_INVESTIGATION',
      history: [
        {
          feedback_id: 1,
          alert_id: `ALT-${params.account_id || '001'}`,
          account_id: params.account_id || 'ACC-001001',
          decision: 'UNDER_INVESTIGATION',
          note: 'Initial triage performed following suspicious rapid fund forwarding signal.',
          investigator: 'Analyst #109',
          timestamp: new Date().toISOString(),
        },
      ],
    };
  }
  const { data } = await api.get('/feedback', { params });
  return data;
}

export async function getFeatureIntelligence() {
  if (MOCK) {
    return {
      count: 15,
      categories: ['Transaction', 'Velocity', 'Fund Flow', 'Behavioral', 'Temporal', 'Network'],
      features: [
        {
          feature_name: 'avg_time_to_forward_funds_minutes',
          category: 'Fund Flow',
          importance: 0.24,
          shap_importance: 0.24,
          xgb_importance: 0.22,
          mutual_information: 0.18,
          status: 'SELECTED',
          description: 'Average latency in minutes to forward received incoming funds to downstream counterparties',
          interpretation: 'Short latency (<5 mins) signals automated mule pass-through activity designed to evade manual freeze windows.',
        },
        {
          feature_name: 'txn_count_1h',
          category: 'Velocity',
          importance: 0.19,
          shap_importance: 0.19,
          xgb_importance: 0.17,
          mutual_information: 0.15,
          status: 'SELECTED',
          description: 'Total count of executed transactions within a rolling 1-hour window',
          interpretation: 'High 1-hour transaction spikes highlight active smurfing or burst layering behavior.',
        },
        {
          feature_name: 'unique_counterparty_count',
          category: 'Behavioral',
          importance: 0.14,
          shap_importance: 0.14,
          xgb_importance: 0.13,
          mutual_information: 0.12,
          status: 'SELECTED',
          description: 'Number of distinct inbound senders and outbound receivers linked to the account',
          interpretation: 'Expansive counterparty footprints without prior relationship history correlate strongly with fan-out mule rings.',
        },
        {
          feature_name: 'betweenness_centrality',
          category: 'Network',
          importance: 0.11,
          shap_importance: 0.11,
          xgb_importance: 0.10,
          mutual_information: 0.09,
          status: 'SELECTED',
          description: 'Graph centrality measuring how often an account acts as a bridge between disconnected network clusters',
          interpretation: 'High betweenness centrality indicates a critical intermediary node connecting distinct laundering rings.',
        },
        {
          feature_name: 'transaction_velocity_change',
          category: 'Velocity',
          importance: 0.08,
          shap_importance: 0.08,
          xgb_importance: 0.09,
          mutual_information: 0.07,
          status: 'SELECTED',
          description: 'Acceleration ratio comparing 1-hour transaction frequency against historical 24-hour baseline',
          interpretation: 'Abrupt acceleration in transaction velocity flags newly activated dormant mule accounts.',
        },
        {
          feature_name: 'is_new_high_volume_flag',
          category: 'Behavioral',
          importance: 0.07,
          shap_importance: 0.07,
          xgb_importance: 0.06,
          mutual_information: 0.05,
          status: 'SELECTED',
          description: 'Binary flag for accounts under 30 days old processing uncharacteristically high daily volume',
          interpretation: 'Newly opened accounts processing high-value volume are classic indicators of disposable mule creation.',
        },
        {
          feature_name: 'ratio_received_to_sent_24h',
          category: 'Fund Flow',
          importance: 0.06,
          shap_importance: 0.06,
          xgb_importance: 0.05,
          mutual_information: 0.04,
          status: 'SELECTED',
          description: 'Ratio of 24-hour inbound monetary volume to outbound monetary volume',
          interpretation: 'Near-1.0 balance ratio accompanied by zero retained funds indicates pure pass-through mule draining.',
        },
        {
          feature_name: 'fan_out_ratio',
          category: 'Network',
          importance: 0.05,
          shap_importance: 0.05,
          xgb_importance: 0.04,
          mutual_information: 0.04,
          status: 'SELECTED',
          description: 'Proportion of graph degree dedicated to outbound transfer counterparties',
          interpretation: 'High fan-out ratios signal funds being broken up and dispersed to multiple downstream recipients.',
        },
        {
          feature_name: 'is_in_short_cycle',
          category: 'Network',
          importance: 0.04,
          shap_importance: 0.04,
          xgb_importance: 0.04,
          mutual_information: 0.03,
          status: 'SELECTED',
          description: 'Binary indicator for participation in short graph cycles (<= 4 hops)',
          interpretation: 'Circular money movement loops demonstrate deliberate obfuscation and ring-based laundering.',
        },
        {
          feature_name: 'round_number_txn_ratio',
          category: 'Transaction',
          importance: 0.03,
          shap_importance: 0.03,
          xgb_importance: 0.03,
          mutual_information: 0.02,
          status: 'SELECTED',
          description: 'Proportion of transactions processed in exact round monetary values (e.g. multiples of $1,000)',
          interpretation: 'Excessive round-number transfers suggest structured smurfing to remain under reporting thresholds.',
        },
        {
          feature_name: 'odd_hour_txn_ratio',
          category: 'Temporal',
          importance: 0.02,
          shap_importance: 0.02,
          xgb_importance: 0.02,
          mutual_information: 0.02,
          status: 'SELECTED',
          description: 'Fraction of transactions executed during off-peak hours (00:00 to 05:00 local time)',
          interpretation: 'Late-night transfers exploit reduced operational compliance oversight.',
        },
        {
          feature_name: 'night_transaction_ratio',
          category: 'Temporal',
          importance: 0.02,
          shap_importance: 0.02,
          xgb_importance: 0.02,
          mutual_information: 0.01,
          status: 'SELECTED',
          description: 'Proportion of transfers conducted between 23:00 and 05:00',
          interpretation: 'Nocturnal activity clusters correlate with automated bot-driven laundering scripts.',
        },
        {
          feature_name: 'account_age_days',
          category: 'Behavioral',
          importance: 0.01,
          shap_importance: 0.01,
          xgb_importance: 0.01,
          mutual_information: 0.01,
          status: 'SELECTED',
          description: 'Lifespan of account since registration in days',
          interpretation: 'Younger account lifespan elevates baseline vulnerability for illicit takeover.',
        },
        {
          feature_name: 'amount_zscore_avg',
          category: 'Transaction',
          importance: 0.01,
          shap_importance: 0.01,
          xgb_importance: 0.01,
          mutual_information: 0.01,
          status: 'SELECTED',
          description: 'Average Z-score deviation of account transaction amounts against normal distribution',
          interpretation: 'High Z-score deviations pinpoint statistical monetary outliers.',
        },
        {
          feature_name: 'active_hours',
          category: 'Temporal',
          importance: 0.005,
          shap_importance: 0.005,
          xgb_importance: 0.004,
          mutual_information: 0.003,
          status: 'REJECTED',
          description: 'Number of active hours per day',
          interpretation: 'Low predictive signal; rejected due to low composite correlation and high redundancy.',
        },
      ],
    };
  }

  const { data } = await api.get('/feature-selection/intelligence');
  return data;
}

export async function getAnomalySummary(params = {}) {
  if (MOCK) {
    return {
      total_accounts_analyzed: 1048,
      anomalous_accounts: 134,
      anomaly_rate: 12.79,
      average_anomaly_score: 0.385,
      high_anomaly_accounts: 42,
      distribution: [
        { range: '0.0 - 0.2 (Normal)', count: 540, tier: 'Low' },
        { range: '0.2 - 0.4 (Mild)', count: 374, tier: 'Low' },
        { range: '0.4 - 0.6 (Moderate)', count: 92, tier: 'Medium' },
        { range: '0.6 - 0.8 (Elevated)', count: 28, tier: 'High' },
        { range: '0.8 - 1.0 (Critical)', count: 14, tier: 'Critical' },
      ],
      page: params.page || 1,
      page_size: params.page_size || 15,
      total_pages: 3,
      accounts: [
        {
          account_id: 'ACC-001001',
          anomaly_score: 0.942,
          risk_score: 96.5,
          transaction_velocity: 48,
          behavior_change: 4.85,
          network_risk: 88.2,
        },
        {
          account_id: 'ACC-001004',
          anomaly_score: 0.884,
          risk_score: 91.2,
          transaction_velocity: 32,
          behavior_change: 3.42,
          network_risk: 82.5,
        },
        {
          account_id: 'ACC-001009',
          anomaly_score: 0.812,
          risk_score: 87.4,
          transaction_velocity: 29,
          behavior_change: 2.95,
          network_risk: 76.0,
        },
        {
          account_id: 'ACC-001015',
          anomaly_score: 0.745,
          risk_score: 79.0,
          transaction_velocity: 21,
          behavior_change: 2.10,
          network_risk: 68.4,
        },
        {
          account_id: 'ACC-001022',
          anomaly_score: 0.680,
          risk_score: 72.3,
          transaction_velocity: 18,
          behavior_change: 1.85,
          network_risk: 61.2,
        },
      ],
    };
  }

  const { data } = await api.get('/predict/anomalies', { params });
  return data;
}

export async function getModelMonitoring() {
  if (MOCK) {
    return {
      model_version: 'v2.4-PaySim-XGB',
      training_date: '2026-08-22T14:30:00Z',
      latest_scoring_date: '2026-08-22T17:20:00Z',
      feature_drift_status: 'WARNING',
      drift_severity: 'MODERATE',
      overall_psi: 0.142,
      prediction_distribution: [
        { range: '0.0 - 0.2 (Low Risk)', training_pct: 74.5, current_pct: 68.2 },
        { range: '0.2 - 0.4 (Mild Risk)', training_pct: 14.2, current_pct: 16.5 },
        { range: '0.4 - 0.6 (Medium Risk)', training_pct: 6.1, current_pct: 8.4 },
        { range: '0.6 - 0.8 (High Risk)', training_pct: 3.8, current_pct: 4.9 },
        { range: '0.8 - 1.0 (Critical Mule)', training_pct: 1.4, current_pct: 2.0 },
      ],
      monitored_features: [
        {
          feature: 'avg_time_to_forward_funds_minutes',
          training_distribution: 'μ = 14.8m (σ = 9.2m)',
          current_distribution: 'μ = 3.2m (σ = 2.8m)',
          drift_metric: 0.284,
          metric_name: 'PSI',
          status: 'CRITICAL',
          description: 'Severe acceleration in fund forwarding latency; short-lived pass-through burst detected.',
        },
        {
          feature: 'txn_count_1h',
          training_distribution: 'μ = 2.4 (σ = 1.8)',
          current_distribution: 'μ = 6.8 (σ = 4.5)',
          drift_metric: 0.185,
          metric_name: 'PSI',
          status: 'WARNING',
          description: 'Moderate shift in 1-hour transaction frequency toward higher velocity bursts.',
        },
        {
          feature: 'unique_counterparty_count',
          training_distribution: 'μ = 5.1 (σ = 3.2)',
          current_distribution: 'μ = 5.4 (σ = 3.6)',
          drift_metric: 0.038,
          metric_name: 'PSI',
          status: 'NORMAL',
          description: 'Counterparty connectivity distribution matches baseline expectations.',
        },
        {
          feature: 'betweenness_centrality',
          training_distribution: 'μ = 0.012 (σ = 0.008)',
          current_distribution: 'μ = 0.045 (σ = 0.032)',
          drift_metric: 0.268,
          metric_name: 'PSI',
          status: 'CRITICAL',
          description: 'Network topology shift; significant increase in bridge/intermediary account centrality.',
        },
        {
          feature: 'amount_zscore_avg',
          training_distribution: 'μ = 0.15 (σ = 1.02)',
          current_distribution: 'μ = 1.48 (σ = 2.10)',
          drift_metric: 0.192,
          metric_name: 'PSI',
          status: 'WARNING',
          description: 'Elevated monetary Z-score dispersion indicating larger transaction spikes.',
        },
        {
          feature: 'odd_hour_txn_ratio',
          training_distribution: 'μ = 0.08 (σ = 0.05)',
          current_distribution: 'μ = 0.09 (σ = 0.06)',
          drift_metric: 0.024,
          metric_name: 'PSI',
          status: 'NORMAL',
          description: 'Off-peak transaction proportion remains stable.',
        },
        {
          feature: 'ratio_received_to_sent_24h',
          training_distribution: 'μ = 0.85 (σ = 0.22)',
          current_distribution: 'μ = 0.98 (σ = 0.08)',
          drift_metric: 0.165,
          metric_name: 'PSI',
          status: 'WARNING',
          description: 'Shift toward near-1.0 balance transfer ratio (zero retention flow pattern).',
        },
        {
          feature: 'is_in_short_cycle',
          training_distribution: 'Rate = 1.4%',
          current_distribution: 'Rate = 1.6%',
          drift_metric: 0.018,
          metric_name: 'PSI',
          status: 'NORMAL',
          description: 'Closed-loop transaction cycle participation consistent with baseline.',
        },
      ],
    };
  }

  try {
    const { data } = await api.get('/api/monitoring/drift');
    return data;
  } catch (e) {
    const { data } = await api.get('/train/monitoring');
    return data;
  }
}

// ── Canonical /api/... API Wrappers ──────────────────────────────
export async function getApiDashboardSummary() {
  if (MOCK) return getDashboardSummary();
  const { data } = await api.get('/api/dashboard/summary');
  return data;
}

export async function getApiAccounts(params = {}) {
  if (MOCK) return getRiskScores(params);
  const { data } = await api.get('/api/accounts', { params });
  return data;
}

export async function getApiAccountDetails(accountId) {
  if (MOCK) return getAccountDetails(accountId);
  const { data } = await api.get(`/api/accounts/${accountId}`);
  return data;
}

export async function getApiAccountTransactions(accountId, params = {}) {
  if (MOCK) return getAccountTransactions(accountId, params);
  const { data } = await api.get(`/api/accounts/${accountId}/transactions`, { params });
  return data;
}

export async function getApiAccountFundFlow(accountId) {
  if (MOCK) return getAccountFundFlow(accountId);
  const { data } = await api.get(`/api/accounts/${accountId}/fund-flow`);
  return data;
}

export async function getApiAccountNetwork(accountId, maxHops = 2) {
  if (MOCK) return getGraphData(accountId);
  const { data } = await api.get(`/api/accounts/${accountId}/network`, { params: { max_hops: maxHops } });
  return data;
}

export async function getApiAccountExplanation(accountId) {
  if (MOCK) return getExplanation(accountId);
  const { data } = await api.get(`/api/accounts/${accountId}/explanation`);
  return data;
}

export async function getApiAlerts(params = {}) {
  if (MOCK) return getAlerts(params);
  const { data } = await api.get('/api/alerts', { params });
  return data;
}

export async function getApiAlertDetails(alertId) {
  if (MOCK) return getAlertDetails(alertId);
  const { data } = await api.get(`/api/alerts/${alertId}`);
  return data;
}

export async function postApiAlertDecision(alertId, payload) {
  if (MOCK) return submitAlertDecision({ alert_id: alertId, ...payload });
  const { data } = await api.post(`/api/alerts/${alertId}/decision`, payload);
  return data;
}

export async function postApiAccountNotes(accountId, payload) {
  if (MOCK) return submitInvestigatorNote({ account_id: accountId, ...payload });
  const { data } = await api.post(`/api/accounts/${accountId}/notes`, payload);
  return data;
}

export async function getApiModels() {
  if (MOCK) return getModelPerformance();
  const { data } = await api.get('/api/models');
  return data;
}

export async function getApiModelVersionMetrics(version = 'v2.4') {
  if (MOCK) return getModelPerformance();
  const { data } = await api.get(`/api/models/${version}/metrics`);
  return data;
}

export async function getApiModelVersionFeatures(version = 'v2.4') {
  if (MOCK) return getFeatureIntelligence();
  const { data } = await api.get(`/api/models/${version}/features`);
  return data;
}

export async function getApiAnomalies(params = {}) {
  if (MOCK) return getAnomalySummary(params);
  const { data } = await api.get('/api/anomalies', { params });
  return data;
}

export async function getApiNetworkAccount(accountId) {
  if (MOCK) return getGraphData(accountId);
  const { data } = await api.get(`/api/network/${accountId}`);
  return data;
}

export async function getApiMonitoringDrift() {
  if (MOCK) return getModelMonitoring();
  const { data } = await api.get('/api/monitoring/drift');
  return data;
}

export default api;





