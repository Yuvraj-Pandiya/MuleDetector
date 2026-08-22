import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Play, Pause, RefreshCw, Zap, ShieldAlert,
  ArrowRight, Activity, Radio, CheckCircle2,
} from 'lucide-react';
import './SimulationPage.css';

const SIM_NAMES = [
  'Apex Trading LLC', 'Nova Payments', 'Cascade Fin', 'Quantum Pay',
  'Stellar Remit', 'Vortex Cap', 'Pulse Wire', 'Cobalt Bank',
];

export default function SimulationPage() {
  const [isRunning, setIsRunning] = useState(true);
  const [stream, setStream] = useState([]);
  const [stats, setStats] = useState({ totalScanned: 1420, mulesIntercepted: 18, totalVolume: 4250000 });
  const navigate = useNavigate();

  useEffect(() => {
    if (!isRunning) return;

    const interval = setInterval(() => {
      const isMule = Math.random() < 0.18;
      const amount = Math.floor(500 + Math.random() * 45500);
      const sender = `ACC-${Math.floor(1000 + Math.random() * 9000)}`;
      const receiver = `ACC-${Math.floor(1000 + Math.random() * 9000)}`;

      const newTxn = {
        id: `TXN-${Math.floor(100000 + Math.random() * 900000)}`,
        timestamp: new Date().toLocaleTimeString(),
        sender,
        receiver,
        amount,
        riskScore: isMule ? Math.floor(75 + Math.random() * 24) : Math.floor(5 + Math.random() * 30),
        isMule,
        reason: isMule ? 'Rapid fan-out pass-through pattern' : 'Normal peer-to-peer transfer',
      };

      setStream((prev) => [newTxn, ...prev.slice(0, 19)]);
      setStats((prev) => ({
        totalScanned: prev.totalScanned + 1,
        mulesIntercepted: prev.mulesIntercepted + (isMule ? 1 : 0),
        totalVolume: prev.totalVolume + amount,
      }));
    }, 1200);

    return () => clearInterval(interval);
  }, [isRunning]);

  return (
    <div className="sim-page animate-fade-in">
      <div className="sim-header-bar">
        <div>
          <div className="sim-live-tag">
            <Radio size={14} className="live-pulse" />
            <span>REAL-TIME STREAMING ENGINE</span>
          </div>
          <h2>Live Mule Detection Simulation</h2>
          <p className="subtext">Simulating live ISO 20022 wire feeds & instant graph neural scoring</p>
        </div>

        <div className="sim-controls">
          <button
            className={`btn-secondary ${isRunning ? 'btn-pause' : 'btn-play'}`}
            onClick={() => setIsRunning(!isRunning)}
            id="sim-toggle-btn"
          >
            {isRunning ? <><Pause size={14} /> Pause Stream</> : <><Play size={14} /> Resume Stream</>}
          </button>
          <button className="btn-secondary" onClick={() => setStream([])}>
            <RefreshCw size={14} /> Clear Log
          </button>
        </div>
      </div>

      {/* KPI Stats */}
      <div className="sim-stats-grid">
        <div className="dash-card">
          <span className="stat-label">Total Transactions Ingested</span>
          <span className="stat-val">{stats.totalScanned.toLocaleString()}</span>
        </div>
        <div className="dash-card">
          <span className="stat-label">Mule Accounts Intercepted</span>
          <span className="stat-val text-danger">{stats.mulesIntercepted}</span>
        </div>
        <div className="dash-card">
          <span className="stat-label">Total Ingestion Volume</span>
          <span className="stat-val">${(stats.totalVolume / 1000000).toFixed(2)}M</span>
        </div>
        <div className="dash-card">
          <span className="stat-label">Stream Latency</span>
          <span className="stat-val text-success">14ms</span>
        </div>
      </div>

      {/* Main Streaming Feed */}
      <div className="sim-main-grid">
        <div className="dash-card sim-feed-card">
          <div className="card-head">
            <h3>Live Wire Transaction Stream</h3>
            <span className="stream-badge">{isRunning ? 'Ingesting (1.2s tick)' : 'Paused'}</span>
          </div>

          <div className="stream-table-wrap">
            <table className="sim-table">
              <thead>
                <tr>
                  <th>Timestamp</th>
                  <th>Txn ID</th>
                  <th>Sender</th>
                  <th>Receiver</th>
                  <th>Amount</th>
                  <th>Risk Score</th>
                  <th>Action</th>
                </tr>
              </thead>
              <tbody>
                {stream.length === 0 ? (
                  <tr>
                    <td colSpan="7" className="sim-empty">Stream ready. Initializing ticks…</td>
                  </tr>
                ) : (
                  stream.map((txn) => (
                    <tr key={txn.id} className={`sim-row ${txn.isMule ? 'mule-flagged' : ''}`}>
                      <td className="font-mono text-stone">{txn.timestamp}</td>
                      <td className="font-mono">{txn.id}</td>
                      <td className="font-mono">{txn.sender}</td>
                      <td className="font-mono">{txn.receiver}</td>
                      <td className="font-mono font-bold">${txn.amount.toLocaleString()}</td>
                      <td>
                        <span className={`severity-badge ${txn.isMule ? 'critical' : 'low'}`}>
                          {txn.riskScore} / 100
                        </span>
                      </td>
                      <td>
                        {txn.isMule ? (
                          <button
                            className="btn-primary"
                            style={{ height: 26, fontSize: 11, padding: '0 8px' }}
                            onClick={() => navigate(`/explain?id=${txn.sender}`)}
                          >
                            <ShieldAlert size={12} /> Inspect Mule
                          </button>
                        ) : (
                          <span className="text-stone" style={{ fontSize: 11 }}>Passed</span>
                        )}
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  );
}
