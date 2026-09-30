import React, { useState } from 'react';
import { useParams, Link, useNavigate } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import {
  Wallet,
  Activity,
  Radio,
  Network,
  FileSpreadsheet,
  ArrowLeft,
  Clock,
  Globe,
  Share2,
  Boxes,
  ShieldAlert,
  ArrowUpRight,
  ExternalLink,
  RotateCcw
} from 'lucide-react';
import { getEntityDossier, getEntityGraph, generateReport } from '../services/api';
import { RiskGauge } from '../components/common/RiskGauge';
import { Badge } from '../components/common/Badge';
import { ReasoningCard } from '../components/explainability/ReasoningCard';
import { FeatureDeviationChart } from '../components/explainability/FeatureDeviationChart';
import { CytoscapeGraph } from '../components/graph/CytoscapeGraph';
import { InvestigationReplayModal } from '../components/replay/InvestigationReplayModal';

export const EntityDetailPage: React.FC = () => {
  const { entityId } = useParams<{ entityId: string }>();
  const navigate = useNavigate();
  const decodedId = decodeURIComponent(entityId || '');
  const [activeTab, setActiveTab] = useState<'overview' | 'graph' | 'ledger' | 'network'>('overview');
  const [reportSuccess, setReportSuccess] = useState<string | null>(null);
  const [showReplayModal, setShowReplayModal] = useState<boolean>(false);

  const { data: dossier, isLoading: dossierLoading } = useQuery({
    queryKey: ['entity-dossier', decodedId],
    queryFn: () => getEntityDossier(decodedId),
    enabled: Boolean(decodedId),
  });

  const { data: graphData, isLoading: graphLoading } = useQuery({
    queryKey: ['entity-graph', decodedId],
    queryFn: () => getEntityGraph(decodedId, 2),
    enabled: Boolean(decodedId),
  });

  const handleGenerateReport = async () => {
    try {
      const rep = await generateReport({
        title: `Forensic Lead Brief: ${decodedId.slice(0, 14)}`,
        entity_id: decodedId,
        include_evidence: true,
        analyst_notes: 'Automated brief generated from entity dossier investigation workspace.',
      });
      setReportSuccess(`Report ${rep.report_id} generated!`);
      setTimeout(() => navigate('/reports'), 1200);
    } catch (err: any) {
      alert(`Report failed: ${err.message}`);
    }
  };

  if (dossierLoading) {
    return (
      <div className="cyber-card p-12 text-center text-xs font-mono text-slate-500">
        Compiling entity dossier and correlation profile...
      </div>
    );
  }

  if (!dossier) {
    return (
      <div className="cyber-card p-12 text-center text-xs font-mono text-slate-500 space-y-4">
        <p>Entity not found in current dataset.</p>
        <Link to="/search" className="text-cyber-emerald hover:underline">
          Return to Entity Search
        </Link>
      </div>
    );
  }

  return (
    <div className="space-y-6 font-mono">
      {/* Back Navigation & Actions */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-cyber-border pb-4">
        <div className="flex items-center gap-3">
          <Link
            to="/alerts"
            className="p-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 transition-colors"
          >
            <ArrowLeft className="w-4 h-4" />
          </Link>
          <div>
            <div className="flex items-center gap-2">
              <span className="text-xs font-semibold text-slate-400 uppercase tracking-widest">
                {dossier.entity_type} DOSSIER
              </span>
              {dossier.cluster_info && (
                <span className="px-2 py-0.5 rounded bg-purple-500/10 text-purple-400 border border-purple-500/30 text-[10px]">
                  {dossier.cluster_info.cluster_name}
                </span>
              )}
            </div>
            <h1 className="text-lg font-bold text-slate-100 break-all select-all font-mono">
              {dossier.entity_id}
            </h1>
          </div>
        </div>

        <div className="flex items-center gap-2 shrink-0">
          <button
            onClick={() => setShowReplayModal(true)}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-cyber-cyan/10 hover:bg-cyber-cyan/20 border border-cyber-cyan/40 text-cyber-cyan font-bold text-xs shadow-glow-cyan transition-all"
            title="Open Investigation Replay"
          >
            <RotateCcw className="w-3.5 h-3.5" />
            <span>Investigation Replay</span>
          </button>
          <button
            onClick={handleGenerateReport}
            className="flex items-center gap-1.5 px-3.5 py-1.5 rounded-lg bg-gradient-to-r from-emerald-600 to-teal-600 hover:from-emerald-500 hover:to-teal-500 text-slate-950 font-bold text-xs shadow-glow-emerald transition-all"
          >
            <FileSpreadsheet className="w-3.5 h-3.5" />
            <span>{reportSuccess || 'Export Lead Report'}</span>
          </button>
        </div>
      </div>

      {/* Entity Summary Row */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div className="cyber-card p-5 flex items-center justify-between md:col-span-1">
          <RiskGauge score={dossier.risk_score} size="md" />
        </div>

        <div className="cyber-card p-4 space-y-1">
          <p className="text-[10px] text-slate-500 uppercase">Total Value Flow</p>
          <p className="text-xl font-bold text-slate-100">{dossier.total_volume_btc.toFixed(4)} BTC</p>
          <p className="text-[11px] text-slate-400">{dossier.transaction_count} Total Transactions</p>
        </div>

        <div className="cyber-card p-4 space-y-1">
          <p className="text-[10px] text-slate-500 uppercase">Counterparty Network</p>
          <p className="text-xl font-bold text-slate-100">{dossier.unique_counterparties} Peers</p>
          <p className="text-[11px] text-slate-400">Direct connected addresses</p>
        </div>

        <div className="cyber-card p-4 space-y-1">
          <p className="text-[10px] text-slate-500 uppercase">Jurisdictional Observations</p>
          <p className="text-xl font-bold text-slate-100">{dossier.observed_countries.length} Countries</p>
          <p className="text-[11px] text-slate-400">{dossier.observed_asns.length} Autonomous Systems (ASNs)</p>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex border-b border-cyber-border gap-2">
        {[
          { id: 'overview', label: 'Explainability & Features' },
          { id: 'graph', label: 'Ego Graph (2-Hop)' },
          { id: 'ledger', label: `Transactions (${dossier.recent_transactions.length})` },
          { id: 'network', label: `Network Layer (${dossier.observed_ips.length} IPs)` },
        ].map((tab) => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id as any)}
            className={`px-4 py-2 text-xs font-semibold transition-all border-b-2 ${
              activeTab === tab.id
                ? 'border-cyber-emerald text-cyber-emerald bg-emerald-500/5'
                : 'border-transparent text-slate-400 hover:text-slate-200'
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* Tab 1: Explainability & Features */}
      {activeTab === 'overview' && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <ReasoningCard
            reasons={dossier.explanation_reasons}
            severity={dossier.severity}
            anomalyScore={dossier.anomaly_score}
            priorityScore={dossier.risk_score}
            rawAnomalyScore={dossier.raw_anomaly_score}
            validationScore={dossier.validation_score}
            confidence={dossier.confidence}
            supportingEvidence={dossier.supporting_evidence}
            counterEvidence={dossier.counter_evidence}
            behaviouralDeviation={dossier.behavioural_deviation}
            historicalContext={dossier.historical_context}
            validationExplanation={dossier.validation_explanation}
          />

          <div className="cyber-card p-5 space-y-3">
            <h3 className="text-sm font-semibold text-slate-100 uppercase tracking-wider">
              Feature Deviation vs Baseline Population (z-Score)
            </h3>
            <FeatureDeviationChart deviations={dossier.feature_deviations} />
          </div>
        </div>
      )}

      {/* Tab 2: Graph Explorer */}
      {activeTab === 'graph' && (
        <div className="space-y-3">
          {graphData ? (
            <CytoscapeGraph data={graphData} focalNodeId={decodedId} height="520px" />
          ) : (
            <div className="cyber-card p-12 text-center text-xs text-slate-500">Loading graph...</div>
          )}
        </div>
      )}

      {/* Tab 3: Transaction Ledger */}
      {activeTab === 'ledger' && (
        <div className="cyber-card p-5 space-y-4">
          <h3 className="text-sm font-semibold text-slate-100 uppercase tracking-wider">
            Transaction Activity Ledger
          </h3>
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead>
                <tr className="border-b border-slate-800 text-slate-400 uppercase text-[10px]">
                  <th className="pb-3 pl-2">TXID</th>
                  <th className="pb-3">Timestamp (UTC)</th>
                  <th className="pb-3">Input Total</th>
                  <th className="pb-3">Output Total</th>
                  <th className="pb-3">Fee</th>
                  <th className="pb-3">Script</th>
                  <th className="pb-3 pr-2 text-right">Inspect</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60 text-slate-200">
                {dossier.recent_transactions.map((tx, i) => (
                  <tr key={i} className="hover:bg-slate-800/30">
                    <td className="py-3 pl-2 text-cyber-cyan font-bold">
                      {tx.txid.length > 20 ? `${tx.txid.slice(0, 12)}...` : tx.txid}
                    </td>
                    <td className="py-3 text-slate-400">{tx.timestamp || 'N/A'}</td>
                    <td className="py-3 text-slate-300">{tx.input_total ? `${tx.input_total.toFixed(4)} BTC` : '-'}</td>
                    <td className="py-3 text-slate-300">{tx.output_total ? `${tx.output_total.toFixed(4)} BTC` : '-'}</td>
                    <td className="py-3 text-slate-500">{tx.fee ? `${tx.fee.toFixed(5)} BTC` : '-'}</td>
                    <td className="py-3 text-slate-400">{tx.script_type || 'P2PKH'}</td>
                    <td className="py-3 pr-2 text-right">
                      <Link
                        to={`/entities/${encodeURIComponent(tx.txid)}`}
                        className="p-1 text-slate-400 hover:text-cyber-emerald"
                      >
                        <ExternalLink className="w-3.5 h-3.5 inline" />
                      </Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Tab 4: Network Observations */}
      {activeTab === 'network' && (
        <div className="cyber-card p-5 space-y-4">
          <div className="border-b border-slate-800 pb-2">
            <h3 className="text-sm font-semibold text-slate-100 uppercase tracking-wider">
              Network P2P Relay Observations
            </h3>
            <p className="text-[11px] text-slate-500 mt-0.5">
              Network-layer broadcast evidence. Does not assert cryptographic ownership of wallet address.
            </p>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead>
                <tr className="border-b border-slate-800 text-slate-400 uppercase text-[10px]">
                  <th className="pb-3 pl-2">Relay IP Address</th>
                  <th className="pb-3">Country Jurisdiction</th>
                  <th className="pb-3">Autonomous System (ASN)</th>
                  <th className="pb-3">Observation Time</th>
                  <th className="pb-3 pr-2 text-right">Inspect IP</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60 text-slate-200">
                {dossier.observed_ips.map((ipo, i) => (
                  <tr key={i} className="hover:bg-slate-800/30">
                    <td className="py-3 pl-2 text-cyber-purple font-bold flex items-center gap-2">
                      <Radio className="w-3.5 h-3.5 text-cyber-purple" />
                      <span>{ipo.ip}</span>
                    </td>
                    <td className="py-3 text-slate-300">{ipo.country || 'UNKNOWN'}</td>
                    <td className="py-3 text-slate-400">{ipo.asn || 'AS_UNKNOWN'}</td>
                    <td className="py-3 text-slate-500">{ipo.timestamp || 'N/A'}</td>
                    <td className="py-3 pr-2 text-right">
                      <Link
                        to={`/entities/${encodeURIComponent(ipo.ip)}`}
                        className="p-1 text-slate-400 hover:text-cyber-purple"
                      >
                        <ExternalLink className="w-3.5 h-3.5 inline" />
                      </Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Investigation Replay Modal */}
      <InvestigationReplayModal
        entityId={decodedId}
        isOpen={showReplayModal}
        onClose={() => setShowReplayModal(false)}
      />
    </div>
  );
};
