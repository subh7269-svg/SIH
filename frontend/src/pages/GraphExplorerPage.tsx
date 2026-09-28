import React, { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Link } from 'react-router-dom';
import {
  Network,
  Search,
  Sliders,
  Route,
  ArrowRight,
  ShieldAlert,
  ExternalLink,
  Layers,
  Info
} from 'lucide-react';
import { getGraphOverview, getEntityGraph, getPathGraph } from '../services/api';
import { CytoscapeGraph } from '../components/graph/CytoscapeGraph';
import { GraphNode } from '../types';
import { Badge } from '../components/common/Badge';

export const GraphExplorerPage: React.FC = () => {
  const [focalInput, setFocalInput] = useState('');
  const [activeFocalId, setActiveFocalId] = useState<string | null>(null);
  const [kHop, setKHop] = useState<number>(2);

  // Path finder state
  const [pathSource, setPathSource] = useState('');
  const [pathTarget, setPathTarget] = useState('');
  const [isPathMode, setIsPathMode] = useState(false);

  const [selectedNode, setSelectedNode] = useState<GraphNode | null>(null);

  // Query graph
  const { data: graphData, isLoading, refetch } = useQuery({
    queryKey: ['graph-view', activeFocalId, kHop, isPathMode, pathSource, pathTarget],
    queryFn: () => {
      if (isPathMode && pathSource && pathTarget) {
        return getPathGraph(pathSource.trim(), pathTarget.trim());
      }
      if (activeFocalId) {
        return getEntityGraph(activeFocalId.trim(), kHop);
      }
      return getGraphOverview(80);
    },
  });

  const handleFocusSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (focalInput.trim()) {
      setIsPathMode(false);
      setActiveFocalId(focalInput.trim());
    }
  };

  const handlePathSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (pathSource.trim() && pathTarget.trim()) {
      setIsPathMode(true);
      setActiveFocalId(null);
    }
  };

  const handleResetToGlobal = () => {
    setActiveFocalId(null);
    setIsPathMode(false);
    setFocalInput('');
    setPathSource('');
    setPathTarget('');
  };

  return (
    <div className="space-y-6 font-mono">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-cyber-border pb-4">
        <div>
          <h1 className="text-xl font-bold text-slate-100 flex items-center gap-2">
            <Network className="w-5 h-5 text-cyber-emerald" />
            <span>INTERACTIVE ENTITY LINK ANALYSIS WORKSPACE</span>
          </h1>
          <p className="text-xs text-slate-400 mt-1">
            Visual graph exploration linking Bitcoin Wallets, Transactions, Relay IPs, ASNs, and Jurisdictions.
          </p>
        </div>

        {/* Live Graph Status Badges */}
        {graphData && (
          <div className="flex items-center gap-2 text-xs">
            <span className="px-2.5 py-1 rounded bg-slate-900 border border-slate-700 text-slate-300">
              Nodes: <strong className="text-cyber-emerald">{graphData.node_count}</strong>
            </span>
            <span className="px-2.5 py-1 rounded bg-slate-900 border border-slate-700 text-slate-300">
              Edges: <strong className="text-cyber-cyan">{graphData.edge_count}</strong>
            </span>
            {activeFocalId && (
              <span className="px-2.5 py-1 rounded bg-cyber-emerald/10 border border-cyber-emerald/40 text-cyber-emerald truncate max-w-[180px]">
                Focus: {activeFocalId}
              </span>
            )}
          </div>
        )}
      </div>

      {/* Control Strip */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {/* Focal Search */}
        <form onSubmit={handleFocusSubmit} className="cyber-card p-3 flex items-center gap-2">
          <Search className="w-4 h-4 text-cyber-emerald shrink-0" />
          <input
            type="text"
            value={focalInput}
            onChange={(e) => setFocalInput(e.target.value)}
            placeholder="Focus on Entity (bc1... / TX / IP)..."
            className="w-full bg-transparent text-xs text-slate-100 placeholder-slate-500 focus:outline-none"
          />
          <button
            type="submit"
            className="px-2.5 py-1 bg-cyber-emerald text-slate-950 font-bold rounded text-[11px] hover:bg-emerald-400 shrink-0"
          >
            Explore
          </button>
        </form>

        {/* Path Tracer */}
        <form onSubmit={handlePathSubmit} className="cyber-card p-3 flex items-center gap-2">
          <Route className="w-4 h-4 text-cyber-cyan shrink-0" />
          <input
            type="text"
            value={pathSource}
            onChange={(e) => setPathSource(e.target.value)}
            placeholder="Source..."
            className="w-1/2 bg-transparent text-xs text-slate-100 placeholder-slate-500 focus:outline-none"
          />
          <ArrowRight className="w-3 h-3 text-slate-500 shrink-0" />
          <input
            type="text"
            value={pathTarget}
            onChange={(e) => setPathTarget(e.target.value)}
            placeholder="Target..."
            className="w-1/2 bg-transparent text-xs text-slate-100 placeholder-slate-500 focus:outline-none"
          />
          <button
            type="submit"
            className="px-2.5 py-1 bg-cyber-cyan text-slate-950 font-bold rounded text-[11px] hover:bg-cyan-400 shrink-0"
          >
            Trace Path
          </button>
        </form>

        {/* Graph Parameters & Reset */}
        <div className="cyber-card p-3 flex items-center justify-between gap-3 text-xs">
          <div className="flex items-center gap-2">
            <span className="text-slate-400 text-[11px]">k-Hop Depth:</span>
            <select
              value={kHop}
              onChange={(e) => setKHop(Number(e.target.value))}
              className="bg-slate-900 border border-slate-700 rounded px-2 py-0.5 text-xs text-slate-200"
            >
              <option value={1}>1-Hop</option>
              <option value={2}>2-Hop</option>
              <option value={3}>3-Hop</option>
            </select>
          </div>

          {(activeFocalId || isPathMode) ? (
            <button
              onClick={handleResetToGlobal}
              className="px-2.5 py-1 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded text-[11px] border border-slate-700"
            >
              Reset to Global View
            </button>
          ) : (
            <div className="flex items-center gap-1.5 text-[11px] text-slate-400">
              <span className="text-slate-500">Try:</span>
              <button
                type="button"
                onClick={() => { setActiveFocalId('1Addr10A'); setFocalInput('1Addr10A'); }}
                className="px-1.5 py-0.5 rounded bg-slate-800 hover:bg-slate-700 text-cyber-cyan text-[10px]"
              >
                1Addr10A
              </button>
              <button
                type="button"
                onClick={() => { setActiveFocalId('tx_10'); setFocalInput('tx_10'); }}
                className="px-1.5 py-0.5 rounded bg-slate-800 hover:bg-slate-700 text-cyber-emerald text-[10px]"
              >
                tx_10
              </button>
            </div>
          )}
        </div>
      </div>

      {/* Main Canvas with Floating Inspector */}
      <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
        <div className="lg:col-span-3">
          {isLoading ? (
            <div className="cyber-card h-[620px] flex flex-col items-center justify-center text-xs text-slate-400 gap-3">
              <div className="w-8 h-8 border-2 border-cyber-emerald border-t-transparent rounded-full animate-spin" />
              <span>Generating graph topology and value flow paths...</span>
            </div>
          ) : graphData ? (
            <CytoscapeGraph
              data={graphData}
              focalNodeId={activeFocalId || undefined}
              onNodeSelect={setSelectedNode}
              height="620px"
            />
          ) : null}
        </div>

        {/* Selected Node Inspector Drawer */}
        <div className="cyber-card p-5 space-y-4">
          <div className="border-b border-cyber-border pb-3 flex items-center justify-between">
            <h3 className="text-sm font-semibold text-slate-100 uppercase tracking-wider flex items-center gap-1.5">
              <Info className="w-4 h-4 text-cyber-emerald" />
              <span>Node Inspector</span>
            </h3>
            {selectedNode && (
              <Badge variant={selectedNode.risk_score >= 60 ? 'critical' : 'info'}>
                {selectedNode.type}
              </Badge>
            )}
          </div>

          {selectedNode ? (
            <div className="space-y-4 text-xs">
              <div>
                <p className="text-[10px] text-slate-500 uppercase">Entity Identifier</p>
                <p className="text-slate-100 font-bold break-all">{selectedNode.id}</p>
              </div>

              {selectedNode.risk_score > 0 && (
                <div className="p-3 rounded-lg bg-red-500/10 border border-red-500/30 space-y-1">
                  <div className="flex justify-between">
                    <span className="text-slate-400">Risk Priority:</span>
                    <span className="font-bold text-red-400">{selectedNode.risk_score}/100</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-slate-400">ML Anomaly:</span>
                    <span className="font-bold text-cyber-emerald">{selectedNode.anomaly_score.toFixed(2)}</span>
                  </div>
                </div>
              )}

              {/* Node Properties */}
              <div className="space-y-1.5 border-t border-slate-800 pt-3">
                <p className="text-[10px] text-slate-500 uppercase">Attributes</p>
                {Object.entries(selectedNode.properties || {}).map(([k, v]) => (
                  <div key={k} className="flex justify-between text-slate-400">
                    <span className="capitalize">{k.replace(/_/g, ' ')}:</span>
                    <span className="text-slate-200 font-semibold truncate max-w-[140px]">{String(v)}</span>
                  </div>
                ))}
              </div>

              {/* Action Jump to Dossier */}
              <div className="pt-2 border-t border-slate-800">
                <Link
                  to={`/entities/${encodeURIComponent(selectedNode.id)}`}
                  className="w-full flex items-center justify-center gap-1.5 py-2 rounded bg-cyber-emerald text-slate-950 font-bold hover:bg-emerald-400 transition-all text-xs shadow-glow-emerald"
                >
                  <span>Open Full Dossier</span>
                  <ExternalLink className="w-3.5 h-3.5" />
                </Link>
              </div>
            </div>
          ) : (
            <div className="py-16 text-center text-xs text-slate-500">
              Click on any node in the graph visualizer to inspect its topological attributes, risk score, and connected flow.
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
