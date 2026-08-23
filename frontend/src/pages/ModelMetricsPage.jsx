import React, { useState, useEffect } from 'react';
import {
  BarChart3, Award, Target, Activity, ShieldCheck,
  CheckCircle2, AlertTriangle, Layers, Database, Calendar,
  Sliders, Cpu, Sparkles, RefreshCw, LineChart as LineChartIcon, Check, ArrowRight
} from 'lucide-react';
import {
  BarChart, Bar, LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer, Cell, Legend
} from 'recharts';
import { getModelPerformance } from '../api/client';
import './ModelMetricsPage.css';

export default function ModelMetricsPage() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);

  const loadPerformanceData = async () => {
    setLoading(true);
    try {
      const res = await getModelPerformance();
      setData(res);
    } catch (err) {
      console.error('Failed to load model performance evaluation:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadPerformanceData();
    const handleDatasetChange = () => {
      loadPerformanceData();
    };
    window.addEventListener('dataset-changed', handleDatasetChange);
    return () => window.removeEventListener('dataset-changed', handleDatasetChange);
  }, []);

  if (loading || !data) {
    return (
      <div className="metrics-page animate-fade-in">
        <div className="loading-state">Fetching backend model evaluation telemetry...</div>
      </div>
    );
  }

  const { metadata, metrics, confusion_matrix, roc_curve, pr_curve, threshold_comparison, model_comparison } = data;

  const kpis = [
    { label: 'Precision', val: `${(metrics.precision * 100).toFixed(1)}%`, sub: 'Low false positive alarm rate', icon: Target },
    { label: 'Recall (Sensitivity)', val: `${(metrics.recall * 100).toFixed(1)}%`, sub: 'Mule ring detection coverage', icon: Activity },
    { label: 'F1 Score', val: `${(metrics.f1 * 100).toFixed(1)}%`, sub: 'Harmonic mean precision & recall', icon: ShieldCheck },
    { label: 'ROC-AUC', val: metrics.roc_auc.toFixed(3), sub: 'Discrimination separability index', icon: BarChart3 },
    { label: 'PR-AUC', val: metrics.pr_auc.toFixed(3), sub: 'Precision-Recall area under curve', icon: Award },
  ];

  return (
    <div className="metrics-page animate-fade-in">
      {/* Page Header */}
      <div className="page-head flex-between">
        <div>
          <h2>Model Performance & Evaluation Intelligence</h2>
          <p>Backend-derived quantitative evaluation metrics for the production Mule Detection model.</p>
        </div>

        <button className="btn-secondary flex-align gap-xs" onClick={loadPerformanceData}>
          <RefreshCw size={14} /> Refresh Evaluation Data
        </button>
      </div>

      {/* 1. Model Metadata Panel */}
      <div className="section-card margin-top-xs">
        <div className="section-title flex-align gap-xs">
          <Cpu size={18} className="title-icon text-teal" />
          <div>
            <h3>Production Model Specifications & Training Context</h3>
            <span>Backend model metadata, features, and evaluation split windows</span>
          </div>
        </div>

        <div className="meta-grid margin-top-xs">
          <div className="meta-item">
            <span className="meta-label">Model Name</span>
            <span className="meta-val font-semibold text-ink">{metadata.model_name}</span>
          </div>

          <div className="meta-item">
            <span className="meta-label">Model Version</span>
            <span className="meta-val font-mono text-teal font-semibold">{metadata.model_version}</span>
          </div>

          <div className="meta-item">
            <span className="meta-label">Training Dataset</span>
            <span className="meta-val font-mono text-stone">{metadata.training_dataset}</span>
          </div>

          <div className="meta-item">
            <span className="meta-label">Feature Schema Count</span>
            <span className="meta-val font-mono text-ink font-bold">{metadata.feature_count} features</span>
          </div>

          <div className="meta-item">
            <span className="meta-label">Training Date</span>
            <span className="meta-val font-mono text-stone">{new Date(metadata.training_date).toLocaleString()}</span>
          </div>

          <div className="meta-item">
            <span className="meta-label">Training Period</span>
            <span className="meta-val text-stone">{metadata.training_period}</span>
          </div>

          <div className="meta-item">
            <span className="meta-label">Validation Period</span>
            <span className="meta-val text-stone">{metadata.validation_period}</span>
          </div>

          <div className="meta-item">
            <span className="meta-label">Holdout Test Period</span>
            <span className="meta-val text-stone">{metadata.test_period}</span>
          </div>
        </div>
      </div>

      {/* 2. Top-Level Metric KPI Cards */}
      <div className="metrics-kpi-grid margin-top-xs">
        {kpis.map((k, i) => {
          const Icon = k.icon;
          return (
            <div key={i} className="dash-card metric-kpi-card">
              <div className="kpi-inner">
                <div className="kpi-head-sm">
                  <span className="label">{k.label}</span>
                  <Icon size={16} className="text-teal" />
                </div>
                <span className="val">{k.val}</span>
                <span className="sub">{k.sub}</span>
              </div>
            </div>
          );
        })}
      </div>

      {/* 3. Confusion Matrix & Curves Grid */}
      <div className="metrics-grid-main margin-top-xs">
        {/* Left: Confusion Matrix */}
        <div className="matrix-card">
          <div className="card-head">
            <div>
              <h3>Confusion Matrix</h3>
              <p className="card-sub">Holdout test set evaluations</p>
            </div>
          </div>

          <div className="matrix-2x2">
            <div className="matrix-cell tp">
              <span className="cell-title">True Positives (TP)</span>
              <span className="cell-num">{confusion_matrix.tp}</span>
              <span className="cell-desc">Correctly flagged mule accounts</span>
            </div>

            <div className="matrix-cell fp">
              <span className="cell-title">False Positives (FP)</span>
              <span className="cell-num">{confusion_matrix.fp}</span>
              <span className="cell-desc">False alarms (legitimate flagged)</span>
            </div>

            <div className="matrix-cell fn">
              <span className="cell-title">False Negatives (FN)</span>
              <span className="cell-num">{confusion_matrix.fn}</span>
              <span className="cell-desc">Missed mule accounts</span>
            </div>

            <div className="matrix-cell tn">
              <span className="cell-title">True Negatives (TN)</span>
              <span className="cell-num">{confusion_matrix.tn}</span>
              <span className="cell-desc">Correctly identified legitimate</span>
            </div>
          </div>

          <div className="matrix-stats-footer margin-top-xs">
            <div className="m-stat">
              <span>False Positive Rate:</span>
              <span className="font-mono text-ink font-semibold">
                {((confusion_matrix.fp / Math.max(1, confusion_matrix.fp + confusion_matrix.tn)) * 100).toFixed(2)}%
              </span>
            </div>
            <div className="m-stat">
              <span>Detection Hit Rate:</span>
              <span className="font-mono text-ink font-semibold">
                {((confusion_matrix.tp / Math.max(1, confusion_matrix.tp + confusion_matrix.fn)) * 100).toFixed(2)}%
              </span>
            </div>
          </div>
        </div>

        {/* Right: ROC Curve */}
        <div className="section-card">
          <div className="card-head flex-between">
            <div>
              <h3>ROC Curve (Receiver Operating Characteristic)</h3>
              <p className="card-sub">False Positive Rate vs. True Positive Rate (AUC = {metrics.roc_auc.toFixed(3)})</p>
            </div>
          </div>

          <ResponsiveContainer width="100%" height={260}>
            <LineChart data={roc_curve} margin={{ top: 10, right: 30, left: 10, bottom: 10 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#242728" />
              <XAxis dataKey="fpr" type="number" domain={[0, 1]} stroke="#6a6b6c" fontSize={11} name="FPR" />
              <YAxis dataKey="tpr" type="number" domain={[0, 1]} stroke="#6a6b6c" fontSize={11} name="TPR" />
              <Tooltip contentStyle={{ background: '#0d0d0d', borderColor: 'rgba(255,255,255,0.16)', borderRadius: 8, color: '#f4f4f6', fontSize: 12 }} />
              <Line type="monotone" dataKey="tpr" stroke="#14b8a6" strokeWidth={2} dot={{ r: 4 }} name="TPR (Recall)" />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* 4. Precision-Recall Curve & Threshold Comparison Grid */}
      <div className="metrics-grid-main margin-top-xs">
        {/* Left: Precision-Recall Curve */}
        <div className="section-card">
          <div className="card-head">
            <div>
              <h3>Precision-Recall Curve</h3>
              <p className="card-sub">Recall vs Precision tradeoff under class imbalance (PR-AUC = {metrics.pr_auc.toFixed(3)})</p>
            </div>
          </div>

          <ResponsiveContainer width="100%" height={250}>
            <LineChart data={pr_curve} margin={{ top: 10, right: 30, left: 10, bottom: 10 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#242728" />
              <XAxis dataKey="recall" type="number" domain={[0, 1]} stroke="#6a6b6c" fontSize={11} name="Recall" />
              <YAxis dataKey="precision" type="number" domain={[0, 1]} stroke="#6a6b6c" fontSize={11} name="Precision" />
              <Tooltip contentStyle={{ background: '#0d0d0d', borderColor: 'rgba(255,255,255,0.16)', borderRadius: 8, color: '#f4f4f6', fontSize: 12 }} />
              <Line type="monotone" dataKey="precision" stroke="#3b82f6" strokeWidth={2} dot={{ r: 4 }} name="Precision" />
            </LineChart>
          </ResponsiveContainer>
        </div>

        {/* Right: Threshold Comparison Table */}
        <div className="section-card">
          <div className="card-head">
            <div>
              <h3>Decision Threshold Performance Comparison</h3>
              <p className="card-sub">Evaluating risk score classification boundaries</p>
            </div>
          </div>

          <div className="table-responsive margin-top-xs">
            <table className="mini-table">
              <thead>
                <tr>
                  <th>Threshold</th>
                  <th>Precision</th>
                  <th>Recall</th>
                  <th>F1 Score</th>
                  <th>False Alarms (FP)</th>
                </tr>
              </thead>
              <tbody>
                {threshold_comparison.map((t, idx) => (
                  <tr key={idx} className={t.threshold === 0.50 ? 'active-row' : ''}>
                    <td className="font-mono font-bold text-ink">
                      {t.threshold.toFixed(2)} {t.threshold === 0.50 && <span className="default-badge">Default</span>}
                    </td>
                    <td className="font-mono">{(t.precision * 100).toFixed(1)}%</td>
                    <td className="font-mono">{(t.recall * 100).toFixed(1)}%</td>
                    <td className="font-mono font-bold text-teal">{(t.f1 * 100).toFixed(1)}%</td>
                    <td className="font-mono text-warning">{t.false_positives}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>

      {/* 5. Benchmark Model Comparison Section */}
      <div className="section-card margin-top-xs">
        <div className="section-title flex-between">
          <div className="flex-align gap-xs">
            <Sliders size={18} className="title-icon text-teal" />
            <div>
              <h3>Model Benchmark Comparison</h3>
              <p className="card-sub">Side-by-side performance audit across candidate algorithms</p>
            </div>
          </div>

          <span className="prod-chip flex-align gap-xs">
            <Sparkles size={13} className="text-teal" /> Production Baseline Selected
          </span>
        </div>

        <div className="table-responsive margin-top-xs">
          <table className="mini-table">
            <thead>
              <tr>
                <th>Model Architecture</th>
                <th>Model Type</th>
                <th>Precision</th>
                <th>Recall</th>
                <th>F1 Score</th>
                <th>ROC-AUC</th>
                <th>PR-AUC</th>
                <th>Status</th>
              </tr>
            </thead>
            <tbody>
              {model_comparison.map((m, idx) => (
                <tr key={idx} className={m.is_production ? 'production-model-row' : ''}>
                  <td className="font-semibold text-ink">
                    {m.model_name}
                  </td>
                  <td className="font-mono text-xs text-stone">{m.model_type}</td>
                  <td className="font-mono">{(m.precision * 100).toFixed(1)}%</td>
                  <td className="font-mono">{(m.recall * 100).toFixed(1)}%</td>
                  <td className="font-mono font-semibold">{(m.f1 * 100).toFixed(1)}%</td>
                  <td className="font-mono">{m.roc_auc.toFixed(3)}</td>
                  <td className="font-mono">{m.pr_auc.toFixed(3)}</td>
                  <td>
                    {m.is_production ? (
                      <span className="prod-status-badge flex-align gap-xs">
                        <Check size={12} /> Active Production
                      </span>
                    ) : (
                      <span className="bench-status-badge">Candidate Benchmark</span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}

