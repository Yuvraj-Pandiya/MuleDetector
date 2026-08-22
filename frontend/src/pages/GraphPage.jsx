import React, { useState, useEffect, useRef } from 'react';
import { useSearchParams, useNavigate } from 'react-router-dom';
import ForceGraph2D from 'react-force-graph-2d';
import {
  Share2, ArrowLeft, RefreshCw, ZoomIn, ZoomOut, Maximize2,
  BrainCircuit, ShieldAlert, ArrowRight, Activity,
} from 'lucide-react';
import { getTransactionGraph, getRiskScores } from '../api/client';
import './GraphPage.css';

const NODE_COLORS = {
  target: '#14B8A6',
  flagged: '#EF4444',
  external: '#F59E0B',
  normal: '#3B82F6',
};

export default function GraphPage() {
  const [searchParams] = useSearchParams();
  const accountId = searchParams.get('id') || 'ACC-001001';

  const [graphData, setGraphData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [selectedNode, setSelectedNode] = useState(null);
  const [accountList, setAccountList] = useState([]);

  const fgRef = useRef();
  const containerRef = useRef();
  const navigate = useNavigate();

  useEffect(() => {
    async function loadData() {
      setLoading(true);
      try {
        const [gData, accs] = await Promise.all([
          getTransactionGraph(accountId),
          getRiskScores(),
        ]);
        setGraphData(gData);
        setAccountList(accs);
        const centerNode = gData.nodes.find((n) => n.id === accountId);
        setSelectedNode(centerNode || gData.nodes[0]);
      } catch (err) {
        console.error('Error fetching graph:', err);
      } finally {
        setLoading(false);
      }
    }
    loadData();
  }, [accountId]);

  const handleNodeClick = (node) => {
    setSelectedNode(node);
    if (fgRef.current) {
      fgRef.current.centerAt(node.x, node.y, 400);
      fgRef.current.zoom(2.5, 400);
    }
  };

  const handleZoomIn = () => fgRef.current?.zoom(fgRef.current.zoom() * 1.3, 300);
  const handleZoomOut = () => fgRef.current?.zoom(fgRef.current.zoom() / 1.3, 300);
  const handleResetZoom = () => {
    fgRef.current?.zoomToFit(400, 50);
  };

  if (loading || !graphData) {
    return <div className="loading-state">Rendering multi-hop transaction graph topology…</div>;
  }

  return (
    <div className="graph-page animate-fade-in">
      {/* Header Bar */}
      <div className="graph-header-bar">
        <div className="graph-title-group">
          <button className="btn-secondary" style={{ height: 32, padding: '0 10px' }} onClick={() => navigate('/accounts')}>
            <ArrowLeft size={14} /> Back
          </button>
          <div>
            <h2>Mule Ring Graph Topology — {accountId}</h2>
            <p className="subtext">Interactive multi-hop neighborhood • Fan-in, Fan-out & Cycle detection</p>
          </div>
        </div>

        <div className="graph-header-actions">
          <div className="legend-pills">
            <span className="pill"><span className="dot target" /> Target</span>
            <span className="pill"><span className="dot flagged" /> Flagged Mule</span>
            <span className="pill"><span className="dot external" /> External</span>
            <span className="pill"><span className="dot normal" /> Normal</span>
          </div>

          <select
            value={accountId}
            onChange={(e) => navigate(`/graph?id=${e.target.value}`)}
            className="acct-select"
            id="graph-account-select"
          >
            {accountList.map((acc) => (
              <option key={acc.id} value={acc.id}>
                {acc.id} ({acc.name})
              </option>
            ))}
          </select>
        </div>
      </div>

      {/* Main Graph Grid */}
      <div className="graph-container-grid">
        {/* Force Directed Canvas */}
        <div className="canvas-wrapper" ref={containerRef}>
          <ForceGraph2D
            ref={fgRef}
            graphData={graphData}
            nodeLabel={(node) => `${node.id} (${node.group}) — Risk: ${node.risk}`}
            nodeColor={(node) => NODE_COLORS[node.group] || '#ffffff'}
            nodeRelSize={7}
            linkColor={(link) => (link.type === 'cycle' ? '#EF4444' : link.type === 'inflow' ? '#10B981' : '#3B82F6')}
            linkWidth={(link) => (link.type === 'cycle' ? 2.5 : 1.5)}
            linkDirectionalParticles={(link) => (link.type === 'cycle' ? 4 : 2)}
            linkDirectionalParticleSpeed={(link) => (link.type === 'cycle' ? 0.015 : 0.008)}
            linkDirectionalParticleWidth={2.5}
            onNodeClick={handleNodeClick}
            backgroundColor="#0d0d0d"
            nodeCanvasObject={(node, ctx, globalScale) => {
              const label = node.label;
              const fontSize = 11 / globalScale;
              ctx.font = `${fontSize}px JetBrains Mono, monospace`;
              const r = node.group === 'target' ? 8 : 6;

              // Outer halo for target & flagged
              if (node.group === 'target' || node.group === 'flagged') {
                ctx.beginPath();
                ctx.arc(node.x, node.y, r + 3, 0, 2 * Math.PI, false);
                ctx.fillStyle = node.group === 'target' ? 'rgba(20, 184, 166, 0.25)' : 'rgba(239, 68, 68, 0.25)';
                ctx.fill();
              }

              // Node circle
              ctx.beginPath();
              ctx.arc(node.x, node.y, r, 0, 2 * Math.PI, false);
              ctx.fillStyle = NODE_COLORS[node.group] || '#ffffff';
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

        {/* Node Inspector Panel */}
        <div className="inspector-panel">
          {selectedNode ? (
            <div className="inspector-content">
              <div className="inspector-header">
                <ShieldAlert size={20} className="text-danger" />
                <div>
                  <h3 className="inspect-id">{selectedNode.id}</h3>
                  <span className={`severity-badge ${selectedNode.risk > 70 ? 'critical' : selectedNode.risk > 40 ? 'medium' : 'low'}`}>
                    {selectedNode.group.toUpperCase()}
                  </span>
                </div>
              </div>

              <div className="inspect-risk-box">
                <span className="inspect-label">Node Risk Score</span>
                <span className="risk-num">{selectedNode.risk} / 100</span>
                <div className="score-bar-bg" style={{ height: 6 }}>
                  <div
                    className={`score-bar-fill ${selectedNode.risk > 70 ? 'critical' : 'medium'}`}
                    style={{ width: `${selectedNode.risk}%` }}
                  />
                </div>
              </div>

              <div className="inspect-details">
                <h4>Neighborhood Statistics</h4>
                <div className="inspect-group">
                  <span>Category:</span>
                  <span className="font-mono text-ink">{selectedNode.group}</span>
                </div>
                <div className="inspect-group">
                  <span>Connected Edges:</span>
                  <span className="font-mono text-ink">
                    {graphData.links.filter((l) => l.source.id === selectedNode.id || l.target.id === selectedNode.id || l.source === selectedNode.id || l.target === selectedNode.id).length}
                  </span>
                </div>
              </div>

              <div className="inspect-actions">
                <button
                  className="btn-primary"
                  style={{ width: '100%', justifyContent: 'center' }}
                  onClick={() => navigate(`/explain?id=${selectedNode.id}`)}
                >
                  <BrainCircuit size={15} /> Explain Account Risk
                </button>
              </div>
            </div>
          ) : (
            <div className="inspector-empty">
              <Share2 size={32} />
              <p>Click any node on the graph to inspect detailed transaction topology</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
