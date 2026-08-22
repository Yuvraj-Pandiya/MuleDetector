import React, { useState, useEffect } from 'react';
import {
  BarChart3, Award, Target, Activity, ShieldCheck,
  CheckCircle2, AlertTriangle, Layers,
} from 'lucide-react';
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer, Cell,
} from 'recharts';
import { getModelMetrics } from '../api/client';
import './ModelMetricsPage.css';

export default function ModelMetricsPage() {
  const [metrics, setMetrics] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function loadData() {
      setLoading(true);
      try {
        const data = await getModelMetrics();
        setMetrics(data);
      } catch (err) {
        console.error('Failed to load metrics:', err);
      } finally {
        setLoading(false);
      }
    }
    loadData();
  }, []);

  if (loading || !metrics) {
    return <div className="loading-state">Evaluating Graph Neural Network model performance…</div>;
  }

  const kpis = [
    { label: 'Accuracy', val: `${(metrics.accuracy * 100).toFixed(1)}%`, sub: 'Overall classification correctness', icon: Award },
    { label: 'Precision', val: `${(metrics.precision * 100).toFixed(1)}%`, sub: 'Low false alarm rate', icon: Target },
    { label: 'Recall (Sensitivity)', val: `${(metrics.recall * 100).toFixed(1)}%`, sub: 'Mule ring detection coverage', icon: Activity },
    { label: 'F1 Score', val: `${(metrics.f1_score * 100).toFixed(1)}%`, sub: 'Harmonic mean balance', icon: ShieldCheck },
    { label: 'ROC-AUC', val: metrics.roc_auc.toFixed(3), sub: 'Separability index', icon: BarChart3 },
  ];

  return (
    <div className="metrics-page animate-fade-in">
      <div className="page-head">
        <h2>Model Performance & Evaluation Intelligence</h2>
        <p>Quantitative audit metrics for the Graph Neural Network + Gradient Boosted Mule Classifier.</p>
      </div>

      {/* KPI Cards Strip */}
      <div className="metrics-kpi-grid">
        {kpis.map((k, i) => {
          const Icon = k.icon;
          return (
            <div key={i} className="dash-card metric-kpi-card">
              <div className="kpi-inner">
                <div className="kpi-head-sm">
                  <span className="label">{k.label}</span>
                  <Icon size={16} className="text-primary" />
                </div>
                <span className="val">{k.val}</span>
                <span className="sub">{k.sub}</span>
              </div>
            </div>
          );
        })}
      </div>

      {/* Main Grid: Confusion Matrix + Feature Importance */}
      <div className="metrics-grid-main">
        {/* Left: Confusion Matrix */}
        <div className="matrix-card">
          <div className="card-head">
            <div>
              <h3>Confusion Matrix</h3>
              <p className="card-sub">Holdout test set evaluations (n=2,247)</p>
            </div>
          </div>

          <div className="matrix-2x2">
            <div className="matrix-cell tp">
              <span className="cell-title">True Positives (TP)</span>
              <span className="cell-num">{metrics.confusion_matrix.tp}</span>
              <span className="cell-desc">Correctly flagged mules</span>
            </div>

            <div className="matrix-cell fp">
              <span className="cell-title">False Positives (FP)</span>
              <span className="cell-num">{metrics.confusion_matrix.fp}</span>
              <span className="cell-desc">False alarms (normal flagged)</span>
            </div>

            <div className="matrix-cell fn">
              <span className="cell-title">False Negatives (FN)</span>
              <span className="cell-num">{metrics.confusion_matrix.fn}</span>
              <span className="cell-desc">Missed mule accounts</span>
            </div>

            <div className="matrix-cell tn">
              <span className="cell-title">True Negatives (TN)</span>
              <span className="cell-num">{metrics.confusion_matrix.tn}</span>
              <span className="cell-desc">Correctly identified legitimate</span>
            </div>
          </div>

          <div className="matrix-stats-footer">
            <div className="m-stat">
              <span>False Positive Rate:</span>
              <span className="font-mono text-ink">
                {((metrics.confusion_matrix.fp / (metrics.confusion_matrix.fp + metrics.confusion_matrix.tn)) * 100).toFixed(2)}%
              </span>
            </div>
            <div className="m-stat">
              <span>Detection Rate:</span>
              <span className="font-mono text-ink">
                {((metrics.confusion_matrix.tp / (metrics.confusion_matrix.tp + metrics.confusion_matrix.fn)) * 100).toFixed(2)}%
              </span>
            </div>
          </div>
        </div>

        {/* Right: Global Feature Importance */}
        <div className="importance-card">
          <div className="card-head">
            <div>
              <h3>Global Feature Importance</h3>
              <p className="card-sub">GNN embedding & structural graph feature weightings</p>
            </div>
          </div>

          <ResponsiveContainer width="100%" height={340}>
            <BarChart
              layout="vertical"
              data={metrics.feature_importance}
              margin={{ top: 5, right: 30, left: 60, bottom: 5 }}
            >
              <CartesianGrid strokeDasharray="3 3" stroke="#242728" horizontal={false} />
              <XAxis type="number" stroke="#6a6b6c" fontSize={11} />
              <YAxis
                dataKey="feature"
                type="category"
                stroke="#cdcdcd"
                fontSize={11}
                tickLine={false}
                width={120}
              />
              <Tooltip
                contentStyle={{ background: '#0d0d0d', borderColor: 'rgba(255,255,255,0.16)', borderRadius: 8, color: '#f4f4f6', fontSize: 12 }}
                formatter={(value) => [`${(value * 100).toFixed(1)}%`, 'Weight']}
              />
              <Bar dataKey="importance" fill="#ffffff" radius={[0, 4, 4, 0]}>
                {metrics.feature_importance.map((entry, index) => (
                  <Cell key={index} fill={index < 3 ? '#ffffff' : '#9c9c9d'} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>
    </div>
  );
}
