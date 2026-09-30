import React, { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Link, useNavigate } from 'react-router-dom';
import {
  RotateCcw,
  X,
  AlertTriangle,
  CheckCircle2,
  TrendingUp,
  Scale,
  Network,
  ShieldAlert,
  ChevronDown,
  ChevronUp,
  ExternalLink,
  Layers,
  ArrowRight,
  Clock,
  Radio,
  Share2,
  FileSpreadsheet,
  Info,
  Maximize2
} from 'lucide-react';
import { getInvestigationReplay, getEntityInvestigationReplay } from '../../services/api';
import { InvestigationReplay, ReplayStage } from '../../types';
import { Badge } from '../common/Badge';
import { CytoscapeGraph } from '../graph/CytoscapeGraph';

interface InvestigationReplayModalProps {
  alertId?: string | null;
  entityId?: string | null;
  isOpen: boolean;
  onClose: () => void;
}

export const InvestigationReplayModal: React.FC<InvestigationReplayModalProps> = ({
  alertId,
  entityId,
  isOpen,
  onClose,
}) => {
  const navigate = useNavigate();

  // Expanded stage tracking: all true by default
  const [expandedStages, setExpandedStages] = useState<Record<string, boolean>>({
    anomaly_detected: true,
    contextual_validation: true,
    historical_baseline: true,
    evidence_collected: true,
    graph_investigation: true,
    investigative_lead: true,
  });

  const { data: replay, isLoading, error } = useQuery<InvestigationReplay>({
    queryKey: ['investigation-replay', alertId, entityId],
    queryFn: () => {
      if (alertId) {
        return getInvestigationReplay(alertId);
      }
      if (entityId) {
        return getEntityInvestigationReplay(entityId);
      }
      throw new Error('Either alertId or entityId must be provided');
    },
    enabled: isOpen && Boolean(alertId || entityId),
  });

  if (!isOpen) return null;

  const toggleStage = (stageId: string) => {
    setExpandedStages((prev) => ({
      ...prev,
      [stageId]: !prev[stageId],
    }));
  };

  const toggleAllStages = () => {
    const anyClosed = Object.values(expandedStages).some((val) => !val);
    const nextState: Record<string, boolean> = {};
    ['anomaly_detected', 'contextual_validation', 'historical_baseline', 'evidence_collected', 'graph_investigation', 'investigative_lead'].forEach((k) => {
      nextState[k] = anyClosed;
    });
    setExpandedStages(nextState);
  };

  const getStageIcon = (stageId: string) => {
    switch (stageId) {
      case 'anomaly_detected':
        return <AlertTriangle className="w-4 h-4 text-cyber-cyan" />;
      case 'contextual_validation':
        return <CheckCircle2 className="w-4 h-4 text-cyber-emerald" />;
      case 'historical_baseline':
        return <TrendingUp className="w-4 h-4 text-amber-400" />;
      case 'evidence_collected':
        return <Scale className="w-4 h-4 text-purple-400" />;
      case 'graph_investigation':
        return <Network className="w-4 h-4 text-blue-400" />;
      case 'investigative_lead':
        return <ShieldAlert className="w-4 h-4 text-red-400" />;
      default:
        return <RotateCcw className="w-4 h-4 text-slate-400" />;
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-md p-3 sm:p-6 overflow-y-auto">
      <div className="cyber-card w-full max-w-5xl my-auto border border-cyber-borderLight shadow-2xl flex flex-col max-h-[92vh] overflow-hidden rounded-xl">
        {/* Header */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 p-4 sm:p-5 border-b border-cyber-border bg-slate-950/90 shrink-0">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-lg bg-cyber-cyan/10 border border-cyber-cyan/30 flex items-center justify-center shrink-0">
              <RotateCcw className="w-5 h-5 text-cyber-cyan animate-pulse" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h2 className="text-base font-bold text-slate-100 tracking-wide font-mono">
                  INVESTIGATION REPLAY
                </h2>
                {replay && (
                  <span className="px-2 py-0.5 rounded bg-slate-800 text-[10px] font-mono text-cyber-cyan border border-slate-700">
                    {replay.replay_id}
                  </span>
                )}
              </div>
              <p className="text-[11px] text-slate-400 mt-0.5 font-mono">
                Chronological reproduction of anomaly detection, contextual validation, baseline comparison, and fund-flow evidence.
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2 shrink-0 self-end sm:self-auto">
            {replay && (
              <Badge variant={replay.severity.toLowerCase() as any}>
                {replay.severity} ({replay.priority_score}/100)
              </Badge>
            )}
            <button
              onClick={toggleAllStages}
              className="px-2.5 py-1 text-xs rounded bg-slate-800 hover:bg-slate-700 text-slate-300 border border-slate-700 font-mono transition-colors"
            >
              Toggle All
            </button>
            <button
              onClick={onClose}
              className="p-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-400 hover:text-slate-100 transition-colors"
              title="Close Replay"
            >
              <X className="w-4 h-4" />
            </button>
          </div>
        </div>

        {/* Scrollable Replay Body */}
        <div className="p-4 sm:p-6 overflow-y-auto space-y-6 font-mono text-xs bg-cyber-bg">
          {isLoading ? (
            <div className="py-20 flex flex-col items-center justify-center text-slate-400 gap-3">
              <div className="w-8 h-8 border-2 border-cyber-cyan border-t-transparent rounded-full animate-spin" />
              <span>Reconstructing chronological investigation timeline from pipeline records...</span>
            </div>
          ) : error || !replay ? (
            <div className="p-8 text-center text-slate-400 space-y-3">
              <AlertTriangle className="w-8 h-8 text-amber-400 mx-auto" />
              <p className="font-semibold text-slate-200">Unable to load investigation replay</p>
              <p className="text-slate-500 text-[11px]">
                {(error as any)?.message || 'No prior investigative alert found for this entity.'}
              </p>
              <button
                onClick={onClose}
                className="px-3 py-1.5 rounded bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs border border-slate-700"
              >
                Close Replay
              </button>
            </div>
          ) : (
            <div className="relative pl-6 sm:pl-8 space-y-6 before:absolute before:left-3 sm:before:left-4 before:top-4 before:bottom-4 before:w-0.5 before:bg-slate-800">
              {/* STAGE 1: ANOMALY DETECTED */}
              {(() => {
                const stage = replay.stages.find((s) => s.stage_id === 'anomaly_detected');
                const isExpanded = expandedStages['anomaly_detected'];
                if (!stage) return null;
                const data = stage.data;

                return (
                  <div className="relative space-y-2">
                    {/* Step Icon Badge */}
                    <div className="absolute -left-6 sm:-left-8 top-1 w-6 h-6 rounded-full bg-slate-900 border border-cyber-cyan flex items-center justify-center text-[10px] font-bold text-cyber-cyan shadow-[0_0_8px_rgba(6,182,212,0.4)]">
                      1
                    </div>

                    <div className="cyber-card p-4 rounded-xl border border-slate-800 bg-slate-950/70 space-y-3">
                      <div
                        onClick={() => toggleStage('anomaly_detected')}
                        className="flex items-center justify-between cursor-pointer select-none"
                      >
                        <div className="flex items-center gap-2">
                          {getStageIcon('anomaly_detected')}
                          <span className="font-bold text-slate-100 uppercase text-xs tracking-wider">
                            1. Anomaly Detected
                          </span>
                          <span className="text-[10px] px-2 py-0.5 rounded bg-cyber-cyan/10 text-cyber-cyan border border-cyber-cyan/30">
                            Isolation Forest
                          </span>
                        </div>
                        <div className="flex items-center gap-3">
                          <span className="text-[11px] text-slate-400">
                            Score: <strong className="text-cyber-cyan font-bold">{(data.raw_anomaly_score ?? data.anomaly_score).toFixed(4)}</strong>
                          </span>
                          {isExpanded ? <ChevronUp className="w-4 h-4 text-slate-400" /> : <ChevronDown className="w-4 h-4 text-slate-400" />}
                        </div>
                      </div>

                      {isExpanded && (
                        <div className="space-y-3 pt-2 border-t border-slate-800 text-xs">
                          <p className="text-slate-300 text-[11px] leading-relaxed">
                            {stage.summary}
                          </p>

                          <div className="grid grid-cols-1 sm:grid-cols-3 gap-2 bg-slate-900/60 p-2.5 rounded border border-slate-800">
                            <div>
                              <span className="text-slate-500 text-[10px] block">Target Entity:</span>
                              <span className="text-cyber-cyan font-bold break-all">{data.entity_id}</span>
                            </div>
                            <div>
                              <span className="text-slate-500 text-[10px] block">Entity Type:</span>
                              <span className="text-slate-200 font-semibold">{data.entity_type}</span>
                            </div>
                            <div>
                              <span className="text-slate-500 text-[10px] block">ML Anomaly Score:</span>
                              <span className="text-cyber-emerald font-bold">{data.anomaly_score.toFixed(4)}</span>
                            </div>
                          </div>

                          {/* Triggering Feature Deviations */}
                          {data.triggering_reasons && data.triggering_reasons.length > 0 && (
                            <div className="space-y-1">
                              <span className="text-[10px] uppercase tracking-wider text-slate-400 font-bold block">
                                Triggering Population Outlier Factors:
                              </span>
                              <div className="flex flex-wrap gap-1.5">
                                {data.triggering_reasons.map((r: string, idx: number) => (
                                  <span
                                    key={idx}
                                    className="px-2 py-1 rounded bg-slate-900 border border-cyber-cyan/30 text-slate-200 text-[11px]"
                                  >
                                    ⚡ {r}
                                  </span>
                                ))}
                              </div>
                            </div>
                          )}
                        </div>
                      )}
                    </div>
                  </div>
                );
              })()}

              {/* STAGE 2: CONTEXTUAL VALIDATION */}
              {(() => {
                const stage = replay.stages.find((s) => s.stage_id === 'contextual_validation');
                const isExpanded = expandedStages['contextual_validation'];
                if (!stage) return null;
                const data = stage.data;

                return (
                  <div className="relative space-y-2">
                    <div className="absolute -left-6 sm:-left-8 top-1 w-6 h-6 rounded-full bg-slate-900 border border-cyber-emerald flex items-center justify-center text-[10px] font-bold text-cyber-emerald shadow-[0_0_8px_rgba(16,185,129,0.4)]">
                      2
                    </div>

                    <div className="cyber-card p-4 rounded-xl border border-slate-800 bg-slate-950/70 space-y-3">
                      <div
                        onClick={() => toggleStage('contextual_validation')}
                        className="flex items-center justify-between cursor-pointer select-none"
                      >
                        <div className="flex items-center gap-2">
                          {getStageIcon('contextual_validation')}
                          <span className="font-bold text-slate-100 uppercase text-xs tracking-wider">
                            2. Contextual Validation
                          </span>
                          <span className="text-[10px] px-2 py-0.5 rounded bg-cyber-emerald/10 text-cyber-emerald border border-cyber-emerald/30">
                            Behavioral Context
                          </span>
                        </div>
                        <div className="flex items-center gap-3">
                          <span className="text-[11px] text-slate-400">
                            Validation: <strong className="text-cyber-emerald font-bold">{(data.validation_score).toFixed(2)}</strong> | Confidence: <strong className="text-amber-400">{data.confidence_percentage}%</strong>
                          </span>
                          {isExpanded ? <ChevronUp className="w-4 h-4 text-slate-400" /> : <ChevronDown className="w-4 h-4 text-slate-400" />}
                        </div>
                      </div>

                      {isExpanded && (
                        <div className="space-y-3 pt-2 border-t border-slate-800 text-xs">
                          <div className="p-3 rounded bg-blue-950/20 border border-blue-800/40 text-slate-200 text-[11px] leading-relaxed">
                            <div className="flex items-center gap-1.5 text-cyber-cyan font-bold mb-1">
                              <Info className="w-3.5 h-3.5" />
                              <span>Validation Reasoning</span>
                            </div>
                            <p>{data.validation_explanation}</p>
                          </div>

                          <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 bg-slate-900/60 p-2.5 rounded border border-slate-800">
                            <div>
                              <span className="text-slate-500 text-[10px] block">Raw Anomaly:</span>
                              <span className="text-cyber-cyan font-bold">{data.raw_anomaly_score?.toFixed(2)}</span>
                            </div>
                            <div>
                              <span className="text-slate-500 text-[10px] block">Validation Score:</span>
                              <span className="text-cyber-emerald font-bold">{data.validation_score?.toFixed(2)}</span>
                            </div>
                            <div>
                              <span className="text-slate-500 text-[10px] block">Context Confidence:</span>
                              <span className="text-amber-400 font-bold">{data.confidence_percentage}%</span>
                            </div>
                            <div>
                              <span className="text-slate-500 text-[10px] block">Score Adjustment:</span>
                              <span className={`font-bold ${data.score_adjustment >= 0 ? 'text-cyber-emerald' : 'text-slate-400'}`}>
                                {data.score_adjustment >= 0 ? `+${data.score_adjustment.toFixed(2)}` : data.score_adjustment.toFixed(2)}
                              </span>
                            </div>
                          </div>
                        </div>
                      )}
                    </div>
                  </div>
                );
              })()}

              {/* STAGE 3: HISTORICAL BASELINE COMPARISON */}
              {(() => {
                const stage = replay.stages.find((s) => s.stage_id === 'historical_baseline');
                const isExpanded = expandedStages['historical_baseline'];
                if (!stage) return null;
                const data = stage.data;

                return (
                  <div className="relative space-y-2">
                    <div className="absolute -left-6 sm:-left-8 top-1 w-6 h-6 rounded-full bg-slate-900 border border-amber-400 flex items-center justify-center text-[10px] font-bold text-amber-400 shadow-[0_0_8px_rgba(251,191,36,0.4)]">
                      3
                    </div>

                    <div className="cyber-card p-4 rounded-xl border border-slate-800 bg-slate-950/70 space-y-3">
                      <div
                        onClick={() => toggleStage('historical_baseline')}
                        className="flex items-center justify-between cursor-pointer select-none"
                      >
                        <div className="flex items-center gap-2">
                          {getStageIcon('historical_baseline')}
                          <span className="font-bold text-slate-100 uppercase text-xs tracking-wider">
                            3. Historical Baseline Comparison
                          </span>
                          <span className={`text-[10px] px-2 py-0.5 rounded border ${
                            data.has_sufficient_history
                              ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/30'
                              : 'bg-amber-500/10 text-amber-400 border-amber-500/30'
                          }`}>
                            {data.profile_reliability}
                          </span>
                        </div>
                        <div className="flex items-center gap-3">
                          <span className="text-[11px] text-slate-400">
                            History: <strong className="text-slate-200">{data.observation_count}</strong> txs observed
                          </span>
                          {isExpanded ? <ChevronUp className="w-4 h-4 text-slate-400" /> : <ChevronDown className="w-4 h-4 text-slate-400" />}
                        </div>
                      </div>

                      {isExpanded && (
                        <div className="space-y-3 pt-2 border-t border-slate-800 text-xs">
                          {data.what_changed && (
                            <div className="p-3 rounded bg-amber-950/20 border border-amber-800/40 text-slate-200 text-[11px] leading-relaxed">
                              <div className="flex items-center gap-1.5 text-amber-400 font-bold mb-1">
                                <TrendingUp className="w-3.5 h-3.5" />
                                <span>What Changed Against Entity's Own Baseline?</span>
                              </div>
                              <p>{data.what_changed}</p>
                            </div>
                          )}

                          {data.has_sufficient_history ? (
                            <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 bg-slate-900/60 p-2.5 rounded border border-slate-800 text-[11px]">
                              <div>
                                <span className="text-slate-500 text-[10px] block">Baseline Tx Velocity:</span>
                                <span className="text-slate-200 font-bold">{data.historical_metrics?.avg_velocity_per_hour ?? 'N/A'} tx/hr</span>
                              </div>
                              <div>
                                <span className="text-slate-500 text-[10px] block">Baseline Avg Amount:</span>
                                <span className="text-slate-200 font-bold">{data.historical_metrics?.avg_amount ?? 'N/A'} BTC</span>
                              </div>
                              <div>
                                <span className="text-slate-500 text-[10px] block">Prior Counterparties:</span>
                                <span className="text-slate-200 font-bold">{data.historical_metrics?.counterparties_count ?? 'N/A'} peers</span>
                              </div>
                              <div>
                                <span className="text-slate-500 text-[10px] block">Observations:</span>
                                <span className="text-slate-200 font-bold">{data.observation_count} records</span>
                              </div>
                            </div>
                          ) : (
                            <div className="p-2.5 rounded bg-slate-900/80 border border-slate-800 text-slate-400 text-[11px]">
                              <span className="text-amber-400 font-semibold">Insufficient Prior History: </span>
                              Fewer than {data.min_required_observations} prior observations recorded. Baseline is constructed dynamically without fabricating data.
                            </div>
                          )}
                        </div>
                      )}
                    </div>
                  </div>
                );
              })()}

              {/* STAGE 4: EVIDENCE COLLECTED */}
              {(() => {
                const stage = replay.stages.find((s) => s.stage_id === 'evidence_collected');
                const isExpanded = expandedStages['evidence_collected'];
                if (!stage) return null;
                const data = stage.data;

                return (
                  <div className="relative space-y-2">
                    <div className="absolute -left-6 sm:-left-8 top-1 w-6 h-6 rounded-full bg-slate-900 border border-purple-400 flex items-center justify-center text-[10px] font-bold text-purple-400 shadow-[0_0_8px_rgba(192,132,252,0.4)]">
                      4
                    </div>

                    <div className="cyber-card p-4 rounded-xl border border-slate-800 bg-slate-950/70 space-y-3">
                      <div
                        onClick={() => toggleStage('evidence_collected')}
                        className="flex items-center justify-between cursor-pointer select-none"
                      >
                        <div className="flex items-center gap-2">
                          {getStageIcon('evidence_collected')}
                          <span className="font-bold text-slate-100 uppercase text-xs tracking-wider">
                            4. Evidence Collected & Synthesized
                          </span>
                          <span className="text-[10px] px-2 py-0.5 rounded bg-purple-500/10 text-purple-400 border border-purple-500/30">
                            Multi-Layer Evidence
                          </span>
                        </div>
                        <div className="flex items-center gap-3">
                          <span className="text-[11px] text-slate-400">
                            Supporting: <strong className="text-emerald-400 font-bold">{(data.supporting_evidence || []).length}</strong> | Counter: <strong className="text-amber-400">{(data.counter_evidence || []).length}</strong>
                          </span>
                          {isExpanded ? <ChevronUp className="w-4 h-4 text-slate-400" /> : <ChevronDown className="w-4 h-4 text-slate-400" />}
                        </div>
                      </div>

                      {isExpanded && (
                        <div className="space-y-3 pt-2 border-t border-slate-800 text-xs">
                          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                            {/* Supporting Evidence Items */}
                            <div className="space-y-1.5">
                              <span className="text-[10px] uppercase tracking-wider text-emerald-400 font-bold flex items-center gap-1">
                                <CheckCircle2 className="w-3 h-3" />
                                <span>Supporting Evidence ({(data.supporting_evidence || []).length})</span>
                              </span>
                              {(data.supporting_evidence || []).length === 0 ? (
                                <p className="text-[11px] text-slate-500 italic">No specific behavioral deviations identified.</p>
                              ) : (
                                <div className="space-y-1.5">
                                  {data.supporting_evidence.map((ev: any, idx: number) => (
                                    <div key={idx} className="p-2 rounded bg-emerald-950/20 border border-emerald-800/30 text-[11px]">
                                      <div className="font-semibold text-emerald-300">{ev.reason}</div>
                                      <div className="text-[10px] text-emerald-400/70 mt-0.5 font-mono">
                                        Feature: {ev.feature} | Observed: {String(ev.observed_value)} | Baseline: {String(ev.baseline_value)}
                                      </div>
                                    </div>
                                  ))}
                                </div>
                              )}
                            </div>

                            {/* Counter-Evidence Items */}
                            <div className="space-y-1.5">
                              <span className="text-[10px] uppercase tracking-wider text-amber-400 font-bold flex items-center gap-1">
                                <Scale className="w-3 h-3" />
                                <span>Counter-Evidence / Normalcy ({(data.counter_evidence || []).length})</span>
                              </span>
                              {(data.counter_evidence || []).length === 0 ? (
                                <p className="text-[11px] text-slate-500 italic">No mitigating counter-evidence observed.</p>
                              ) : (
                                <div className="space-y-1.5">
                                  {data.counter_evidence.map((cev: any, idx: number) => (
                                    <div key={idx} className="p-2 rounded bg-amber-950/20 border border-amber-800/30 text-[11px]">
                                      <div className="font-semibold text-amber-300">{cev.reason}</div>
                                      <div className="text-[10px] text-amber-400/70 mt-0.5 font-mono">
                                        Feature: {cev.feature} | Observed: {String(cev.observed_value)}
                                      </div>
                                    </div>
                                  ))}
                                </div>
                              )}
                            </div>
                          </div>

                          {/* Related Transactions & Network IPs */}
                          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 pt-2 border-t border-slate-800">
                            <div>
                              <span className="text-[10px] uppercase tracking-wider text-slate-400 font-bold block mb-1">
                                Associated Transaction IDs:
                              </span>
                              <div className="flex flex-wrap gap-1">
                                {(data.related_transactions || []).length === 0 ? (
                                  <span className="text-slate-500 text-[11px] italic">None recorded</span>
                                ) : (
                                  data.related_transactions.map((tx: string) => (
                                    <Link
                                      key={tx}
                                      to={`/entities/${encodeURIComponent(tx)}`}
                                      target="_blank"
                                      className="px-2 py-0.5 rounded bg-slate-900 border border-slate-700 text-cyber-cyan hover:border-cyber-cyan text-[11px] transition-colors inline-flex items-center gap-1"
                                    >
                                      <span>{tx.length > 16 ? `${tx.slice(0, 10)}...` : tx}</span>
                                      <ExternalLink className="w-2.5 h-2.5" />
                                    </Link>
                                  ))
                                )}
                              </div>
                            </div>

                            <div>
                              <span className="text-[10px] uppercase tracking-wider text-slate-400 font-bold block mb-1">
                                Corroborated Network Wire IPs:
                              </span>
                              <div className="flex flex-wrap gap-1">
                                {(data.observed_ips || []).length === 0 ? (
                                  <span className="text-slate-500 text-[11px] italic">None recorded</span>
                                ) : (
                                  data.observed_ips.map((ip: string) => (
                                    <Link
                                      key={ip}
                                      to={`/entities/${encodeURIComponent(ip)}`}
                                      target="_blank"
                                      className="px-2 py-0.5 rounded bg-slate-900 border border-slate-700 text-cyber-purple hover:border-purple-400 text-[11px] transition-colors inline-flex items-center gap-1"
                                    >
                                      <Radio className="w-2.5 h-2.5" />
                                      <span>{ip}</span>
                                    </Link>
                                  ))
                                )}
                              </div>
                            </div>
                          </div>
                        </div>
                      )}
                    </div>
                  </div>
                );
              })()}

              {/* STAGE 5: GRAPH / FUND-FLOW INVESTIGATION */}
              {(() => {
                const stage = replay.stages.find((s) => s.stage_id === 'graph_investigation');
                const isExpanded = expandedStages['graph_investigation'];
                if (!stage) return null;
                const data = stage.data;

                return (
                  <div className="relative space-y-2">
                    <div className="absolute -left-6 sm:-left-8 top-1 w-6 h-6 rounded-full bg-slate-900 border border-blue-400 flex items-center justify-center text-[10px] font-bold text-blue-400 shadow-[0_0_8px_rgba(96,165,250,0.4)]">
                      5
                    </div>

                    <div className="cyber-card p-4 rounded-xl border border-slate-800 bg-slate-950/70 space-y-3">
                      <div
                        onClick={() => toggleStage('graph_investigation')}
                        className="flex items-center justify-between cursor-pointer select-none"
                      >
                        <div className="flex items-center gap-2">
                          {getStageIcon('graph_investigation')}
                          <span className="font-bold text-slate-100 uppercase text-xs tracking-wider">
                            5. Graph / Fund-Flow Investigation
                          </span>
                          <span className="text-[10px] px-2 py-0.5 rounded bg-blue-500/10 text-blue-400 border border-blue-500/30">
                            {data.k_hop_depth}-Hop Ego Network
                          </span>
                        </div>
                        <div className="flex items-center gap-3">
                          <span className="text-[11px] text-slate-400">
                            Nodes: <strong className="text-cyber-emerald">{data.total_connected_nodes}</strong> | Edges: <strong className="text-cyber-cyan">{data.total_connected_edges}</strong>
                          </span>
                          {isExpanded ? <ChevronUp className="w-4 h-4 text-slate-400" /> : <ChevronDown className="w-4 h-4 text-slate-400" />}
                        </div>
                      </div>

                      {isExpanded && (
                        <div className="space-y-3 pt-2 border-t border-slate-800 text-xs">
                          <p className="text-slate-300 text-[11px] leading-relaxed">
                            {stage.summary}
                          </p>

                          {/* Embedded Cytoscape Graph Canvas for Local Fund-Flow */}
                          {replay.graph_data && replay.graph_data.nodes && replay.graph_data.nodes.length > 0 ? (
                            <div className="rounded-lg overflow-hidden border border-slate-800">
                              <CytoscapeGraph
                                data={replay.graph_data}
                                focalNodeId={replay.entity_id}
                                height="320px"
                              />
                            </div>
                          ) : (
                            <div className="p-4 rounded bg-slate-900/60 border border-slate-800 text-center text-slate-500">
                              Sub-graph relationships mapped from connected transaction ledger.
                            </div>
                          )}

                          {/* Fund Flow Transfers Table */}
                          {data.fund_flow_transfers && data.fund_flow_transfers.length > 0 && (
                            <div className="space-y-1">
                              <span className="text-[10px] uppercase tracking-wider text-slate-400 font-bold block">
                                Traced Value-Flow Transfer Links:
                              </span>
                              <div className="overflow-x-auto">
                                <table className="w-full text-left text-[11px] border border-slate-800/80 rounded">
                                  <thead>
                                    <tr className="bg-slate-900/80 text-slate-400 border-b border-slate-800 text-[10px]">
                                      <th className="p-1.5">Source Entity</th>
                                      <th className="p-1.5">Direction</th>
                                      <th className="p-1.5">Target Entity</th>
                                      <th className="p-1.5">Amount (BTC)</th>
                                    </tr>
                                  </thead>
                                  <tbody className="divide-y divide-slate-800/40 text-slate-300">
                                    {data.fund_flow_transfers.map((ff: any, i: number) => (
                                      <tr key={i} className="hover:bg-slate-900/40">
                                        <td className="p-1.5 text-cyber-cyan truncate max-w-[120px]">{ff.source}</td>
                                        <td className="p-1.5 text-cyber-emerald font-bold">→ {ff.type}</td>
                                        <td className="p-1.5 text-cyber-cyan truncate max-w-[120px]">{ff.target}</td>
                                        <td className="p-1.5 text-slate-200 font-semibold">{ff.amount ? `${ff.amount} BTC` : '-'}</td>
                                      </tr>
                                    ))}
                                  </tbody>
                                </table>
                              </div>
                            </div>
                          )}

                          {/* Quick Navigation to Full Graph Explorer */}
                          <div className="flex justify-end pt-1">
                            <button
                              onClick={() => {
                                onClose();
                                navigate('/graph');
                              }}
                              className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded bg-blue-600/20 hover:bg-blue-600/30 text-blue-300 border border-blue-500/40 text-[11px] font-bold transition-colors"
                            >
                              <span>Open in Full Graph Explorer</span>
                              <ExternalLink className="w-3 h-3" />
                            </button>
                          </div>
                        </div>
                      )}
                    </div>
                  </div>
                );
              })()}

              {/* STAGE 6: INVESTIGATIVE LEAD */}
              {(() => {
                const stage = replay.stages.find((s) => s.stage_id === 'investigative_lead');
                const isExpanded = expandedStages['investigative_lead'];
                if (!stage) return null;
                const data = stage.data;

                return (
                  <div className="relative space-y-2">
                    <div className="absolute -left-6 sm:-left-8 top-1 w-6 h-6 rounded-full bg-slate-900 border border-red-500 flex items-center justify-center text-[10px] font-bold text-red-400 shadow-[0_0_8px_rgba(239,68,68,0.4)]">
                      6
                    </div>

                    <div className="cyber-card p-4 rounded-xl border border-red-500/40 bg-gradient-to-b from-red-950/10 to-slate-950/80 space-y-3">
                      <div
                        onClick={() => toggleStage('investigative_lead')}
                        className="flex items-center justify-between cursor-pointer select-none"
                      >
                        <div className="flex items-center gap-2">
                          {getStageIcon('investigative_lead')}
                          <span className="font-bold text-slate-100 uppercase text-xs tracking-wider">
                            6. Investigative Lead & Prioritization
                          </span>
                          <Badge variant={data.severity.toLowerCase() as any}>
                            {data.severity}
                          </Badge>
                        </div>
                        <div className="flex items-center gap-3">
                          <span className="text-[11px] text-slate-400">
                            Priority: <strong className="text-red-400 font-bold">{data.priority_score}/100</strong>
                          </span>
                          {isExpanded ? <ChevronUp className="w-4 h-4 text-slate-400" /> : <ChevronDown className="w-4 h-4 text-slate-400" />}
                        </div>
                      </div>

                      {isExpanded && (
                        <div className="space-y-3 pt-2 border-t border-slate-800 text-xs">
                          <p className="text-slate-300 text-[11px] leading-relaxed">
                            {stage.summary}
                          </p>

                          <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 bg-slate-900/60 p-2.5 rounded border border-slate-800 text-[11px]">
                            <div>
                              <span className="text-slate-500 text-[10px] block">Lead Identifier:</span>
                              <span className="text-slate-200 font-mono font-bold truncate max-w-[120px] block">{data.lead_id}</span>
                            </div>
                            <div>
                              <span className="text-slate-500 text-[10px] block">Risk Priority:</span>
                              <span className="text-red-400 font-bold">{data.priority_score}/100</span>
                            </div>
                            <div>
                              <span className="text-slate-500 text-[10px] block">Triage Status:</span>
                              <span className="text-cyber-cyan font-bold">{data.status}</span>
                            </div>
                            <div>
                              <span className="text-slate-500 text-[10px] block">Assigned Analyst:</span>
                              <span className="text-slate-300 font-semibold">{data.assigned_to || 'Unassigned'}</span>
                            </div>
                          </div>

                          {/* Quick Actions to jump to related components */}
                          <div className="flex flex-wrap items-center justify-between gap-2 pt-2 border-t border-slate-800">
                            <span className="text-[10px] text-slate-500">
                              Investigator Options:
                            </span>
                            <div className="flex items-center gap-2">
                              <Link
                                to={`/entities/${encodeURIComponent(replay.entity_id)}`}
                                onClick={onClose}
                                className="px-3 py-1.5 rounded bg-cyber-emerald text-slate-950 font-bold hover:bg-emerald-400 text-[11px] transition-all flex items-center gap-1.5 shadow-glow-emerald"
                              >
                                <span>Inspect Full Entity Dossier</span>
                                <ExternalLink className="w-3 h-3" />
                              </Link>
                              <Link
                                to="/reports"
                                onClick={onClose}
                                className="px-3 py-1.5 rounded bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 text-[11px] font-semibold transition-colors flex items-center gap-1"
                              >
                                <FileSpreadsheet className="w-3 h-3" />
                                <span>Export Lead Report</span>
                              </Link>
                            </div>
                          </div>
                        </div>
                      )}
                    </div>
                  </div>
                );
              })()}
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="p-3 sm:p-4 border-t border-cyber-border bg-slate-950 flex items-center justify-between text-[11px] text-slate-400 font-mono shrink-0">
          <span className="flex items-center gap-1.5">
            <CheckCircle2 className="w-3.5 h-3.5 text-cyber-emerald" />
            <span>Audit-ready timeline reconstructed strictly from recorded pipeline state. Zero fabricated data.</span>
          </span>
          <button
            onClick={onClose}
            className="px-4 py-1.5 rounded bg-slate-800 hover:bg-slate-700 text-slate-200 font-bold transition-colors"
          >
            Close Replay
          </button>
        </div>
      </div>
    </div>
  );
};
