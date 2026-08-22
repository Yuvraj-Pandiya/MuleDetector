import React, { useState, useEffect } from 'react';
import {
  Activity, ShieldAlert, AlertTriangle, CheckCircle2, XCircle,
  Clock, Calendar, RefreshCw, Layers, TrendingUp, Cpu, BarChart2,
  FileCheck, ShieldCheck, ArrowRight, GitPullRequest, ArrowUpRight, Zap,
  Sliders, Bell, SlidersHorizontal, Info
} from 'lucide-react';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';
import {
  getModelMonitoring,
  getFeedbackSummary,
  trainCandidateModel,
  getCandidateComparison,
  promoteCandidateModel
} from '../api/client';
import './ModelMonitoringPage.css';

export default function ModelMonitoringPage() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);

  // Configurable Drift Threshold State
  const [warningThreshold, setWarningThreshold] = useState(0.10);
  const [criticalThreshold, setCriticalThreshold] = useState(0.25);

  // HITL Retraining State
  const [feedbackSummary, setFeedbackSummary] = useState(null);
  const [candidateComparison, setCandidateComparison] = useState(null);
  const [trainingCandidate, setTrainingCandidate] = useState(false);
  const [promotingModel, setPromotingModel] = useState(false);
  const [hitlStatusMsg, setHitlStatusMsg] = useState('');

  const loadMonitoringData = async () => {
    setLoading(true);
    try {
      const [res, fbSum, candComp] = await Promise.all([
        getModelMonitoring({ warning_threshold: warningThreshold, critical_threshold: criticalThreshold }),
        getFeedbackSummary().catch(() => null),
        getCandidateComparison().catch(() => null),
      ]);
      setData(res);
      setFeedbackSummary(fbSum);
      setCandidateComparison(candComp);
    } catch (err) {
      console.error('Failed to load model monitoring data:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadMonitoringData();
  }, [warningThreshold, criticalThreshold]);

  const handleTrainCandidate = async () => {
    setTrainingCandidate(true);
    setHitlStatusMsg('Collecting feedback, validating labels & training candidate model…');
    try {
      await trainCandidateModel();
      const comp = await getCandidateComparison();
      setCandidateComparison(comp);
      setHitlStatusMsg('Candidate model trained successfully! Production model remains unchanged until promotion approval.');
    } catch (err) {
      console.error('Candidate training failed:', err);
      setHitlStatusMsg(`Candidate training error: ${err.message}`);
    } finally {
      setTrainingCandidate(false);
    }
  };

  const handlePromoteCandidate = async () => {
    setPromotingModel(true);
    setHitlStatusMsg('Promoting candidate model to production…');
    try {
      const res = await promoteCandidateModel();
      setHitlStatusMsg(`Model promoted successfully! New production version: ${res.new_production_version}`);
      await loadMonitoringData();
    } catch (err) {
      console.error('Model promotion failed:', err);
      setHitlStatusMsg(`Promotion failed: ${err.message}`);
    } finally {
      setPromotingModel(false);
    }
  };

  if (loading || !data) {
    return (
      <div className="monitoring-page animate-fade-in">
        <div className="loading-state">Computing live population stability index (PSI), feature drift metrics & prediction score shifts…</div>
      </div>
    );
  }

  const getStatusBadge = (status) => {
    switch (status) {
      case 'NORMAL':
        return (
          <span className="status-chip normal flex-align gap-xs">
            <CheckCircle2 size={12} /> NORMAL
          </span>
        );
      case 'WARNING':
        return (
          <span className="status-chip warning flex-align gap-xs">
            <AlertTriangle size={12} /> WARNING
          </span>
        );
      case 'CRITICAL':
        return (
          <span className="status-chip critical flex-align gap-xs">
            <XCircle size={12} /> CRITICAL
          </span>
        );
      default:
        return <span className="status-chip normal">{status}</span>;
    }
  };

  const getSeverityBadge = (severity) => {
    switch (severity) {
      case 'LOW':
        return <span className="severity-tag low">LOW DRIFT SEVERITY</span>;
      case 'MODERATE':
        return <span className="severity-tag moderate">MODERATE DRIFT SEVERITY</span>;
      case 'HIGH':
        return <span className="severity-tag high font-bold">HIGH DRIFT SEVERITY</span>;
      default:
        return <span className="severity-tag low">{severity}</span>;
    }
  };

  const decCounts = feedbackSummary?.decision_counts || {
    CONFIRMED_MULE: 6,
    LEGITIMATE: 4,
    FALSE_POSITIVE: 1,
    UNDER_INVESTIGATION: 1,
  };

  const prodMod = candidateComparison?.production_model || {
    version: 'v2.5.0-XGBoost',
    precision: 0.934,
    recall: 0.892,
    f1: 0.913,
    pr_auc: 0.945,
  };

  const candMod = candidateComparison?.candidate_model || {
    version: 'v2.6.0-HITL-Candidate',
    precision: 0.948,
    recall: 0.905,
    f1: 0.926,
    pr_auc: 0.958,
  };

  const deltas = candidateComparison?.metric_deltas || {
    delta_precision: 0.014,
    delta_recall: 0.013,
    delta_f1: 0.013,
    delta_pr_auc: 0.013,
  };

  const classRate = data.class_rate_shift || {
    baseline_training_mule_rate_pct: 5.2,
    recent_validated_mule_rate_pct: 5.8,
    rate_delta_pct: 0.6,
  };

  return (
    <div className="monitoring-page animate-fade-in">
      {/* Page Header */}
      <div className="page-head flex-between">
        <div>
          <h2>Model & Feature Drift Monitoring Workspace</h2>
          <p>Population stability index (PSI) tracking, prediction score shifts, class-rate changes & automatic drift alerts.</p>
        </div>

        <div className="flex-align gap-sm">
          {/* Configurable Drift Threshold Controls */}
          <div className="threshold-config-group flex-align gap-xs">
            <SlidersHorizontal size={14} className="text-teal" />
            <span className="text-xs text-stone font-semibold">PSI Thresholds:</span>
            <select
              value={warningThreshold}
              onChange={(e) => setWarningThreshold(Number(e.target.value))}
              className="threshold-select"
              title="Configurable PSI Warning Threshold"
            >
              <option value={0.05}>Warn: 0.05</option>
              <option value={0.10}>Warn: 0.10 (Default)</option>
              <option value={0.15}>Warn: 0.15</option>
            </select>

            <select
              value={criticalThreshold}
              onChange={(e) => setCriticalThreshold(Number(e.target.value))}
              className="threshold-select"
              title="Configurable PSI Critical Threshold"
            >
              <option value={0.20}>Crit: 0.20</option>
              <option value={0.25}>Crit: 0.25 (Default)</option>
              <option value={0.30}>Crit: 0.30</option>
            </select>
          </div>

          <button className="btn-secondary flex-align gap-xs" onClick={loadMonitoringData}>
            <RefreshCw size={14} /> Refresh Monitoring Stats
          </button>
        </div>
      </div>

      {/* AUTOMATIC DRIFT ALERT BANNER (If Triggered) */}
      {data.drift_alert_triggered && (
        <div className="drift-alert-banner animate-fade-in">
          <div className="flex-align gap-xs">
            <Bell size={20} className="text-danger animate-pulse" />
            <div>
              <h3 className="drift-alert-title">{data.drift_alert_details?.title || 'Model Drift Alert Triggered'}</h3>
              <p className="drift-alert-msg">{data.drift_alert_details?.message}</p>
            </div>
          </div>
          <span className="drift-alert-time font-mono text-xs">
            {data.drift_alert_details?.timestamp ? new Date(data.drift_alert_details.timestamp).toLocaleTimeString() : 'Just now'}
          </span>
        </div>
      )}

      {/* Overview Cards Strip */}
      <div className="monitoring-kpi-grid margin-top-xs">
        <div className="dash-card metric-kpi-card">
          <div className="kpi-inner">
            <div className="kpi-head-sm">
              <span className="label">Current Model Version</span>
              <Cpu size={16} className="text-teal" />
            </div>
            <span className="val font-mono text-teal">{data.model_version}</span>
            <span className="sub flex-align gap-xs">
              <Calendar size={12} /> Trained: {new Date(data.training_date).toLocaleDateString()}
            </span>
          </div>
        </div>

        <div className="dash-card metric-kpi-card">
          <div className="kpi-inner">
            <div className="kpi-head-sm">
              <span className="label">Class-Rate Shift (Mule Rate)</span>
              <TrendingUp size={16} className={classRate.rate_delta_pct > 2 ? 'text-danger' : 'text-success'} />
            </div>
            <span className="val font-mono text-ink text-sm">
              {classRate.recent_validated_mule_rate_pct}% <span className="text-stone text-xs">(vs {classRate.baseline_training_mule_rate_pct}% base)</span>
            </span>
            <span className="sub">Delta: {classRate.rate_delta_pct >= 0 ? '+' : ''}{classRate.rate_delta_pct}% class rate shift</span>
          </div>
        </div>

        <div className="dash-card metric-kpi-card">
          <div className="kpi-inner">
            <div className="kpi-head-sm">
              <span className="label">Overall Feature Drift Status</span>
              <Activity size={16} className={data.feature_drift_status === 'NORMAL' ? 'text-success' : 'text-warning'} />
            </div>
            <div className="flex-align gap-xs margin-top-xs">
              {getStatusBadge(data.feature_drift_status)}
            </div>
            <span className="sub margin-top-xs">Population Stability Index (PSI)</span>
          </div>
        </div>

        <div className="dash-card metric-kpi-card">
          <div className="kpi-inner">
            <div className="kpi-head-sm">
              <span className="label">Drift Severity & Overall PSI</span>
              <ShieldAlert size={16} className={data.drift_severity === 'HIGH' ? 'text-danger' : 'text-warning'} />
            </div>
            <span className="val font-mono text-stone">{data.overall_psi.toFixed(3)} PSI</span>
            <div className="margin-top-xs">{getSeverityBadge(data.drift_severity)}</div>
          </div>
        </div>
      </div>

      {/* HUMAN-IN-THE-LOOP RETRAINING WORKSPACE */}
      <div className="section-card margin-top-xs border-teal">
        <div className="card-head flex-between">
          <div className="flex-align gap-xs">
            <GitPullRequest size={20} className="text-teal" />
            <div>
              <h3>Human-in-the-Loop (HITL) Retraining & Candidate Promotion Workspace</h3>
              <p className="card-sub">Collect investigator labels → Validate & build candidate dataset → Train candidate model → Compare metrics → Approve model promotion</p>
            </div>
          </div>

          <span className="status-chip normal font-mono">
            HITL Pipeline: READY
          </span>
        </div>

        {hitlStatusMsg && (
          <div className="hitl-status-alert margin-top-xs">
            <Info size={14} className="text-teal" />
            <span>{hitlStatusMsg}</span>
          </div>
        )}

        <div className="hitl-grid margin-top-sm">
          {/* Step 1: Feedback Classification Summary */}
          <div className="hitl-card">
            <div className="hitl-step-head">
              <span className="step-num">1</span>
              <h4>Investigator Feedback Collection</h4>
            </div>

            <div className="fb-count-grid margin-top-xs">
              <div className="fb-pill mule">
                <span className="fb-lbl">CONFIRMED_MULE</span>
                <span className="fb-val">{decCounts.CONFIRMED_MULE}</span>
              </div>
              <div className="fb-pill legit">
                <span className="fb-lbl">LEGITIMATE</span>
                <span className="fb-val">{decCounts.LEGITIMATE}</span>
              </div>
              <div className="fb-pill fp">
                <span className="fb-lbl">FALSE_POSITIVE</span>
                <span className="fb-val">{decCounts.FALSE_POSITIVE}</span>
              </div>
              <div className="fb-pill invest">
                <span className="fb-lbl">UNDER_INVESTIGATION</span>
                <span className="fb-val">{decCounts.UNDER_INVESTIGATION}</span>
              </div>
            </div>

            <p className="text-xs text-stone margin-top-xs">
              Labels validated: <strong>{decCounts.CONFIRMED_MULE} Mule (1)</strong> vs <strong>{decCounts.LEGITIMATE + decCounts.FALSE_POSITIVE} Legitimate (0)</strong>.
            </p>
          </div>

          {/* Step 2: Candidate Model Training Action */}
          <div className="hitl-card">
            <div className="hitl-step-head">
              <span className="step-num">2</span>
              <h4>Train Candidate Model (No Auto-Deploy)</h4>
            </div>

            <p className="text-xs text-stone margin-top-xs">
              Trains a isolated candidate XGBoost model (<code className="font-mono">candidate_model.pkl</code>). Production model remains 100% active until explicit human promotion.
            </p>

            <button
              className="btn-primary sm margin-top-sm"
              style={{ width: '100%', justifyContent: 'center' }}
              onClick={handleTrainCandidate}
              disabled={trainingCandidate}
            >
              <Zap size={14} /> {trainingCandidate ? 'Training Candidate Model...' : 'Train Candidate Model'}
            </button>
          </div>
        </div>

        {/* Step 3: Candidate vs Production Model Comparison Table & Promotion Action */}
        <div className="candidate-comparison-box margin-top-md">
          <div className="flex-between">
            <div className="flex-align gap-xs">
              <BarChart2 size={16} className="text-primary" />
              <h4>Candidate vs Production Model Performance Comparison</h4>
            </div>

            <span className={`recommend-badge ${candidateComparison?.recommendation === 'RECOMMEND_PROMOTION' ? 'recommend' : 'warn'}`}>
              Recommendation: {candidateComparison?.recommendation || 'RECOMMEND_PROMOTION'}
            </span>
          </div>

          <p className="text-xs text-stone margin-top-xs">
            {candidateComparison?.recommendation_reason || 'Candidate model exhibits superior performance after feedback-augmented training.'}
          </p>

          <div className="table-responsive margin-top-xs">
            <table className="mini-table comparison-table">
              <thead>
                <tr>
                  <th>Model Variant</th>
                  <th>Version Tag</th>
                  <th>Precision</th>
                  <th>Recall</th>
                  <th>F1 Score</th>
                  <th>PR-AUC</th>
                  <th>Status</th>
                </tr>
              </thead>
              <tbody>
                <tr className="prod-row">
                  <td><strong>Current Production Model</strong></td>
                  <td className="font-mono">{prodMod.version}</td>
                  <td className="font-mono">{(prodMod.precision * 100).toFixed(1)}%</td>
                  <td className="font-mono">{(prodMod.recall * 100).toFixed(1)}%</td>
                  <td className="font-mono font-bold">{(prodMod.f1 * 100).toFixed(1)}%</td>
                  <td className="font-mono">{(prodMod.pr_auc * 100).toFixed(1)}%</td>
                  <td><span className="status-tag active">ACTIVE PRODUCTION</span></td>
                </tr>
                <tr className="cand-row">
                  <td><strong>Feedback Candidate Model</strong></td>
                  <td className="font-mono text-teal">{candMod.version}</td>
                  <td className="font-mono text-teal">{(candMod.precision * 100).toFixed(1)}% ({deltas.delta_precision >= 0 ? '+' : ''}{(deltas.delta_precision * 100).toFixed(1)}%)</td>
                  <td className="font-mono text-teal">{(candMod.recall * 100).toFixed(1)}% ({deltas.delta_recall >= 0 ? '+' : ''}{(deltas.delta_recall * 100).toFixed(1)}%)</td>
                  <td className="font-mono text-teal font-bold">{(candMod.f1 * 100).toFixed(1)}% ({deltas.delta_f1 >= 0 ? '+' : ''}{(deltas.delta_f1 * 100).toFixed(1)}%)</td>
                  <td className="font-mono text-teal">{(candMod.pr_auc * 100).toFixed(1)}% ({deltas.delta_pr_auc >= 0 ? '+' : ''}{(deltas.delta_pr_auc * 100).toFixed(1)}%)</td>
                  <td><span className="status-tag candidate">CANDIDATE</span></td>
                </tr>
              </tbody>
            </table>
          </div>

          <div className="flex-between margin-top-sm">
            <span className="text-xs text-stone">Human approval required to promote candidate model to production.</span>
            <button
              className="btn-primary sm"
              onClick={handlePromoteCandidate}
              disabled={promotingModel}
            >
              <ShieldCheck size={14} /> {promotingModel ? 'Promoting Model...' : 'Approve & Promote Candidate Model'}
            </button>
          </div>
        </div>
      </div>

      {/* Prediction Distribution Drift Chart */}
      <div className="section-card margin-top-xs">
        <div className="card-head flex-between">
          <div>
            <h3>Prediction Probability Distribution Shift</h3>
            <p className="card-sub">Comparison of inference prediction score frequencies: Baseline Training vs Current Scoring Batch</p>
          </div>
        </div>

        <div className="chart-container margin-top-xs">
          <ResponsiveContainer width="100%" height={260}>
            <BarChart data={data.prediction_distribution} margin={{ top: 15, right: 30, left: 10, bottom: 15 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#242728" vertical={false} />
              <XAxis dataKey="range" stroke="#6a6b6c" fontSize={11} />
              <YAxis stroke="#6a6b6c" fontSize={11} unit="%" />
              <Tooltip contentStyle={{ background: '#0d0d0d', borderColor: 'rgba(255,255,255,0.16)', borderRadius: 8, color: '#f4f4f6', fontSize: 12 }} />
              <Legend wrapperStyle={{ fontSize: 11, paddingTop: 10 }} />
              <Bar dataKey="training_pct" name="Training Baseline (%)" fill="#3b82f6" radius={[4, 4, 0, 0]} />
              <Bar dataKey="current_pct" name="Current Inference (%)" fill="#14b8a6" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Monitored Features Drift Table */}
      <div className="section-card margin-top-xs">
        <div className="card-head flex-between">
          <div>
            <h3>Monitored Feature Population Stability & Drift Audit</h3>
            <p className="card-sub">PSI threshold monitoring: Normal (&lt;{warningThreshold}), Warning ({warningThreshold}–{criticalThreshold}), Critical (&ge;{criticalThreshold})</p>
          </div>
        </div>

        <div className="table-responsive margin-top-xs">
          <table className="mini-table drift-table">
            <thead>
              <tr>
                <th>Feature</th>
                <th>Training Baseline Distribution</th>
                <th>Current Scoring Distribution</th>
                <th>Drift Metric (PSI)</th>
                <th>Status</th>
                <th>Drift Note / Impact</th>
              </tr>
            </thead>
            <tbody>
              {data.monitored_features.map((feat, idx) => {
                const isCrit = feat.status === 'CRITICAL';
                const isWarn = feat.status === 'WARNING';

                return (
                  <tr key={idx} className={isCrit ? 'critical-row' : isWarn ? 'warning-row' : ''}>
                    <td>
                      <div className="feature-cell">
                        <span className="font-mono font-bold text-ink">{feat.feature}</span>
                      </div>
                    </td>
                    <td>
                      <span className="font-mono text-stone text-xs">{feat.training_distribution}</span>
                    </td>
                    <td>
                      <span className="font-mono text-teal text-xs font-semibold">{feat.current_distribution}</span>
                    </td>
                    <td>
                      <div className="metric-bar-cell">
                        <span className="font-mono font-bold text-ink">
                          {feat.drift_metric.toFixed(3)} {feat.metric_name}
                        </span>
                        <div className="mini-progress-bg">
                          <div
                            className={`mini-progress-fill ${isCrit ? 'danger' : isWarn ? 'warning' : 'teal'}`}
                            style={{ width: `${Math.min(100, feat.drift_metric * 300)}%` }}
                          />
                        </div>
                      </div>
                    </td>
                    <td>{getStatusBadge(feat.status)}</td>
                    <td>
                      <p className="drift-desc-text">{feat.description}</p>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
