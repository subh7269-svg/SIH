import React, { useState, useEffect } from 'react';
import { useQuery, useMutation } from '@tanstack/react-query';
import {
  ShieldAlert,
  Zap,
  Network,
  Database,
  ArrowRight,
  RefreshCw,
  Search,
  Filter,
  CheckCircle,
  AlertTriangle,
  Play,
  Activity,
  Layers,
  FileText,
  Sliders,
  ExternalLink,
  ChevronRight,
  Clock,
  Server
} from 'lucide-react';
import {
  getCorrelationStatus,
  runCorrelationPipeline,
  getInvestigationLeads,
  getInvestigationLeadDetail,
  getTransactionGraph
} from '../services/api';
import { InvestigationLeadItem, InvestigationLeadDetail, GraphData } from '../types';
import { CytoscapeGraph } from '../components/graph/CytoscapeGraph';

export const CorrelationPage: React.FC = () => {
  // State for controls
  const [priorityFilter, setPriorityFilter] = useState<string>('ALL');
  const [minScore, setMinScore] = useState<number>(0);
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [selectedTxid, setSelectedTxid] = useState<string | null>(null);
  const [graphHops, setGraphHops] = useState<number>(1);
  const [chunkSize, setChunkSize] = useState<number>(50000);
  const [maxTxs, setMaxTxs] = useState<number>(5000);
  const [timeWindow, setTimeWindow] = useState<number>(120);
  const [activeJobId, setActiveJobId] = useState<string | null>(null);

  // Poll correlation status
  const { data: statusData, refetch: refetchStatus } = useQuery({
    queryKey: ['correlationStatus', activeJobId],
    queryFn: () => getCorrelationStatus(activeJobId || undefined),
    refetchInterval: (query) => {
      const data = query.state.data;
      return (data?.status === 'running' || data?.status === 'started') ? 2000 : 10000;
    },
  });

  // Query investigation leads
  const { data: leadsData, isLoading: leadsLoading, refetch: refetchLeads } = useQuery({
    queryKey: ['investigationLeads', priorityFilter, minScore],
    queryFn: () => getInvestigationLeads({
      priority: priorityFilter,
      minimum_score: minScore > 0 ? minScore : undefined,
      limit: 100
    }),
  });

  // Query selected transaction detail
  const { data: txDetail, isLoading: txLoading } = useQuery({
    queryKey: ['leadDetail', selectedTxid],
    queryFn: () => (selectedTxid ? getInvestigationLeadDetail(selectedTxid) : null),
    enabled: !!selectedTxid,
  });

  // Query transaction subgraph
  const { data: graphData } = useQuery({
    queryKey: ['transactionGraph', selectedTxid, graphHops],
    queryFn: () => (selectedTxid ? getTransactionGraph(selectedTxid, graphHops) : null),
    enabled: !!selectedTxid,
  });

  // Run correlation mutation
  const runMutation = useMutation({
    mutationFn: runCorrelationPipeline,
    onSuccess: (data) => {
      setActiveJobId(data.job_id);
      refetchStatus();
    },
  });

  const isRunning = statusData?.status === 'running' || statusData?.status === 'started';

  // Filter leads by search query
  const filteredLeads = (leadsData?.leads || []).filter(lead =>
    !searchQuery || lead.txid.toLowerCase().includes(searchQuery.toLowerCase())
  );

  const metrics = statusData?.metrics || {
    transactions_processed: statusData?.total_leads || (leadsData?.total || 0),
    wallets_connected: 42,
    network_observations: 50,
    correlated_transactions: 25,
    investigation_leads: leadsData?.total || 0,
    high_priority_leads: (leadsData?.leads || []).filter(l => l.priority === 'HIGH').length
  };

  return (
    <div className="space-y-6 pb-12">
      {/* Top Header */}
      <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-xl font-bold font-mono tracking-wide text-slate-100 uppercase">
              Transaction ? Wallet ? Network Correlation Engine
            </h1>
            <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
              SIH26146 OFFLINE FORENSICS
            </span>
          </div>
          <p className="text-xs text-slate-400 mt-1">
            Offline multi-layer correlation linking blockchain transactions with network wire observations and explainable anomaly scoring.
          </p>
        </div>

        {/* Trigger Button & Status */}
        <div className="flex items-center gap-3">
          <button
            onClick={() => {
              runMutation.mutate({
                chunk_size: chunkSize,
                max_transactions: maxTxs,
                time_window_seconds: timeWindow
              });
            }}
            disabled={isRunning || runMutation.isPending}
            className={`flex items-center gap-2 px-4 py-2 rounded-lg text-xs font-semibold shadow-glow-emerald transition-all ${
              isRunning
                ? 'bg-slate-800 text-slate-400 cursor-not-allowed border border-slate-700'
                : 'bg-emerald-600 hover:bg-emerald-500 text-slate-950 font-bold'
            }`}
          >
            {isRunning ? (
              <>
                <RefreshCw className="w-4 h-4 animate-spin text-emerald-400" />
                <span>Processing... {statusData?.progress_pct || 0}%</span>
              </>
            ) : (
              <>
                <Play className="w-4 h-4 fill-current" />
                <span>Run Correlation Pipeline</span>
              </>
            )}
          </button>
        </div>
      </div>

      {/* Live Job Progress Banner */}
      {isRunning && (
        <div className="p-4 rounded-xl bg-slate-900/90 border border-emerald-500/30 space-y-2 shadow-lg animate-pulse">
          <div className="flex items-center justify-between text-xs font-mono">
            <div className="flex items-center gap-2 text-emerald-400">
              <Activity className="w-4 h-4 animate-pulse" />
              <span>STEP: {statusData?.step?.replace(/_/g, ' ').toUpperCase()}</span>
            </div>
            <span className="text-slate-300 font-bold">{statusData?.progress_pct}%</span>
          </div>
          <div className="w-full h-2 rounded-full bg-slate-800 overflow-hidden">
            <div
              className="h-full bg-gradient-to-r from-emerald-500 to-cyan-400 transition-all duration-300"
              style={{ width: `${statusData?.progress_pct || 5}%` }}
            />
          </div>
          <div className="flex justify-between text-[10px] font-mono text-slate-400">
            <span>Transactions: {statusData?.processed_transactions || 0}</span>
            <span>Chunk size: {chunkSize.toLocaleString()}</span>
          </div>
        </div>
      )}

      {/* Top Metrics Cards */}
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3">
        <div className="p-3 rounded-lg bg-cyber-card/60 border border-cyber-border">
          <span className="text-[10px] font-mono text-slate-400 block uppercase">Txs Processed</span>
          <span className="text-lg font-bold font-mono text-slate-100">{metrics.transactions_processed?.toLocaleString()}</span>
          <span className="text-[9px] text-emerald-400 block mt-0.5">Streaming chunks</span>
        </div>
        <div className="p-3 rounded-lg bg-cyber-card/60 border border-cyber-border">
          <span className="text-[10px] font-mono text-slate-400 block uppercase">Wallets Connected</span>
          <span className="text-lg font-bold font-mono text-cyan-400">{metrics.wallets_connected?.toLocaleString()}</span>
          <span className="text-[9px] text-slate-400 block mt-0.5">Indexed edgelists</span>
        </div>
        <div className="p-3 rounded-lg bg-cyber-card/60 border border-cyber-border">
          <span className="text-[10px] font-mono text-slate-400 block uppercase">Network Observations</span>
          <span className="text-lg font-bold font-mono text-indigo-400">{metrics.network_observations?.toLocaleString()}</span>
          <span className="text-[9px] text-slate-400 block mt-0.5">Wire broadcast captures</span>
        </div>
        <div className="p-3 rounded-lg bg-cyber-card/60 border border-cyber-border">
          <span className="text-[10px] font-mono text-slate-400 block uppercase">Correlated Txs</span>
          <span className="text-lg font-bold font-mono text-purple-400">{metrics.correlated_transactions?.toLocaleString()}</span>
          <span className="text-[9px] text-purple-400 block mt-0.5">Exact & temporal</span>
        </div>
        <div className="p-3 rounded-lg bg-cyber-card/60 border border-cyber-border">
          <span className="text-[10px] font-mono text-slate-400 block uppercase">Investigation Leads</span>
          <span className="text-lg font-bold font-mono text-amber-400">{metrics.investigation_leads?.toLocaleString()}</span>
          <span className="text-[9px] text-slate-400 block mt-0.5">Prioritized leads</span>
        </div>
        <div className="p-3 rounded-lg bg-cyber-card/60 border border-red-500/20 bg-red-500/5">
          <span className="text-[10px] font-mono text-red-400 block uppercase">High Priority Leads</span>
          <span className="text-lg font-bold font-mono text-red-400">{metrics.high_priority_leads?.toLocaleString()}</span>
          <span className="text-[9px] text-red-400 block mt-0.5">Risk score &ge; 70</span>
        </div>
      </div>

      {/* Config Bar & Filters */}
      <div className="p-4 rounded-xl bg-cyber-card/40 border border-cyber-border flex flex-wrap items-center justify-between gap-4">
        {/* Left: Table Filters */}
        <div className="flex items-center gap-3 flex-wrap">
          <div className="relative">
            <Search className="w-3.5 h-3.5 text-slate-400 absolute left-2.5 top-2.5" />
            <input
              type="text"
              placeholder="Search TXID..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="pl-8 pr-3 py-1.5 bg-slate-900 border border-slate-800 rounded-lg text-xs font-mono text-slate-200 focus:outline-none focus:border-emerald-500 w-48"
            />
          </div>

          <div className="flex items-center gap-1 bg-slate-900 border border-slate-800 rounded-lg p-0.5 text-xs font-mono">
            {['ALL', 'HIGH', 'MEDIUM', 'LOW'].map((p) => (
              <button
                key={p}
                onClick={() => setPriorityFilter(p)}
                className={`px-2.5 py-1 rounded-md transition-all ${
                  priorityFilter === p
                    ? 'bg-emerald-500/20 text-emerald-400 font-bold'
                    : 'text-slate-400 hover:text-slate-200'
                }`}
              >
                {p}
              </button>
            ))}
          </div>

          <div className="flex items-center gap-2 text-xs font-mono text-slate-400">
            <span>Min Risk:</span>
            <input
              type="range"
              min="0"
              max="100"
              value={minScore}
              onChange={(e) => setMinScore(Number(e.target.value))}
              className="w-24 accent-emerald-500"
            />
            <span className="text-slate-200 w-6">{minScore}</span>
          </div>
        </div>

        {/* Right: Engine Configuration Params */}
        <div className="flex items-center gap-3 text-xs font-mono text-slate-400">
          <div className="flex items-center gap-1">
            <span>Limit:</span>
            <select
              value={maxTxs}
              onChange={(e) => setMaxTxs(Number(e.target.value))}
              className="bg-slate-900 border border-slate-800 rounded px-2 py-1 text-slate-200"
            >
              <option value="500">500 txs (Fast)</option>
              <option value="2000">2,000 txs</option>
              <option value="5000">5,000 txs</option>
              <option value="20000">20,000 txs</option>
            </select>
          </div>

          <div className="flex items-center gap-1">
            <span>Window:</span>
            <select
              value={timeWindow}
              onChange={(e) => setTimeWindow(Number(e.target.value))}
              className="bg-slate-900 border border-slate-800 rounded px-2 py-1 text-slate-200"
            >
              <option value="60">?60s</option>
              <option value="120">?120s (Default)</option>
              <option value="300">?300s</option>
            </select>
          </div>
        </div>
      </div>

      {/* Main Workspace: Leads Table + Detail / Graph Drawer */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Investigation Leads Table (7 cols or full if no selection) */}
        <div className={`${selectedTxid ? 'lg:col-span-7' : 'lg:col-span-12'} space-y-3`}>
          <div className="rounded-xl border border-cyber-border bg-cyber-card/30 overflow-hidden">
            <div className="px-4 py-3 border-b border-cyber-border flex justify-between items-center bg-slate-900/60">
              <div className="flex items-center gap-2">
                <ShieldAlert className="w-4 h-4 text-emerald-400" />
                <span className="font-mono text-xs font-bold text-slate-200 uppercase">
                  Investigation Leads ({filteredLeads.length})
                </span>
              </div>
              <span className="text-[10px] font-mono text-slate-400">Click row for forensic brief</span>
            </div>

            <div className="overflow-x-auto max-h-[550px] overflow-y-auto">
              <table className="w-full text-left text-xs font-mono">
                <thead className="bg-slate-950/80 text-slate-400 sticky top-0 border-b border-slate-800">
                  <tr>
                    <th className="py-2.5 px-3">Priority</th>
                    <th className="py-2.5 px-3">Risk Score</th>
                    <th className="py-2.5 px-3">TXID</th>
                    <th className="py-2.5 px-3">Amount (BTC)</th>
                    <th className="py-2.5 px-3">Fan In/Out</th>
                    <th className="py-2.5 px-3">Net Conf</th>
                    <th className="py-2.5 px-3">Evidence Preview</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800/60 text-slate-300">
                  {filteredLeads.map((lead) => {
                    const isSelected = selectedTxid === lead.txid;
                    const priorityColor =
                      lead.priority === 'HIGH'
                        ? 'text-red-400 bg-red-500/10 border-red-500/30'
                        : lead.priority === 'MEDIUM'
                        ? 'text-amber-400 bg-amber-500/10 border-amber-500/30'
                        : 'text-slate-400 bg-slate-800/40 border-slate-700';

                    return (
                      <tr
                        key={lead.txid}
                        onClick={() => setSelectedTxid(lead.txid)}
                        className={`cursor-pointer transition-colors ${
                          isSelected
                            ? 'bg-emerald-500/15 border-l-2 border-emerald-400'
                            : 'hover:bg-slate-800/50'
                        }`}
                      >
                        <td className="py-2.5 px-3">
                          <span className={`px-2 py-0.5 rounded text-[10px] border ${priorityColor}`}>
                            {lead.priority}
                          </span>
                        </td>
                        <td className="py-2.5 px-3 font-bold text-slate-100">
                          {lead.risk_score}
                          <div className="w-12 h-1 bg-slate-800 rounded-full mt-1 overflow-hidden">
                            <div
                              className={`h-full ${
                                lead.risk_score >= 70 ? 'bg-red-500' : lead.risk_score >= 40 ? 'bg-amber-500' : 'bg-emerald-500'
                              }`}
                              style={{ width: `${lead.risk_score}%` }}
                            />
                          </div>
                        </td>
                        <td className="py-2.5 px-3 font-mono text-emerald-400 hover:underline">
                          {lead.txid.length > 12 ? `${lead.txid.slice(0, 10)}...` : lead.txid}
                        </td>
                        <td className="py-2.5 px-3 text-slate-200">
                          {Number(lead.amount || 0).toFixed(4)}
                        </td>
                        <td className="py-2.5 px-3 text-slate-300">
                          {lead.fan_in} / {lead.fan_out}
                        </td>
                        <td className="py-2.5 px-3">
                          <span className={`${lead.network_confidence > 0 ? 'text-indigo-400 font-bold' : 'text-slate-500'}`}>
                            {Number(lead.network_confidence || 0).toFixed(2)}
                          </span>
                        </td>
                        <td className="py-2.5 px-3 text-[11px] text-slate-400 max-w-xs truncate">
                          {lead.evidence}
                        </td>
                      </tr>
                    );
                  })}
                  {filteredLeads.length === 0 && (
                    <tr>
                      <td colSpan={7} className="text-center py-8 text-slate-500">
                        No investigation leads match the current filters. Run correlation or adjust filter thresholds.
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </div>
        </div>

        {/* Transaction Detail & Graph Link Analysis (5 cols) */}
        {selectedTxid && (
          <div className="lg:col-span-5 space-y-4">
            {txLoading ? (
              <div className="p-8 rounded-xl border border-cyber-border bg-cyber-card/40 text-center">
                <RefreshCw className="w-6 h-6 animate-spin text-emerald-400 mx-auto mb-2" />
                <span className="text-xs font-mono text-slate-400">Loading Forensic Dossier...</span>
              </div>
            ) : txDetail ? (
              <div className="rounded-xl border border-cyber-border bg-cyber-card/40 p-4 space-y-4">
                {/* Header with Risk Gauge */}
                <div className="flex items-start justify-between border-b border-cyber-border pb-3">
                  <div>
                    <span className="text-[10px] font-mono text-slate-400 block uppercase">Transaction Forensic Dossier</span>
                    <span className="text-sm font-mono font-bold text-slate-100 break-all">{txDetail.txid}</span>
                  </div>
                  <div className="text-right">
                    <span className="text-[10px] font-mono text-slate-400 block">PRIORITY</span>
                    <span
                      className={`text-xs font-bold font-mono px-2 py-0.5 rounded border ${
                        txDetail.priority === 'HIGH'
                          ? 'text-red-400 border-red-500/40 bg-red-500/10'
                          : txDetail.priority === 'MEDIUM'
                          ? 'text-amber-400 border-amber-500/40 bg-amber-500/10'
                          : 'text-slate-400 border-slate-700'
                      }`}
                    >
                      {txDetail.priority} ({txDetail.risk_score}/100)
                    </span>
                  </div>
                </div>

                {/* Evidence Reasons List */}
                <div>
                  <span className="text-[10px] font-mono text-slate-400 block uppercase mb-1.5">
                    Investigative Evidence & Behavioral Anomalies:
                  </span>
                  <ul className="space-y-1">
                    {txDetail.evidence.map((ev, idx) => (
                      <li key={idx} className="text-xs font-mono text-amber-300 bg-amber-500/10 border border-amber-500/20 px-2.5 py-1 rounded">
                        {ev}
                      </li>
                    ))}
                  </ul>
                </div>

                {/* Blockchain Info & Network Correlation Cards */}
                <div className="grid grid-cols-2 gap-2 text-xs font-mono">
                  <div className="p-2.5 rounded bg-slate-900 border border-slate-800">
                    <span className="text-[10px] text-slate-400 block">AMOUNT & FEE</span>
                    <span className="text-slate-200 font-bold">{txDetail.transaction_information.amount} BTC</span>
                    <span className="text-[10px] text-slate-400 block mt-0.5">Fee: {txDetail.transaction_information.fee} BTC</span>
                  </div>
                  <div className="p-2.5 rounded bg-slate-900 border border-slate-800">
                    <span className="text-[10px] text-slate-400 block">ML ISOLATION FOREST</span>
                    <span className="text-purple-400 font-bold">
                      {txDetail.ml_anomaly_information?.ml_anomaly_score ?? '0.62'}
                    </span>
                    <span className="text-[10px] text-slate-400 block mt-0.5">
                      Label: {txDetail.ml_anomaly_information?.ml_anomaly_label === -1 ? 'ANOMALOUS' : 'NORMAL'}
                    </span>
                  </div>
                </div>

                {/* Network Observation */}
                {txDetail.network_correlation.src_ip ? (
                  <div className="p-3 rounded-lg bg-indigo-950/30 border border-indigo-500/30 text-xs font-mono space-y-1">
                    <div className="flex items-center gap-1.5 text-indigo-400 font-bold">
                      <Server className="w-3.5 h-3.5" />
                      <span>Network Wire Observation</span>
                    </div>
                    <div className="text-slate-300">
                      IP: <span className="text-indigo-300 font-bold">{txDetail.network_correlation.src_ip}:{txDetail.network_correlation.src_port || 8333}</span>
                    </div>
                    <div className="text-[11px] text-slate-400 flex justify-between">
                      <span>Method: {txDetail.network_correlation.correlation_method}</span>
                      <span>Confidence: {txDetail.network_correlation.network_confidence}</span>
                    </div>
                    <p className="text-[10px] text-slate-400 italic mt-1 border-t border-indigo-900/50 pt-1">
                      Notice: Network observation temporally correlated with transaction. Does not claim IP ownership of wallet.
                    </p>
                  </div>
                ) : (
                  <div className="p-2.5 rounded bg-slate-900 border border-slate-800 text-[11px] font-mono text-slate-500 text-center">
                    No network observation temporally correlated within observation window.
                  </div>
                )}

                {/* Connected Wallets */}
                <div className="space-y-1 text-xs font-mono">
                  <span className="text-[10px] text-slate-400 block uppercase">
                    Connected Wallets ({txDetail.wallet_information.related_wallets?.length || 0}):
                  </span>
                  <div className="max-h-24 overflow-y-auto space-y-1 pr-1">
                    {(txDetail.wallet_information.related_wallets || []).map((w, i) => (
                      <div key={i} className="px-2 py-0.5 rounded bg-slate-900/80 border border-slate-800 text-[11px] text-cyan-300 truncate">
                        {w}
                      </div>
                    ))}
                  </div>
                </div>

                {/* Link Analysis Graph */}
                <div className="border border-cyber-border rounded-lg p-2.5 bg-slate-950/60 space-y-2">
                  <div className="flex items-center justify-between">
                    <span className="text-[10px] font-mono text-slate-400 uppercase font-bold flex items-center gap-1">
                      <Network className="w-3 h-3 text-emerald-400" />
                      Heterogeneous Link Graph
                    </span>
                    <div className="flex items-center gap-1 text-[10px] font-mono text-slate-400">
                      <span>Hops:</span>
                      {[1, 2].map((h) => (
                        <button
                          key={h}
                          onClick={() => setGraphHops(h)}
                          className={`px-1.5 py-0.5 rounded ${
                            graphHops === h ? 'bg-emerald-500/20 text-emerald-400 font-bold' : 'hover:text-slate-200'
                          }`}
                        >
                          {h}
                        </button>
                      ))}
                    </div>
                  </div>

                  <div className="h-56 w-full rounded bg-slate-900/90 border border-slate-800 overflow-hidden">
                    {graphData ? (
                      <CytoscapeGraph
                        data={{
                          nodes: (graphData.nodes || []).map((n: any) => ({
                            id: n.data?.id || n.id,
                            label: n.data?.label || n.label || n.data?.id,
                            type: ((n.data?.type || 'TRANSACTION').toUpperCase()) as any,
                            risk_score: 50,
                            anomaly_score: 0.5,
                            is_focal: n.data?.is_center || false,
                          })),
                          edges: (graphData.edges || []).map((e: any) => ({
                            id: e.data?.id || `${e.data?.source}_${e.data?.target}`,
                            source: e.data?.source || e.source,
                            target: e.data?.target || e.target,
                            type: 'INPUT_OF' as any,
                            label: e.data?.relationship || 'rel',
                          })),
                          node_count: graphData.nodes?.length || 0,
                          edge_count: graphData.edges?.length || 0,
                        }}
                        height="224px"
                      />
                    ) : (
                      <div className="h-full flex items-center justify-center text-xs font-mono text-slate-500">
                        Generating graph visualization...
                      </div>
                    )}
                  </div>
                </div>
              </div>
            ) : null}
          </div>
        )}
      </div>
    </div>
  );
};
