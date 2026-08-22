import React, { useState, useEffect, useRef } from 'react';
import { useSearchParams, useNavigate } from 'react-router-dom';
import ForceGraph2D from 'react-force-graph-2d';
import {
  Share2, ArrowLeft, RefreshCw, ZoomIn, ZoomOut, Maximize2,
  BrainCircuit, ShieldAlert, ArrowUpRight, ArrowDownLeft, Search, Filter,
  Activity, Layers, Clock, X, CheckCircle, Info
} from 'lucide-react';
import { getTransactionGraph, getRiskScores } from '../api/client';
import './GraphPage.css';

const NODE_COLORS = {
  target: '#14B8A6',
  critical: '#EF4444',
  high: '#F97316',
  medium: '#F59E0B',
  low: '#10B981',
  flagged: '#EF4444',
  external: '#6366F1',
  normal: '#3B82F6',
};

export default function GraphPage() {
  const [searchParams] = useSearchParams();
  const accountId = searchParams.get('id') || 'ACC-001001';

  const [graphData, setGraphData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [selectedNode, setSelectedNode] = useState(null);
  const [selectedEdge, setSelectedEdge] = useState(null);
  const [accountList, setAccountList] = useState([]);

  // Filter States
  const [searchQuery, setSearchQuery] = useState('');
  const [riskTierFilter, setRiskTierFilter] = useState('ALL');
  const [minAmountFilter, setMinAmountFilter] = useState('');
  const [startDateFilter, setStartDateFilter] = useState('');
  const [endDateFilter, setEndDateFilter] = useState('');

  const fgRef = useRef();
  const containerRef = useRef();
  const navigate = useNavigate();

  const loadData = async () => {
    setLoading(true);
    try {
      const params = {};
      if (riskTierFilter !== 'ALL') params.risk_tier = riskTierFilter;
      if (minAmountFilter) params.min_amount = Number(minAmountFilter);
      if (startDateFilter) params.start_date = startDateFilter;
      if (endDateFilter) params.end_date = endDateFilter;

      const [gData, accsRes] = await Promise.all([
        getTransactionGraph(accountId, params),
        getRiskScores({ page_size: 100 }).catch(() => ({ accounts: [] })),
      ]);

      const accs = accsRes.accounts || (Array.isArray(accsRes) ? accsRes : []);
      setGraphData(gData);
      setAccountList(accs);

      const target = (gData.nodes || []).find((n) => (n.account_id || n.id) === accountId);
      setSelectedNode(target || (gData.nodes || [])[0] || null);
    } catch (err) {
      console.error('Error fetching graph telemetry:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, [accountId, riskTierFilter, minAmountFilter, startDateFilter, endDateFilter]);

  const handleNodeClick = (node) => {
    setSelectedNode(node);
    setSelectedEdge(null);
    if (fgRef.current) {
      fgRef.current.centerAt(node.x, node.y, 400);
      fgRef.current.zoom(2.5, 400);
    }
  };

  const handleLinkClick = (link) => {
    setSelectedEdge(link);
  };

  const handleSearchSubmit = (e) => {
    e.preventDefault();
    if (!searchQuery.trim()) return;
    const target = (graphData?.nodes || []).find(
      (n) => (n.account_id || n.id).toLowerCase().includes(searchQuery.toLowerCase().trim())
    );
    if (target) {
      handleNodeClick(target);
    } else {
      navigate(`/graph?id=${searchQuery.trim()}`);
    }
  };

  const handleZoomIn = () => fgRef.current?.zoom(fgRef.current.zoom() * 1.3, 300);
  const handleZoomOut = () => fgRef.current?.zoom(fgRef.current.zoom() / 1.3, 300);
  const handleResetZoom = () => fgRef.current?.zoomToFit(400, 50);

  if (loading || !graphData) {
    return <div className="loading-state">Rendering multi-hop transaction network topology…</div>;
  }

  const summary = graphData.summary || {};
  const nodes = graphData.nodes || [];
  const links = graphData.links || graphData.edges || [];

  return (
    <div className="graph-page animate-fade-in">
      {/* Header Bar */}
      <div className="graph-header-bar flex-between">
        <div className="graph-title-group flex-align gap-xs">
          <button className="btn-secondary sm" onClick={() => navigate('/accounts')}>
            <ArrowLeft size={14} /> Back
          </button>
          <div>
            <h2>Transaction Network Topology — {accountId}</h2>
            <p className="subtext">Multi-hop graph topology • Risk-weighted node centralities and transaction edges</p>
          </div>
        </div>

        <div className="graph-header-actions flex-align gap-sm">
          {/* Legend */}
          <div className="legend-pills">
            <span className="pill"><span className="dot target" /> Target</span>
            <span className="pill"><span className="dot critical" /> Critical</span>
            <span className="pill"><span className="dot high" /> High</span>
            <span className="pill"><span className="dot medium" /> Medium</span>
            <span className="pill"><span className="dot low" /> Low</span>
          </div>

          {/* Account Selector */}
          <select
            value={accountId}
            onChange={(e) => navigate(`/graph?id=${e.target.value}`)}
            className="acct-select"
            id="graph-account-select"
          >
            {accountList.map((acc) => (
              <option key={acc.account_id || acc.id} value={acc.account_id || acc.id}>
                {acc.account_id || acc.id} ({acc.risk_tier?.toUpperCase() || 'SCORE'} - {acc.risk_score})
              </option>
            ))}
          </select>
        </div>
      </div>

      {/* Interactive Filter Toolbar */}
      <div className="graph-filter-toolbar margin-top-xs">
        {/* Search */}
        <form onSubmit={handleSearchSubmit} className="search-box">
          <Search size={14} className="search-icon" />
          <input
            type="text"
            placeholder="Search account ID..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
          />
        </form>

        {/* Risk Filter */}
        <div className="filter-item">
          <label>Risk Tier:</label>
          <select value={riskTierFilter} onChange={(e) => setRiskTierFilter(e.target.value)}>
            <option value="ALL">All Tiers</option>
            <option value="CRITICAL">Critical</option>
            <option value="HIGH">High</option>
            <option value="MEDIUM">Medium</option>
            <option value="LOW">Low</option>
          </select>
        </div>

        {/* Min Amount */}
        <div className="filter-item">
          <label>Min Amount ($):</label>
          <input
            type="number"
            placeholder="0"
            value={minAmountFilter}
            onChange={(e) => setMinAmountFilter(e.target.value)}
            className="num-input"
          />
        </div>

        {/* Date Range */}
        <div className="filter-item">
          <label>Date Range:</label>
          <input
            type="date"
            value={startDateFilter}
            onChange={(e) => setStartDateFilter(e.target.value)}
            className="date-input"
          />
          <span>to</span>
          <input
            type="date"
            value={endDateFilter}
            onChange={(e) => setEndDateFilter(e.target.value)}
            className="date-input"
          />
        </div>

        <button
          type="button"
          className="btn-secondary sm"
          onClick={() => {
            setSearchQuery('');
            setRiskTierFilter('ALL');
            setMinAmountFilter('');
            setStartDateFilter('');
            setEndDateFilter('');
          }}
        >
          Reset Filters
        </button>
      </div>

      {/* Main Graph Grid */}
      <div className="graph-container-grid margin-top-xs">
        {/* Force Directed Canvas */}
        <div className="canvas-wrapper" ref={containerRef}>
          <ForceGraph2D
            ref={fgRef}
            graphData={{ nodes, links }}
            nodeLabel={(node) => `${node.account_id || node.id} (${node.risk_tier || node.group}) — Score: ${node.risk_score ?? node.risk}`}
            nodeColor={(node) => NODE_COLORS[node.group] || NODE_COLORS[(node.risk_tier || '').toLowerCase()] || '#3B82F6'}
            nodeRelSize={7}
            linkColor={(link) => (link.type === 'cycle' ? '#EF4444' : link.type === 'inflow' ? '#10B981' : '#3B82F6')}
            linkWidth={(link) => (link.type === 'cycle' ? 2.5 : 1.5)}
            linkDirectionalParticles={(link) => (link.type === 'cycle' ? 4 : 2)}
            linkDirectionalParticleSpeed={(link) => (link.type === 'cycle' ? 0.015 : 0.008)}
            linkDirectionalParticleWidth={2.5}
            onNodeClick={handleNodeClick}
            onLinkClick={handleLinkClick}
            backgroundColor="#0d0d0d"
            nodeCanvasObject={(node, ctx, globalScale) => {
              const label = node.account_id || node.id || node.label;
              const fontSize = 11 / globalScale;
              ctx.font = `${fontSize}px JetBrains Mono, monospace`;
              const r = node.group === 'target' ? 9 : 7;
              const colKey = node.group === 'target' ? 'target' : (node.risk_tier || node.group || '').toLowerCase();
              const fillColor = NODE_COLORS[colKey] || '#3B82F6';

              // Outer halo for selected or high risk nodes
              if (selectedNode && (node.id === selectedNode.id || node.account_id === selectedNode.account_id)) {
                ctx.beginPath();
                ctx.arc(node.x, node.y, r + 4, 0, 2 * Math.PI, false);
                ctx.fillStyle = 'rgba(20, 184, 166, 0.4)';
                ctx.fill();
              }

              // Node circle
              ctx.beginPath();
              ctx.arc(node.x, node.y, r, 0, 2 * Math.PI, false);
              ctx.fillStyle = fillColor;
              ctx.fill();

              // Text label below node
              ctx.textAlign = 'center';
              ctx.textBaseline = 'middle';
              ctx.fillStyle = '#f4f4f6';
              ctx.fillText(label, node.x, node.y + r + 8 / globalScale);
            }}
          />

          {/* Floating Canvas Controls */}
          <div className="floating-controls">
            <button className="ctrl-btn" title="Zoom In" onClick={handleZoomIn}><ZoomIn size={16} /></button>
            <button className="ctrl-btn" title="Zoom Out" onClick={handleZoomOut}><ZoomOut size={16} /></button>
            <button className="ctrl-btn" title="Fit to Screen" onClick={handleResetZoom}><Maximize2 size={16} /></button>
          </div>
        </div>

        {/* Node & Edge Inspector Panel */}
        <div className="inspector-panel">
          {/* Edge Inspector Popup */}
          {selectedEdge && (
            <div className="edge-inspector-box">
              <div className="flex-between border-bottom padding-bottom-xs">
                <span className="font-mono font-bold text-ink">Edge / Transaction Inspector</span>
                <button className="close-btn" onClick={() => setSelectedEdge(null)}><X size={14} /></button>
              </div>
              <div className="inspect-details margin-top-xs">
                <div className="inspect-group"><span>Txn ID:</span><span className="font-mono font-semibold text-ink">{selectedEdge.transaction_id || 'N/A'}</span></div>
                <div className="inspect-group"><span>Source:</span><span className="font-mono text-ink">{selectedEdge.source?.id || selectedEdge.source}</span></div>
                <div className="inspect-group"><span>Target:</span><span className="font-mono text-ink">{selectedEdge.target?.id || selectedEdge.target}</span></div>
                <div className="inspect-group"><span>Amount ($):</span><span className="font-mono text-success font-bold">${(selectedEdge.amount || selectedEdge.value || 0).toLocaleString()}</span></div>
                <div className="inspect-group"><span>Direction:</span><span className="font-mono text-primary">{selectedEdge.direction || selectedEdge.type || 'TRANSFER'}</span></div>
                <div className="inspect-group"><span>Timestamp:</span><span className="font-mono text-stone text-xs">{selectedEdge.timestamp ? new Date(selectedEdge.timestamp).toLocaleString() : 'N/A'}</span></div>
              </div>
            </div>
          )}

          {/* Node Inspector Content */}
          {selectedNode ? (
            <div className="inspector-content">
              <div className="inspector-header">
                <ShieldAlert size={20} className="text-danger" />
                <div>
                  <h3 className="inspect-id">{selectedNode.account_id || selectedNode.id}</h3>
                  <span className={`severity-badge ${(selectedNode.risk_tier || selectedNode.group || 'medium').toLowerCase()}`}>
                    {(selectedNode.risk_tier || selectedNode.group || 'NORMAL').toUpperCase()}
                  </span>
                </div>
              </div>

              {/* Multi-Model Scores Box */}
              <div className="inspect-risk-box margin-top-xs">
                <div className="flex-between">
                  <span className="inspect-label">Overall Risk Score</span>
                  <span className="risk-num font-mono">{selectedNode.risk_score ?? selectedNode.risk ?? 0} / 100</span>
                </div>
                <div className="score-bar-bg" style={{ height: 6 }}>
                  <div
                    className={`score-bar-fill ${(selectedNode.risk_score ?? selectedNode.risk ?? 0) > 70 ? 'critical' : 'medium'}`}
                    style={{ width: `${selectedNode.risk_score ?? selectedNode.risk ?? 0}%` }}
                  />
                </div>
              </div>

              {/* Node Attribute Metrics */}
              <div className="inspect-metrics-grid margin-top-xs">
                <div className="m-box"><span className="m-lbl">Anomaly Score</span><span className="m-val font-mono">{selectedNode.anomaly_score ?? 0.1}</span></div>
                <div className="m-box"><span className="m-lbl">Network Risk</span><span className="m-val font-mono">{selectedNode.network_risk ?? 15}</span></div>
              </div>

              {/* Topology Summary Panel */}
              <div className="topology-summary margin-top-sm">
                <h4>Network Topology Summary</h4>
                <div className="inspect-group">
                  <span>Suspicious Connected:</span>
                  <span className="font-mono text-danger font-bold">
                    {(summary.suspicious_connected_accounts || []).length}
                  </span>
                </div>
                <div className="inspect-group">
                  <span>Incoming Neighbors:</span>
                  <span className="font-mono text-success font-bold">
                    {(summary.incoming_neighbors || []).length}
                  </span>
                </div>
                <div className="inspect-group">
                  <span>Outgoing Neighbors:</span>
                  <span className="font-mono text-warning font-bold">
                    {(summary.outgoing_neighbors || []).length}
                  </span>
                </div>
                <div className="inspect-group">
                  <span>Connected Components:</span>
                  <span className="font-mono text-ink">{summary.connected_components_count ?? 1}</span>
                </div>

                {summary.short_transaction_paths && summary.short_transaction_paths.length > 0 && (
                  <div className="short-paths-box margin-top-xs">
                    <span className="t-label">Short Transaction Paths & Cycles:</span>
                    <ul className="paths-list">
                      {summary.short_transaction_paths.map((p, i) => (
                        <li key={i} className="path-item font-mono text-xs">{p}</li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>

              {/* Action Buttons */}
              <div className="inspect-actions margin-top-md">
                <button
                  className="btn-primary"
                  style={{ width: '100%', justifyContent: 'center' }}
                  onClick={() => navigate(`/explain?id=${selectedNode.account_id || selectedNode.id}`)}
                >
                  <BrainCircuit size={15} /> Open Account Investigation
                </button>
              </div>
            </div>
          ) : (
            <div className="inspector-empty">
              <Share2 size={32} />
              <p>Click any node or edge on the graph to inspect detailed transaction telemetry</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

