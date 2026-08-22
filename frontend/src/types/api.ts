/**
 * Centralized API Contract Layer & TypeScript Interfaces
 * MuleDetector Platform — Sync with Backend (PaySim & Canonical Schemas)
 */

// 1. Transaction Schema (PaySim & Canonical Mappings)
export interface Transaction {
  transaction_id: string;
  sender_account_id: string;
  receiver_account_id: string;
  amount: number;
  timestamp: string; // ISO 8601 string or datetime
  transaction_type: 'TRANSFER' | 'CASH_OUT' | 'PAYMENT' | 'DEBIT' | 'CASH_IN' | string;
  is_mule_pattern: number; // 0 = legit, 1 = mule/fraud
  step?: number; // PaySim 1-hour step
  oldbalanceOrg?: number;
  newbalanceOrig?: number;
  oldbalanceDest?: number;
  newbalanceDest?: number;
}

// 2. Account Summary Entity
export interface Account {
  id: string;
  name?: string;
  risk_score: number; // Normalized 0-100 or 0.0-1.0
  risk_tier: 'critical' | 'high' | 'medium' | 'low';
  txn_count: number;
  total_volume: number;
  avg_txn_size: number;
  fan_in: number;
  fan_out: number;
  flagged: boolean;
  last_activity?: string;
}

// 3. Account Risk Overview
export interface AccountRisk {
  account_id: string;
  risk_score: number;
  risk_tier: 'Critical' | 'High' | 'Medium' | 'Low' | string;
  top_features: string[];
  reasons?: string[];
  scored_at?: string;
}

// 4. Risk Score DTO (from GET /predict/risk-scores)
export interface RiskScore {
  account_id: string;
  risk_score: number; // 0.0 to 1.0
  risk_tier: string;
  top_features: string[];
  txn_count_24h?: number;
  total_amount_out_24h?: number;
  avg_transaction_amount?: number;
  in_degree?: number;
  out_degree?: number;
}

// 5. Anomaly Score DTO
export interface AnomalyScore {
  account_id: string;
  anomaly_score: number;
  is_anomaly: boolean;
  amount_zscore_avg: number;
  odd_hour_txn_ratio: number;
  round_number_txn_ratio: number;
  algorithm: 'IsolationForest' | 'ZScore' | string;
}

// 6. Network Risk & Topology (from GET /graph/{account_id})
export interface NetworkNode {
  id: string;
  label: string;
  group: 'target' | 'flagged' | 'normal' | 'external' | string;
  risk: number;
}

export interface NetworkLink {
  source: string;
  target: string;
  value: number;
  type: 'inflow' | 'outflow' | 'cycle' | string;
}

export interface NetworkRisk {
  nodes: NetworkNode[];
  links: NetworkLink[];
  centrality?: {
    betweenness_centrality: number;
    fan_in_ratio: number;
    fan_out_ratio: number;
    is_in_short_cycle: number;
  };
}

// 7. Feature Matrix Record (from GET /features, matching docs/feature_schema.md)
export interface Feature {
  account_id: string;
  txn_count_1h: number;
  txn_count_24h: number;
  txn_count_7d: number;
  total_amount_out_24h: number;
  total_amount_in_24h: number;
  avg_transaction_amount: number;
  max_transaction_amount: number;
  ratio_received_to_sent_24h: number;
  avg_time_to_forward_funds_minutes: number;
  unique_counterparty_count: number;
  account_age_days: number;
  is_new_high_volume_flag: number;
  in_degree: number;
  out_degree: number;
  is_in_short_cycle: number;
  betweenness_centrality: number;
  fan_in_ratio: number;
  fan_out_ratio: number;
  amount_zscore_avg: number;
  round_number_txn_ratio: number;
  odd_hour_txn_ratio: number;
  is_mule_pattern?: number;
}

// 8. Feature Importance
export interface FeatureImportance {
  feature: string;
  importance: number;
  description?: string;
}

// 9. SHAP Explanation DTO (from GET /predict/explain/{account_id})
export interface ShapFeatureImpact {
  feature: string;
  shap_value: number;
  feature_value: number;
}

export interface ShapExplanation {
  account_id: string;
  risk_score: number;
  risk_tier: string;
  shap_available: boolean;
  top_shap_features: ShapFeatureImpact[];
  reason: string;
}

// 10. Alert DTO (from GET /alerts, POST /alerts/generate, PATCH /alerts/{alert_id})
export interface Alert {
  alert_id: string;
  account_id: string;
  risk_score: number;
  severity: 'High' | 'Critical' | string;
  summary: string;
  status: 'OPEN' | 'REVIEWED' | 'DISMISSED';
  created_at: string;
  updated_at?: string;
}

// 11. Investigator Decision DTO
export interface InvestigatorDecision {
  alert_id: string;
  account_id: string;
  decision: 'OPEN' | 'REVIEWED' | 'DISMISSED';
  investigator_id?: string;
  notes?: string;
  timestamp: string;
}

// 12. Investigation Note Entry
export interface InvestigationNote {
  id: string;
  account_id: string;
  alert_id?: string;
  author: string;
  note: string;
  created_at: string;
}

// 13. Model Metrics DTO (from POST /train or GET /metrics)
export interface ConfusionMatrix {
  tp: number;
  fp: number;
  fn: number;
  tn: number;
}

export interface ModelMetrics {
  model_type: 'XGBClassifier' | 'IsolationForest' | string;
  roc_auc: number;
  precision: number;
  recall: number;
  f1: number;
  unsupervised?: boolean;
  confusion_matrix: ConfusionMatrix;
  feature_columns?: string[];
  feature_importance?: FeatureImportance[];
}

// 14. Model Version Metadata
export interface ModelVersion {
  version_id: string;
  model_type: string;
  trained_at: string;
  dataset_source: string;
  metrics: ModelMetrics;
  artifact_path: string;
}

// 15. Drift Status & Schema Validation (from GET /features)
export interface DriftStatus {
  schema_ok: boolean;
  missing_keys: string[];
  extra_keys: string[];
  null_cols?: Record<string, number>;
  account_count: number;
  column_count: number;
}
