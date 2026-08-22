import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Users, ShieldAlert, AlertTriangle, Activity,
  ArrowUpRight, Clock, TrendingUp,
} from 'lucide-react';
import {
  PieChart, Pie, Cell, ResponsiveContainer, Tooltip,
  AreaChart, Area, XAxis, YAxis, CartesianGrid, BarChart, Bar,
} from 'recharts';
import { getDashboardSummary, getAlerts } from '../api/client';
import './DashboardPage.css';

const TIER_COLORS = {
  critical: '#EF4444',
  high: '#F59E0B',
  medium: '#3B82F6',
  low: '#10B981',
};

export default function DashboardPage() {
  const [data, setData] = useState(null);
  const [alerts, setAlerts] = useState([]);
  const [loading, setLoading] = useState(true);
  const navigate = useNavigate();

  useEffect(() => {
    async function load() {
      try {
        const [summary, alertList] = await Promise.all([
          getDashboardSummary(),
          getAlerts(),
        ]);
        setData(summary);
        setAlerts(alertList);
      } catch (e) {
        console.error('Dashboard load error:', e);
      } finally {
        setLoading(false);
      }
    }
    load();
  }, []);

  if (loading || !data) {
    return <div className="loading-state">Loading intelligence summary…</div>;
  }

  const pieData = [
    { name: 'Critical', value: data.risk_distribution.critical, color: TIER_COLORS.critical },
    { name: 'High', value: data.risk_distribution.high, color: TIER_COLORS.high },
    { name: 'Medium', value: data.risk_distribution.medium, color: TIER_COLORS.medium },
    { name: 'Low', value: data.risk_distribution.low, color: TIER_COLORS.low },
  ];

  const kpis = [
    {
      label: 'Total Accounts', value: data.total_accounts.toLocaleString(),
      icon: Users, iconClass: 'kpi-icon-primary',
      sub: <span className="kpi-trend up"><TrendingUp size={12} /> +12% this week</span>,
      onClick: () => navigate('/accounts'),
    },
    {
      label: 'Flagged Mule Accounts', value: data.flagged_count,
      icon: ShieldAlert, iconClass: 'kpi-icon-danger', valueClass: 'val-danger',
      sub: 'Requires immediate review',
      onClick: () => navigate('/accounts?tier=critical'),
    },
    {
      label: 'Open Alerts', value: data.open_alerts,
      icon: AlertTriangle, iconClass: 'kpi-icon-warning', valueClass: 'val-warning',
      sub: '3 high priority pending',
      onClick: () => navigate('/alerts'),
    },
    {
      label: 'Mean Risk Index', value: `${data.avg_risk_score} / 100`,
      icon: Activity, iconClass: 'kpi-icon-accent',
      sub: 'Model confidence: 96.2%',
      onClick: () => navigate('/metrics'),
    },
  ];

  return (
    <div className="dash-page animate-fade-in">
      {/* KPI Cards */}
      <div className="kpi-row">
        {kpis.map((k, i) => {
          const Icon = k.icon;
          return (
            <button key={i} className="kpi-card" onClick={k.onClick} id={`kpi-${i}`}>
              <div className={`kpi-icon ${k.iconClass}`}>
                <Icon size={20} />
              </div>
              <div className="kpi-body">
                <span className="kpi-label">{k.label}</span>
                <div className={`kpi-value ${k.valueClass || ''}`}>{k.value}</div>
                <span className="kpi-sub">{k.sub}</span>
              </div>
            </button>
          );
        })}
      </div>

      {/* Charts Row */}
      <div className="charts-row">
        {/* Risk Tier Distribution */}
        <div className="dash-card">
          <div className="card-head">
            <div>
              <h3>Risk Tier Distribution</h3>
              <p className="card-sub">By AI anomaly score classification</p>
            </div>
            <button className="icon-link" onClick={() => navigate('/accounts')} title="View all">
              <ArrowUpRight size={16} />
            </button>
          </div>
          <div className="donut-wrap">
            <ResponsiveContainer width="100%" height={200}>
              <PieChart>
                <Pie data={pieData} cx="50%" cy="50%" innerRadius={58} outerRadius={82} paddingAngle={4} dataKey="value">
                  {pieData.map((e, i) => <Cell key={i} fill={e.color} />)}
                </Pie>
                <Tooltip
                  contentStyle={{ background: '#0d0d0d', borderColor: 'rgba(255,255,255,0.16)', borderRadius: 8, color: '#f4f4f6', fontSize: 13 }}
                />
              </PieChart>
            </ResponsiveContainer>
            <div className="legend-row">
              {pieData.map((d) => (
                <div key={d.name} className="legend-item">
                  <span className="legend-dot" style={{ background: d.color }} />
                  <span className="legend-name">{d.name}</span>
                  <span className="legend-val">{d.value}</span>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* 14-Day Trend */}
        <div className="dash-card">
          <div className="card-head">
            <div>
              <h3>14-Day Alert Velocity</h3>
              <p className="card-sub">Daily generated alerts vs resolved</p>
            </div>
          </div>
          <ResponsiveContainer width="100%" height={220}>
            <AreaChart data={data.trend_data}>
              <defs>
                <linearGradient id="aGrad" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#ffffff" stopOpacity={0.25} />
                  <stop offset="95%" stopColor="#ffffff" stopOpacity={0} />
                </linearGradient>
                <linearGradient id="rGrad" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#10b981" stopOpacity={0.2} />
                  <stop offset="95%" stopColor="#10b981" stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="#242728" />
              <XAxis dataKey="date" stroke="#6a6b6c" fontSize={11} tickFormatter={(v) => v.slice(5)} />
              <YAxis stroke="#6a6b6c" fontSize={11} />
              <Tooltip contentStyle={{ background: '#0d0d0d', borderColor: 'rgba(255,255,255,0.16)', borderRadius: 8, color: '#f4f4f6', fontSize: 13 }} />
              <Area type="monotone" dataKey="alerts" stroke="#ffffff" fill="url(#aGrad)" strokeWidth={1.5} />
              <Area type="monotone" dataKey="resolved" stroke="#10b981" fill="url(#rGrad)" strokeWidth={1.5} />
            </AreaChart>
          </ResponsiveContainer>
        </div>

        {/* Risk Distribution Bar */}
        <div className="dash-card">
          <div className="card-head">
            <div>
              <h3>Tier Volume Breakdown</h3>
              <p className="card-sub">Account count per risk category</p>
            </div>
          </div>
          <ResponsiveContainer width="100%" height={220}>
            <BarChart data={pieData}>
              <CartesianGrid strokeDasharray="3 3" stroke="#242728" />
              <XAxis dataKey="name" stroke="#6a6b6c" fontSize={12} />
              <YAxis stroke="#6a6b6c" fontSize={11} />
              <Tooltip contentStyle={{ background: '#0d0d0d', borderColor: 'rgba(255,255,255,0.16)', borderRadius: 8, color: '#f4f4f6', fontSize: 13 }} />
              <Bar dataKey="value" radius={[4, 4, 0, 0]}>
                {pieData.map((e, i) => <Cell key={i} fill={e.color} />)}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Urgent Alerts Preview */}
      <div className="dash-card">
        <div className="card-head">
          <div>
            <h3>Priority Alert Queue</h3>
            <p className="card-sub">High & critical severity flags requiring action</p>
          </div>
          <button className="btn-secondary" style={{ height: 32, fontSize: 12 }} onClick={() => navigate('/alerts')}>
            View All ({alerts.length})
          </button>
        </div>
        <div className="alert-list">
          {alerts.filter((a) => a.status === 'open').slice(0, 4).map((alt) => (
            <div key={alt.id} className="alert-row">
              <span className={`severity-badge ${alt.severity}`}>{alt.severity}</span>
              <div className="alert-body">
                <div className="alert-head-row">
                  <span className="alert-type">{alt.type}</span>
                  <span className="acct-tag">{alt.account_id}</span>
                </div>
                <div className="alert-msg">{alt.message}</div>
              </div>
              <div className="alert-time">
                <Clock size={11} />
                {new Date(alt.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
              </div>
              <button className="btn-primary" style={{ height: 30, fontSize: 12 }} onClick={() => navigate(`/explain?id=${alt.account_id}`)}>
                Investigate
              </button>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
