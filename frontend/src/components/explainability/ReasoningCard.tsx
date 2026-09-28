import React, { useState } from 'react';
import { AlertTriangle, TrendingUp, Zap, ShieldCheck, ChevronDown, ChevronUp, Scale, CheckCircle2, Info } from 'lucide-react';

interface ReasoningCardProps {
  reasons: string[];
  severity: string;
  anomalyScore: number;
  priorityScore: number;
  rawAnomalyScore?: number;
  validationScore?: number;
  confidence?: number;
  supportingEvidence?: Array<{
    feature: string;
    observed_value: any;
    baseline_value: any;
    deviation_type: string;
    reason: string;
  }>;
  counterEvidence?: Array<{
    feature: string;
    observed_value: any;
    baseline_value: any;
    counter_type: string;
    reason: string;
  }>;
  behaviouralDeviation?: Record<string, any>;
  historicalContext?: Record<string, any>;
  validationExplanation?: string;
}

export const ReasoningCard: React.FC<ReasoningCardProps> = ({
  reasons,
  severity,
  anomalyScore,
  priorityScore,
  rawAnomalyScore,
  validationScore,
  confidence,
  supportingEvidence = [],
  counterEvidence = [],
  behaviouralDeviation = {},
  historicalContext = {},
  validationExplanation,
}) => {
  const [isWhyValidatedOpen, setIsWhyValidatedOpen] = useState(true);

  const displayRawAnomaly = rawAnomalyScore !== undefined ? rawAnomalyScore : anomalyScore;
  const displayValScore = validationScore !== undefined ? validationScore : anomalyScore;
  const displayConfidence = confidence !== undefined ? `${Math.round(confidence * 100)}%` : '85%';

  const hasHistoricalBaseline = historicalContext?.has_sufficient_history === true;

  return (
    <div className="cyber-card p-5 space-y-4">
      {/* Header with Scores */}
      <div className="flex flex-wrap items-center justify-between border-b border-cyber-border pb-3 gap-2">
        <div className="flex items-center gap-2">
          <Zap className="w-4 h-4 text-cyber-emerald" />
          <h3 className="text-sm font-semibold text-slate-100 uppercase tracking-wider font-mono">
            Detection & Contextual Validation
          </h3>
        </div>
        <div className="flex items-center gap-4 text-xs font-mono">
          <div className="bg-slate-900/80 px-2.5 py-1 rounded border border-slate-800">
            <span className="text-slate-400">Raw Anomaly: </span>
            <span className="text-cyber-cyan font-bold">{displayRawAnomaly.toFixed(2)}</span>
          </div>
          <div className="bg-slate-900/80 px-2.5 py-1 rounded border border-slate-800">
            <span className="text-slate-400">Validation Score: </span>
            <span className="text-cyber-emerald font-bold">{displayValScore.toFixed(2)}</span>
          </div>
          <div className="bg-slate-900/80 px-2.5 py-1 rounded border border-slate-800">
            <span className="text-slate-400">Confidence: </span>
            <span className="text-amber-400 font-bold">{displayConfidence}</span>
          </div>
        </div>
      </div>

      {/* Population Feature Deviations */}
      <div className="space-y-2">
        <div className="text-xs font-semibold text-slate-300 font-mono flex items-center gap-1.5">
          <span>Population Benchmark Deviations:</span>
        </div>
        <div className="space-y-2">
          {reasons.length === 0 ? (
            <p className="text-xs text-slate-400 font-mono">No specific statistical deviations recorded.</p>
          ) : (
            reasons.map((reason, idx) => (
              <div
                key={idx}
                className="flex items-start gap-2.5 p-2.5 rounded-lg bg-slate-900/60 border border-slate-800/80 text-xs text-slate-200 font-mono"
              >
                <div className="mt-0.5 shrink-0">
                  {severity === 'CRITICAL' ? (
                    <AlertTriangle className="w-3.5 h-3.5 text-red-400" />
                  ) : severity === 'HIGH' ? (
                    <TrendingUp className="w-3.5 h-3.5 text-orange-400" />
                  ) : (
                    <ShieldCheck className="w-3.5 h-3.5 text-cyber-emerald" />
                  )}
                </div>
                <span className="leading-relaxed">{reason}</span>
              </div>
            ))
          )}
        </div>
      </div>

      {/* Expandable Section: Why validated? */}
      <div className="border border-slate-800 rounded-lg overflow-hidden bg-slate-900/40">
        <button
          type="button"
          onClick={() => setIsWhyValidatedOpen(!isWhyValidatedOpen)}
          className="w-full flex items-center justify-between px-3.5 py-2.5 bg-slate-800/40 hover:bg-slate-800/60 transition-colors text-xs font-mono font-semibold text-slate-200"
        >
          <div className="flex items-center gap-2">
            <Scale className="w-3.5 h-3.5 text-cyber-cyan" />
            <span className="uppercase tracking-wider">Why validated? Contextual Behavioral Analysis</span>
          </div>
          <div className="flex items-center gap-2">
            <span className="text-[10px] text-slate-400">
              {supportingEvidence.length} supporting / {counterEvidence.length} counter
            </span>
            {isWhyValidatedOpen ? (
              <ChevronUp className="w-4 h-4 text-slate-400" />
            ) : (
              <ChevronDown className="w-4 h-4 text-slate-400" />
            )}
          </div>
        </button>

        {isWhyValidatedOpen && (
          <div className="p-3.5 space-y-3.5 text-xs font-mono border-t border-slate-800">
            {/* Validation Explanation */}
            {validationExplanation && (
              <div className="p-3 rounded bg-blue-500/10 border border-blue-500/20 text-slate-200 leading-relaxed">
                <div className="flex items-center gap-1.5 text-cyber-cyan font-bold mb-1">
                  <Info className="w-3.5 h-3.5" />
                  <span>Validation Explanation</span>
                </div>
                <p className="text-[11px] text-slate-300">{validationExplanation}</p>
              </div>
            )}

            {/* What Changed? (Learned Behavioral Deviations) */}
            {behaviouralDeviation?.what_changed && (
              <div className="p-3 rounded bg-amber-500/10 border border-amber-500/20 text-slate-200 leading-relaxed">
                <div className="flex items-center gap-1.5 text-amber-400 font-bold mb-1">
                  <TrendingUp className="w-3.5 h-3.5" />
                  <span className="uppercase tracking-wider">What Changed? (Learned Behavioral Deviations)</span>
                </div>
                <p className="text-[11px] text-slate-300">{behaviouralDeviation.what_changed}</p>
              </div>
            )}

            {/* Supporting Evidence */}
            <div className="space-y-1.5">
              <span className="text-[11px] uppercase tracking-wider text-emerald-400 font-bold flex items-center gap-1">
                <CheckCircle2 className="w-3 h-3" /> Supporting Evidence ({supportingEvidence.length})
              </span>
              {supportingEvidence.length === 0 ? (
                <p className="text-[11px] text-slate-500 italic pl-4">
                  No historical behavioral deviations identified to support this anomaly.
                </p>
              ) : (
                <div className="space-y-1.5">
                  {supportingEvidence.map((ev, i) => (
                    <div
                      key={i}
                      className="p-2 rounded bg-emerald-950/20 border border-emerald-800/40 text-[11px] text-emerald-200"
                    >
                      <div className="font-semibold text-emerald-300">{ev.reason}</div>
                      <div className="text-[10px] text-emerald-400/70 mt-0.5">
                        Feature: <span className="font-mono text-slate-300">{ev.feature}</span> | Observed: <span className="font-mono text-slate-200">{String(ev.observed_value)}</span> | Baseline: <span className="font-mono text-slate-200">{String(ev.baseline_value)}</span>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>

            {/* Counter-Evidence */}
            <div className="space-y-1.5">
              <span className="text-[11px] uppercase tracking-wider text-amber-400 font-bold flex items-center gap-1">
                <Scale className="w-3 h-3" /> Counter-Evidence & Normalcy Indicators ({counterEvidence.length})
              </span>
              {counterEvidence.length === 0 ? (
                <p className="text-[11px] text-slate-500 italic pl-4">
                  No mitigating counter-evidence found.
                </p>
              ) : (
                <div className="space-y-1.5">
                  {counterEvidence.map((cev, i) => (
                    <div
                      key={i}
                      className="p-2 rounded bg-amber-950/20 border border-amber-800/40 text-[11px] text-amber-200"
                    >
                      <div className="font-semibold text-amber-300">{cev.reason}</div>
                      <div className="text-[10px] text-amber-400/70 mt-0.5">
                        Feature: <span className="font-mono text-slate-300">{cev.feature}</span> | Observed: <span className="font-mono text-slate-200">{String(cev.observed_value)}</span>
                        {cev.baseline_value !== null && cev.baseline_value !== undefined && (
                          <> | Baseline: <span className="font-mono text-slate-200">{String(cev.baseline_value)}</span></>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>

            {/* Historical Baseline Comparison */}
            <div className="space-y-1.5 pt-1 border-t border-slate-800">
              <div className="flex items-center justify-between">
                <span className="text-[11px] uppercase tracking-wider text-slate-400 font-bold">
                  What is Normal Behaviour for this Entity? (Learned History)
                </span>
                {historicalContext?.profile_reliability && (
                  <span className="text-[10px] px-2 py-0.5 rounded bg-slate-800 text-slate-300 font-mono">
                    Reliability: <span className="text-cyber-cyan font-bold">{historicalContext.profile_reliability}</span>
                  </span>
                )}
              </div>
              {hasHistoricalBaseline ? (
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 text-[10px] bg-slate-900/80 p-2.5 rounded border border-slate-800">
                  <div>
                    <span className="text-slate-500 block">Baseline Tx Velocity:</span>
                    <span className="text-slate-200 font-bold">
                      {historicalContext.transaction_velocity ?? historicalContext.avg_velocity_per_hour ?? 'N/A'} tx/hr
                    </span>
                  </div>
                  <div>
                    <span className="text-slate-500 block">Baseline Median Amount:</span>
                    <span className="text-slate-200 font-bold">
                      {historicalContext.median_output_amount ?? historicalContext.avg_amount ?? 'N/A'} BTC
                    </span>
                  </div>
                  <div>
                    <span className="text-slate-500 block">Baseline Counterparties:</span>
                    <span className="text-slate-200 font-bold">
                      {historicalContext.unique_counterparty_count ?? historicalContext.counterparties_count ?? 'N/A'} peers
                    </span>
                  </div>
                  <div>
                    <span className="text-slate-500 block">Historical Observations:</span>
                    <span className="text-slate-200 font-bold">
                      {historicalContext.observation_count ?? 'N/A'} txs
                    </span>
                  </div>
                </div>
              ) : (
                <div className="text-[11px] text-slate-400 bg-slate-900/60 p-2 rounded border border-slate-800">
                  <span className="text-amber-400 font-semibold">Insufficient Historical Context: </span>
                  {historicalContext?.message || 'Fewer than minimum required historical observations recorded for this entity. Baseline not fabricated.'}
                </div>
              )}
            </div>
          </div>
        )}
      </div>

      <div className="text-[11px] text-slate-500 font-mono border-t border-slate-800 pt-2 flex items-center gap-1.5">
        <ShieldCheck className="w-3.5 h-3.5 text-slate-400 shrink-0" />
        <span>Contextual validation layer correlates Isolation Forest anomaly score against entity's own historical baseline.</span>
      </div>
    </div>
  );
};
