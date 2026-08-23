import React, { useState, useEffect, useMemo } from 'react';
import {
  Brain, Layers, ArrowUpDown, Filter, CheckCircle2, XCircle,
  Zap, Clock, GitMerge, UserCheck, ShieldAlert, DollarSign, RefreshCw, HelpCircle, ChevronRight
} from 'lucide-react';
import { getFeatureIntelligence } from '../api/client';
import './FeatureIntelligencePage.css';

const CATEGORIES = ['ALL', 'Transaction', 'Velocity', 'Fund Flow', 'Behavioral', 'Temporal', 'Network'];

export default function FeatureIntelligencePage() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [selectedCategory, setSelectedCategory] = useState('ALL');
  const [topLimit, setTopLimit] = useState('10'); // '10', '20', 'ALL'
  const [sortBy, setSortBy] = useState('shap_importance'); // 'shap_importance', 'xgb_importance', 'mutual_information'

  const loadData = async () => {
    setLoading(true);
    try {
      const res = await getFeatureIntelligence();
      setData(res);
    } catch (err) {
      console.error('Failed to load feature intelligence:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
    const handleDatasetChange = () => {
      loadData();
    };
    window.addEventListener('dataset-changed', handleDatasetChange);
    return () => window.removeEventListener('dataset-changed', handleDatasetChange);
  }, []);

  const processedFeatures = useMemo(() => {
    if (!data || !data.features) return [];

    let list = [...data.features];

    // Filter by Category
    if (selectedCategory !== 'ALL') {
      list = list.filter((f) => f.category.toLowerCase() === selectedCategory.toLowerCase());
    }

    // Sort by selected metric
    list.sort((a, b) => {
      const valA = a[sortBy] ?? 0;
      const valB = b[sortBy] ?? 0;
      return valB - valA;
    });

    // Apply Top N Limit
    if (topLimit === '10') {
      return list.slice(0, 10);
    }
    if (topLimit === '20') {
      return list.slice(0, 20);
    }
    return list;
  }, [data, selectedCategory, topLimit, sortBy]);

  if (loading || !data) {
    return (
      <div className="features-page animate-fade-in">
        <div className="loading-state">Evaluating feature importance, SHAP weights, and mutual information...</div>
      </div>
    );
  }

  const selectedCount = data.features.filter((f) => f.status === 'SELECTED').length;
  const rejectedCount = data.features.filter((f) => f.status === 'REJECTED').length;

  const getCategoryIcon = (category) => {
    switch (category) {
      case 'Transaction':
        return DollarSign;
      case 'Velocity':
        return Zap;
      case 'Fund Flow':
        return GitMerge;
      case 'Behavioral':
        return UserCheck;
      case 'Temporal':
        return Clock;
      case 'Network':
        return Layers;
      default:
        return Brain;
    }
  };

  return (
    <div className="features-page animate-fade-in">
      {/* Header */}
      <div className="page-head flex-between">
        <div>
          <h2>Feature Intelligence & Signal Ranking</h2>
          <p>Multi-method explainability, SHAP global importances, and mutual information signal taxonomy.</p>
        </div>

        <button className="btn-secondary flex-align gap-xs" onClick={loadData}>
          <RefreshCw size={14} /> Refresh Features
        </button>
      </div>

      {/* KPI Cards */}
      <div className="kpi-grid margin-top-xs">
        <div className="dash-card metric-kpi-card">
          <div className="kpi-inner">
            <div className="kpi-head-sm">
              <span className="label">Total Features Evaluated</span>
              <Brain size={16} className="text-teal" />
            </div>
            <span className="val">{data.features.length}</span>
            <span className="sub">6 Taxonomy Categories</span>
          </div>
        </div>

        <div className="dash-card metric-kpi-card">
          <div className="kpi-inner">
            <div className="kpi-head-sm">
              <span className="label">Selected (Retained) Signals</span>
              <CheckCircle2 size={16} className="text-success" />
            </div>
            <span className="val text-success">{selectedCount}</span>
            <span className="sub">Passed Composite Selection Threshold</span>
          </div>
        </div>

        <div className="dash-card metric-kpi-card">
          <div className="kpi-inner">
            <div className="kpi-head-sm">
              <span className="label">Rejected Features</span>
              <XCircle size={16} className="text-danger" />
            </div>
            <span className="val text-danger">{rejectedCount}</span>
            <span className="sub">Low Predictive Significance</span>
          </div>
        </div>
      </div>

      {/* Controls Bar */}
      <div className="controls-card margin-top-xs flex-between wrap-gap">
        {/* Category Pills */}
        <div className="category-pills flex-align gap-xs">
          <span className="filter-label flex-align gap-xs">
            <Filter size={14} className="text-stone" /> Group:
          </span>
          {CATEGORIES.map((cat) => (
            <button
              key={cat}
              className={`pill-btn ${selectedCategory === cat ? 'active' : ''}`}
              onClick={() => setSelectedCategory(cat)}
            >
              {cat}
            </button>
          ))}
        </div>

        {/* Limit & Sorting */}
        <div className="right-controls flex-align gap-sm">
          {/* Top Limit Buttons */}
          <div className="pill-group flex-align">
            <span className="filter-label text-xs text-stone margin-right-xs">Show:</span>
            <button
              className={`pill-btn-sm ${topLimit === '10' ? 'active' : ''}`}
              onClick={() => setTopLimit('10')}
            >
              Top 10
            </button>
            <button
              className={`pill-btn-sm ${topLimit === '20' ? 'active' : ''}`}
              onClick={() => setTopLimit('20')}
            >
              Top 20
            </button>
            <button
              className={`pill-btn-sm ${topLimit === 'ALL' ? 'active' : ''}`}
              onClick={() => setTopLimit('ALL')}
            >
              All Features
            </button>
          </div>

          {/* Sort Selector */}
          <div className="sort-box flex-align gap-xs">
            <ArrowUpDown size={14} className="text-teal" />
            <select
              value={sortBy}
              onChange={(e) => setSortBy(e.target.value)}
              className="select-input"
            >
              <option value="shap_importance">Sort: SHAP Global Importance</option>
              <option value="xgb_importance">Sort: XGBoost Gain Importance</option>
              <option value="mutual_information">Sort: Mutual Information</option>
            </select>
          </div>
        </div>
      </div>

      {/* Main Feature Table */}
      <div className="section-card margin-top-xs">
        <div className="card-head flex-between">
          <div>
            <h3>Feature Ranking & Multi-Method Metrics</h3>
            <p className="card-sub">
              Showing {processedFeatures.length} features sorted by{' '}
              {sortBy === 'shap_importance'
                ? 'SHAP Importance'
                : sortBy === 'xgb_importance'
                ? 'XGBoost Gain'
                : 'Mutual Information'}
            </p>
          </div>
        </div>

        <div className="table-responsive margin-top-xs">
          <table className="mini-table feature-table">
            <thead>
              <tr>
                <th>Rank</th>
                <th>Feature Name</th>
                <th>Category</th>
                <th>SHAP Importance</th>
                <th>XGBoost Gain</th>
                <th>Mutual Info</th>
                <th>Status</th>
                <th>Mule-Risk Interpretation</th>
              </tr>
            </thead>
            <tbody>
              {processedFeatures.map((feat, idx) => {
                const CatIcon = getCategoryIcon(feat.category);
                const isSelected = feat.status === 'SELECTED';
                const shapPercent = (feat.shap_importance * 100).toFixed(1);

                return (
                  <tr key={idx} className={!isSelected ? 'rejected-row' : ''}>
                    <td className="font-mono text-stone font-semibold">#{idx + 1}</td>
                    <td>
                      <div className="feature-title-cell">
                        <span className="font-mono font-semibold text-ink">{feat.feature_name}</span>
                        <span className="text-xs text-stone">{feat.description}</span>
                      </div>
                    </td>
                    <td>
                      <span className={`category-badge cat-${feat.category.toLowerCase().replace(' ', '-')}`}>
                        <CatIcon size={12} /> {feat.category}
                      </span>
                    </td>
                    <td>
                      <div className="metric-bar-cell">
                        <span className="font-mono text-teal font-semibold">{feat.shap_importance.toFixed(3)}</span>
                        <div className="mini-progress-bg">
                          <div
                            className="mini-progress-fill teal"
                            style={{ width: `${Math.min(100, feat.shap_importance * 350)}%` }}
                          />
                        </div>
                      </div>
                    </td>
                    <td className="font-mono text-ink">{feat.xgb_importance.toFixed(3)}</td>
                    <td className="font-mono text-stone">{feat.mutual_information.toFixed(3)}</td>
                    <td>
                      {isSelected ? (
                        <span className="status-chip selected flex-align gap-xs">
                          <CheckCircle2 size={12} /> Selected
                        </span>
                      ) : (
                        <span className="status-chip rejected flex-align gap-xs">
                          <XCircle size={12} /> Rejected
                        </span>
                      )}
                    </td>
                    <td>
                      <p className="interpretation-text">{feat.interpretation}</p>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>

      {/* Why Each Top Feature Matters Explanations Panel */}
      <div className="section-card margin-top-xs">
        <div className="section-title flex-align gap-xs">
          <ShieldAlert size={18} className="title-icon text-warning" />
          <div>
            <h3>Why Top Features Matter for Mule Detection</h3>
            <span>Domain-specific anti-money laundering (AML) breakdown for key risk drivers</span>
          </div>
        </div>

        <div className="explanations-grid margin-top-xs">
          {processedFeatures.slice(0, 6).map((feat, idx) => {
            const CatIcon = getCategoryIcon(feat.category);
            return (
              <div key={idx} className="explanation-card">
                <div className="exp-head flex-between">
                  <div className="flex-align gap-xs">
                    <span className="exp-rank font-mono">#{idx + 1}</span>
                    <h4 className="font-mono text-ink">{feat.feature_name}</h4>
                  </div>
                  <span className={`category-badge cat-${feat.category.toLowerCase().replace(' ', '-')}`}>
                    <CatIcon size={12} /> {feat.category}
                  </span>
                </div>

                <div className="exp-body margin-top-xs">
                  <p className="exp-desc">{feat.description}</p>
                  <div className="exp-callout margin-top-xs">
                    <span className="callout-title flex-align gap-xs">
                      <ChevronRight size={13} className="text-teal" /> Anti-Mule Rationale:
                    </span>
                    <p className="callout-text">{feat.interpretation}</p>
                  </div>
                </div>

                <div className="exp-footer margin-top-xs flex-between text-xs font-mono text-stone">
                  <span>SHAP Score: {(feat.shap_importance * 100).toFixed(1)}%</span>
                  <span>XGB Gain: {feat.xgb_importance.toFixed(3)}</span>
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
