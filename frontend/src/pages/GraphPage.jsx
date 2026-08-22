import React, { useState, useEffect, useRef } from 'react';
import { useSearchParams, useNavigate } from 'react-router-dom';
import ForceGraph2D from 'react-force-graph-2d';
import {
  Share2, ArrowLeft, RefreshCw, ZoomIn, ZoomOut, Maximize2,
  BrainCircuit, ShieldAlert, ArrowUpRight, ArrowDownLeft, Search, Filter,
  Activity, Layers, Clock, X, CheckCircle, Info, DollarSign, Calendar, Network
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
  const [activeInspectorTab, setActiveInspectorTab] = useState('overview');

  // Filter States
  const [searchQuery, setSearchQuery] = useState('');
  const [riskTierFilter, setRiskTierFilter] = useState('ALL');
  const [directionFilter, setDirectionFilter] = useState('ALL');
  const [minAmountFilter, setMinAmountFilter] = useState('');
  const [maxAmountFilter, setMaxAmountFilter] = useState('');
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
      if (directionFilter !== 'ALL') params.direction = directionFilter;
      if (minAmountFilter) params.min_amount = Number(minAmountFilter);
      if (maxAmountFilter) params.max_amount = Number(maxAmountFilter);
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
  }, [accountId, riskTierFilter, directionFilter, minAmountFilter, maxAmountFilter, startDateFilter, endDateFilter]);

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

  const incomingNeighbors = summary.incoming_neighbors || [];
  const outgoingNeighbors = summary.outgoing_neighbors || [];
  const suspiciousConnected = summary.suspicious_connected_accounts || [];
  const shortPaths = summary.short_transaction_paths || [];
  const connectedComponentsCount = summary.connected_components_count ?? 1;

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
            <p className="subtext">Multi-hop actual transaction graph • Risk-weighted node centralities and flow edges</p>
          </div>
        </div>

        <div className="graph-header-actions flex-align gap-sm">
          {/* Visual Legend */}
          <div className="legend-pills">
            <span className="pill"><span className="dot target" /> Selected Account</span>
            <span className="pill"><span className="dot critical" /> High Risk / Mule</span>
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

        {/* Direction Filter */}
        <div className="filter-item">
          <label>Direction:</label>
          <select value={directionFilter} onChange={(e) => setDirectionFilter(e.target.value)}>
            <option value="ALL">All Directions</option>
            <option value="INCOMING">INCOMING Only</option>
            <option value="OUTGOING">OUTGOING Only</option>
          </select>
        </div>

        {/* Risk Filter */}
        <div className="filter-item">
          <label>Risk Tier:</label>
          <select value={riskTierFilter} onChange={(e) => setRiskTierFilter(e.target.value)}>
            <option value="ALL">All Risk Tiers</option>
            <option value="CRITICAL">Critical</option>
            <option value="HIGH">High</option>
            <option value="MEDIUM">Medium</option>
            <option value="LOW">Low</option>
          </select>
        </div>

        {/* Amount Range Filter */}
        <div className="filter-item">
          <label>Amount ($):</label>
          <input
            type="number"
            placeholder="Min"
            value={minAmountFilter}
            onChange={(e) => setMinAmountFilter(e.target.value)}
            className="num-input"
          />
          <span>-</span>
          <input
            type="number"
            placeholder="Max"
            value={maxAmountFilter}
            onChange={(e) => setMaxAmountFilter(e.target.value)}
            className="num-input"
          />
        </div>

        {/* Date Range Filter */}
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
            setDirectionFilter('ALL');
            setRiskTierFilter('ALL');
            setMinAmountFilter('');
            setMaxAmountFilter('');
            setStartDateFilter('');
            setEndDateFilter('');
          }}
        >
          Reset Filters
        </button>
      </div>

      {/* Main Graph Layout Grid */}
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
              
              const isTarget = node.id === accountId || node.account_id === accountId || node.group === 'target';
              const isHighRisk = (node.risk_score ?? 0) >= 70 || node.risk_tier === 'CRITICAL' || node.risk_tier === 'HIGH';
              const isSelected = selectedNode && (node.id === selectedNode.id || node.account_id === selectedNode.account_id);

              const r = isTarget ? 10 : (isHighRisk ? 8 : 6);
              const colKey = isTarget ? 'target' : (node.risk_tier || node.group || '').toLowerCase();
              const fillColor = NODE_COLORS[colKey] || '#3B82F6';

              // Visual Indication 1: Selected / Target Account glowing halo (Teal)
              if (isTarget || isSelected) {
                ctx.beginPath();
                ctx.arc(node.x, node.y, r + 6, 0, 2 * Math.PI, false);
                ctx.fillStyle = 'rgba(20, 184, 166, 0.45)';
                ctx.fill();

                ctx.beginPath();
                ctx.arc(node.x, node.y, r + 3, 0, 2 * Math.PI, false);
                ctx.strokeStyle = '#14B8A6';
                ctx.lineWidth = 2 / globalScale;
                ctx.stroke();
              }

              // Visual Indication 2: High-Risk Connected Accounts glowing halo (Red / Orange)
              if (isHighRisk && !isTarget) {
                ctx.beginPath();
                ctx.arc(node.x, node.y, r + 5, 0, 2 * Math.PI, false);
                ctx.fillStyle = 'rgba(239, 68, 68, 0.35)';
                ctx.fill();

                ctx.beginPath();
                ctx.arc(node.x, node.y, r + 2, 0, 2 * Math.PI, false);
                ctx.strokeStyle = '#EF4444';
                ctx.lineWidth = 1.5 / globalScale;
                ctx.stroke();
              }

              // Core Node Circle
              ctx.beginPath();
              ctx.arc(node.x, node.y, r, 0, 2 * Math.PI, false);
              ctx.fillStyle = fillColor;
              ctx.fill();

              // Text Label
              ctx.textAlign = 'center';
              ctx.textBaseline = 'middle';
              ctx.fillStyle = isTarget ? '#14B8A6' : (isHighRisk ? '#EF4444' : '#f4f4f6');
              ctx.fillText(label, node.x, node.y + r + 9 / globalScale);
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
              {/* Header */}
              <div className="inspector-header">
                <ShieldAlert size={20} className="text-danger" />
                <div>
                  <h3 className="inspect-id">{selectedNode.account_id || selectedNode.id}</h3>
                  <span className={`severity-badge ${(selectedNode.risk_tier || selectedNode.group || 'medium').toLowerCase()}`}>
                    {(selectedNode.risk_tier || selectedNode.group || 'NORMAL').toUpperCase()}
                  </span>
                </div>
              </div>

              {/* Inspector Navigation Tabs */}
              <div className="inspector-tabs-nav margin-top-xs">
                <button
                  className={`tab-btn ${activeInspectorTab === 'overview' ? 'active' : ''}`}
                  onClick={() => setActiveInspectorTab('overview')}
                >
                  Overview
                </button>
                <button
                  className={`tab-btn ${activeInspectorTab === 'incoming' ? 'active' : ''}`}
                  onClick={() => setActiveInspectorTab('incoming')}
                >
                  Incoming ({incomingNeighbors.length})
                </button>
                <button
                  className={`tab-btn ${activeInspectorTab === 'outgoing' ? 'active' : ''}`}
                  onClick={() => setActiveInspectorTab('outgoing')}
                >
                  Outgoing ({outgoingNeighbors.length})
                </button>
                <button
                  className={`tab-btn ${activeInspectorTab === 'suspicious' ? 'active' : ''}`}
                  onClick={() => setActiveInspectorTab('suspicious')}
                >
                  Suspicious ({suspiciousConnected.length})
                </button>
              </div>

              {/* Tab 1: Overview */}
              {activeInspectorTab === 'overview' && (
                <div className="tab-content margin-top-xs">
                  <div className="inspect-risk-box">
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

                  <div className="inspect-metrics-grid margin-top-xs">
                    <div className="m-box"><span className="m-lbl">Anomaly Score</span><span className="m-val font-mono">{selectedNode.anomaly_score ?? 0.1}</span></div>
                    <div className="m-box"><span className="m-lbl">Network Risk</span><span className="m-val font-mono">{selectedNode.network_risk ?? 15}</span></div>
                  </div>

                  <div className="topology-summary margin-top-xs">
                    <h4>Connected Components & Topology</h4>
                    <div className="inspect-group"><span>Connected Components:</span><span className="font-mono text-ink font-bold">{connectedComponentsCount}</span></div>
                    <div className="inspect-group"><span>Short Paths & Cycles:</span><span className="font-mono text-warning font-bold">{shortPaths.length}</span></div>
                  </div>

                  {shortPaths.length > 0 && (
                    <div className="short-paths-box margin-top-xs">
                      <span className="t-label">Short Transaction Paths:</span>
                      <ul className="paths-list">
                        {shortPaths.map((p, i) => (
                          <li key={i} className="path-item font-mono text-xs">{typeof p === 'string' ? p : `${p.source} → ${p.target}`}</li>
                        ))}
                      </ul>
                    </div>
                  )}
                </div>
              )}

              {/* Tab 2: Incoming Neighbors */}
              {activeInspectorTab === 'incoming' && (
                <div className="tab-content margin-top-xs">
                  <h4>Incoming Sender Neighbors</h4>
                  {incomingNeighbors.length === 0 ? (
                    <p className="text-xs text-stone margin-top-xs">No incoming senders match current filters.</p>
                  ) : (
                    <div className="neighbor-list margin-top-xs">
                      {incomingNeighbors.map((inc, i) => {
                        const acct = typeof inc === 'string' ? inc : inc.account_id;
                        const amt = typeof inc === 'object' ? inc.amount : null;
                        const ts = typeof inc === 'object' ? inc.timestamp : null;
                        return (
                          <div key={i} className="neighbor-card flex-between" onClick={() => navigate(`/graph?id=${acct}`)}>
                            <div>
                              <span className="font-mono font-bold text-ink">{acct}</span>
                              {ts && <div className="text-xs text-stone font-mono">{new Date(ts).toLocaleString()}</div>}
                            </div>
                            {amt && <span className="font-mono text-success font-bold">${amt.toLocaleString()}</span>}
                          </div>
                        );
                      })}
                    </div>
                  )}
                </div>
              )}

              {/* Tab 3: Outgoing Neighbors */}
              {activeInspectorTab === 'outgoing' && (
                <div className="tab-content margin-top-xs">
                  <h4>Outgoing Receiver Neighbors</h4>
                  {outgoingNeighbors.length === 0 ? (
                    <p className="text-xs text-stone margin-top-xs">No outgoing receivers match current filters.</p>
                  ) : (
                    <div className="neighbor-list margin-top-xs">
                      {outgoingNeighbors.map((out, i) => {
                        const acct = typeof out === 'string' ? out : out.account_id;
                        const amt = typeof out === 'object' ? out.amount : null;
                        const ts = typeof out === 'object' ? out.timestamp : null;
                        return (
                          <div key={i} className="neighbor-card flex-between" onClick={() => navigate(`/graph?id=${acct}`)}>
                            <div>
                              <span className="font-mono font-bold text-ink">{acct}</span>
                              {ts && <div className="text-xs text-stone font-mono">{new Date(ts).toLocaleString()}</div>}
                            </div>
                            {amt && <span className="font-mono text-danger font-bold">${amt.toLocaleString()}</span>}
                          </div>
                        );
                      })}
                    </div>
                  )}
                </div>
              )}

              {/* Tab 4: Suspicious Connected Accounts */}
              {activeInspectorTab === 'suspicious' && (
                <div className="tab-content margin-top-xs">
                  <h4>Flagged High-Risk Connected Accounts</h4>
                  {suspiciousConnected.length === 0 ? (
                    <p className="text-xs text-stone margin-top-xs">No high-risk accounts connected to this entity.</p>
                  ) : (
                    <div className="neighbor-list margin-top-xs">
                      {suspiciousConnected.map((sNode, i) => {
                        const acct = typeof sNode === 'string' ? sNode : sNode.account_id;
                        const sc = typeof sNode === 'object' ? sNode.risk_score : 85;
                        const tier = typeof sNode === 'object' ? sNode.risk_tier : 'CRITICAL';
                        return (
                          <div key={i} className="neighbor-card flex-between" onClick={() => navigate(`/graph?id=${acct}`)}>
                            <span className="font-mono font-bold text-ink">{acct}</span>
                            <span className={`severity-badge ${(tier || 'critical').toLowerCase()}`}>{sc} Score</span>
                          </div>
                        );
                      })}
                    </div>
                  )}
                </div>
              )}

              {/* Action Button */}
              <div className="inspect-actions margin-top-md">
                <button
                  className="btn-primary"
                  style={{ width: '100%', justifyContent: 'center' }}
                  onClick={() => navigate(`/explain?id=${selectedNode.account_id || selectedNode.id}`)}
                >
                  <BrainCircuit size={15} /> Open Full Account Investigation
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
