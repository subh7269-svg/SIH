import React from 'react';
import { AlertTriangle, CheckCircle2, TrendingUp, Network, Zap, ShieldCheck } from 'lucide-react';

interface ReasoningCardProps {
  reasons: string[];
  severity: string;
  anomalyScore: number;
  priorityScore: number;
}

export const ReasoningCard: React.FC<ReasoningCardProps> = ({
  reasons,
  severity,
  anomalyScore,
  priorityScore,
}) => {
  return (
    <div className="cyber-card p-5 space-y-4">
      <div className="flex items-center justify-between border-b border-cyber-border pb-3">
        <div className="flex items-center gap-2">
          <Zap className="w-4 h-4 text-cyber-emerald" />
          <h3 className="text-sm font-semibold text-slate-100 uppercase tracking-wider font-mono">
            Mathematical Explainability & Rationale
          </h3>
        </div>
        <div className="text-xs font-mono text-slate-400">
          ML Anomaly Score: <span className="text-cyber-emerald font-bold">{anomalyScore.toFixed(2)}</span>
        </div>
      </div>

      <div className="space-y-2.5">
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

      <div className="text-[11px] text-slate-500 font-mono border-t border-slate-800 pt-2 flex items-center gap-1.5">
        <ShieldCheck className="w-3.5 h-3.5 text-slate-400 shrink-0" />
        <span>Reasons derived strictly from empirical feature deviations against population medians.</span>
      </div>
    </div>
  );
};
