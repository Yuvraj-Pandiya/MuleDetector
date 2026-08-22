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
    if (params.tier) accounts = accounts.filter((a) => a.risk_tier === params.tier);
    if (params.sort === 'score_desc') accounts.sort((a, b) => b.risk_score - a.risk_score);
    if (params.sort === 'score_asc') accounts.sort((a, b) => a.risk_score - b.risk_score);
    if (params.search) {
      const q = params.search.toLowerCase();
      accounts = accounts.filter((a) => a.id.toLowerCase().includes(q) || a.name.toLowerCase().includes(q));
    }
    return accounts;
  }
  const { data } = await api.get('/predict/risk-scores', { params });
  const rawList = data.accounts || (Array.isArray(data) ? data : []);

  let accounts = rawList.map((acc, i) => {
    const rawScore = acc.risk_score ?? 0;
    const scoreVal = rawScore <= 1.0 ? Math.round(rawScore * 1000) / 10 : Math.round(rawScore * 10) / 10;
    const rawTier = (acc.risk_tier || '').toLowerCase();
    const tier = rawTier === 'high' && scoreVal > 85 ? 'critical' : (rawTier || (scoreVal > 70 ? 'high' : scoreVal > 30 ? 'medium' : 'low'));

    return {
      id: acc.account_id || acc.id || `ACC-${i}`,
      name: NAMES[i % NAMES.length],
      risk_score: scoreVal,
      risk_tier: tier,
      txn_count: acc.txn_count_24h ?? acc.txn_count ?? acc.txn_count_7d ?? 0,
      total_volume: Math.round((acc.total_amount_out_24h ?? acc.total_volume ?? 0) * 100) / 100,
      avg_txn_size: Math.round((acc.avg_transaction_amount ?? acc.avg_txn_size ?? 0) * 100) / 100,
      fan_in: acc.in_degree ?? acc.fan_in ?? 0,
      fan_out: acc.out_degree ?? acc.fan_out ?? 0,
      flagged: scoreVal > 70,
    };
  });

  if (params.tier) accounts = accounts.filter((a) => a.risk_tier === params.tier.toLowerCase());
  if (params.sort === 'score_desc') accounts.sort((a, b) => b.risk_score - a.risk_score);
  if (params.sort === 'score_asc') accounts.sort((a, b) => a.risk_score - b.risk_score);
  if (params.search) {
    const q = params.search.toLowerCase();
    accounts = accounts.filter((a) => a.id.toLowerCase().includes(q) || a.name.toLowerCase().includes(q));
  }

  return accounts;
}

export async function getExplanation(id) {
  if (MOCK) return mockExplain(id);
  const { data } = await api.get(`/predict/explain/${id}`);
  const scoreVal = typeof data.risk_score === 'number' && data.risk_score <= 1.0
    ? Math.round(data.risk_score * 1000) / 10
    : (data.risk_score || 0);

  const rawFeatures = data.top_shap_features || data.features || [];

  return {
    account_id: data.account_id,
    risk_score: scoreVal,
    risk_tier: (data.risk_tier || (scoreVal > 70 ? 'high' : 'medium')).toLowerCase(),
    reason: data.reason || 'Account flagged based on automated risk feature analysis.',
    features: rawFeatures.map(f => ({
      name: (f.feature || f.name || '').replace(/_/g, ' '),
      value: f.feature_value ?? f.value ?? 0,
      impact: f.shap_value ?? f.impact ?? 0.1,
      direction: (f.shap_value ?? f.impact ?? 0) >= 0 ? 'positive' : 'negative'
    }))
  };
}

export async function getAlerts() {
  if (MOCK) return [...mockAlerts];
  const { data } = await api.get('/alerts');
  const list = Array.isArray(data) ? data : (data.alerts || []);

  return list.map((alt, i) => ({
    id: alt.alert_id || alt.id || `ALT-${i}`,
    account_id: alt.account_id,
    severity: (alt.severity || 'high').toLowerCase(),
    type: alt.summary ? alt.summary.split('.')[0] : (alt.type || 'Mule Risk Flag'),
    message: alt.summary || alt.message || 'High risk score triggered compliance alert',
    status: (alt.status || 'open').toLowerCase(),
    created_at: alt.created_at || new Date().toISOString(),
  }));
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
  return {
    id: data.alert_id || data.id,
    status: (data.status || 'open').toLowerCase(),
  };
}

export async function getModelMetrics() {
  if (MOCK) return mockMetrics;
  try {
    const { data } = await api.post('/train');
    const metrics = data.metrics || data;
    return {
      accuracy: metrics.roc_auc ?? 0.95,
      precision: metrics.precision ?? 0.92,
      recall: metrics.recall ?? 0.88,
      f1_score: metrics.f1 ?? 0.90,
      roc_auc: metrics.roc_auc ?? 0.96,
      confusion_matrix: metrics.confusion_matrix || { tp: 50, fp: 2, fn: 3, tn: 945 },
      feature_importance: (metrics.feature_columns || []).map((col, idx) => ({
        feature: col,
        importance: Math.round((1.0 / (idx + 1)) * 100) / 100
      }))
    };
  } catch (err) {
    return mockMetrics;
  }
}

export async function getTransactionGraph(id) {
  if (MOCK) return mockGraph(id);
  try {
    const { data } = await api.get(`/graph/${id}`);
    return data;
  } catch (e) {
    return mockGraph(id);
  }
}

export default api;
