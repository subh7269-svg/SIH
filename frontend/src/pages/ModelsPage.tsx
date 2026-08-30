import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  Cpu,
  CheckCircle2,
  TrendingUp,
  RefreshCw,
  Layers,
  ShieldCheck,
  Zap,
  Sliders,
  Scale
} from 'lucide-react';
import { getModels, trainModel } from '../services/api';
import { Badge } from '../components/common/Badge';

export const ModelsPage: React.FC = () => {
  const queryClient = useQueryClient();
  const [modelType, setModelType] = useState('ISOLATION_FOREST');
  const [contamination, setContamination] = useState<number>(0.08);

  const { data: models, isLoading } = useQuery({
    queryKey: ['models'],
    queryFn: getModels,
  });

  const trainMutation = useMutation({
    mutationFn: trainModel,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['models'] });
      queryClient.invalidateQueries({ queryKey: ['alerts'] });
    },
  });

  const handleTrainSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    trainMutation.mutate({
      model_type: modelType,
      contamination,
    });
  };

  const latestModel = models?.[0];
  const evalMetrics = latestModel?.evaluation_metrics;
  const baselineComp = evalMetrics?.baseline_comparison;

  return (
    <div className="space-y-6 font-mono">
      {/* Header */}
      <div className="border-b border-cyber-border pb-4">
        <h1 className="text-xl font-bold text-slate-100 flex items-center gap-2">
          <Cpu className="w-5 h-5 text-cyber-emerald" />
          <span>ML MODEL STUDIO & RIGOROUS EVALUATION BENCHMARK</span>
        </h1>
        <p className="text-xs text-slate-400 mt-1">
          Genuine Isolation Forest anomaly detection compared side-by-side against Local Outlier Factor (LOF) baseline.
        </p>
      </div>

      {/* Retrain Parameter Form */}
      <div className="cyber-card p-5 space-y-4">
        <div className="flex items-center justify-between border-b border-cyber-border pb-3">
          <div className="flex items-center gap-2">
            <Sliders className="w-4 h-4 text-cyber-cyan" />
            <h2 className="text-sm font-semibold text-slate-100 uppercase tracking-wider">
              Train / Update Anomaly Detection Model
            </h2>
          </div>
        </div>

        <form onSubmit={handleTrainSubmit} className="grid grid-cols-1 sm:grid-cols-3 gap-4 items-end text-xs">
          <div>
            <label className="block text-slate-400 mb-1">Algorithm Selection</label>
            <select
              value={modelType}
              onChange={(e) => setModelType(e.target.value)}
              className="w-full bg-slate-900 border border-slate-700 rounded-lg p-2 text-slate-100 focus:outline-none focus:border-cyber-emerald"
            >
              <option value="ISOLATION_FOREST">Isolation Forest (Primary - 100 Trees)</option>
              <option value="LOCAL_OUTLIER_FACTOR">Local Outlier Factor (LOF Baseline)</option>
            </select>
          </div>

          <div>
            <label className="block text-slate-400 mb-1">
              Expected Contamination Rate: <span className="text-cyber-emerald font-bold">{contamination}</span>
            </label>
            <input
              type="range"
              min="0.01"
              max="0.20"
              step="0.01"
              value={contamination}
              onChange={(e) => setContamination(Number(e.target.value))}
              className="w-full accent-cyber-emerald cursor-pointer"
            />
          </div>

          <div>
            <button
              type="submit"
              disabled={trainMutation.isPending}
              className="w-full flex items-center justify-center gap-2 px-4 py-2 bg-cyber-emerald text-slate-950 font-bold rounded-lg hover:bg-emerald-400 transition-all shadow-glow-emerald disabled:opacity-50"
            >
              {trainMutation.isPending ? (
                <>
                  <RefreshCw className="w-4 h-4 animate-spin" />
                  <span>Fitting Model...</span>
                </>
              ) : (
                <>
                  <Zap className="w-4 h-4" />
                  <span>Execute Training & Evaluation</span>
                </>
              )}
            </button>
          </div>
        </form>
      </div>

      {/* Model Benchmark Evaluation Cards */}
      {evalMetrics ? (
        <div className="space-y-4">
          <div className="flex items-center gap-2 text-xs text-slate-400 font-semibold">
            <Scale className="w-4 h-4 text-cyber-emerald" />
            <span>ALGORITHM BENCHMARK PERFORMANCE COMPARISON</span>
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Primary Model (Isolation Forest) */}
            <div className="cyber-card p-5 space-y-4 border-l-4 border-l-cyber-emerald">
              <div className="flex items-center justify-between border-b border-cyber-border pb-3">
                <div>
                  <h3 className="text-sm font-bold text-slate-100">Primary: Isolation Forest</h3>
                  <p className="text-[10px] text-slate-500">Tree-based multidimensional subspace isolation</p>
                </div>
                <Badge variant="success">ACTIVE MODEL</Badge>
              </div>

              <div className="grid grid-cols-2 sm:grid-cols-3 gap-3 text-xs">
                <div className="p-2.5 rounded bg-slate-900 border border-slate-800">
                  <p className="text-[10px] text-slate-500">Precision</p>
                  <p className="text-base font-bold text-cyber-emerald">{(evalMetrics.precision * 100).toFixed(1)}%</p>
                </div>
                <div className="p-2.5 rounded bg-slate-900 border border-slate-800">
                  <p className="text-[10px] text-slate-500">Recall / Detection Rate</p>
                  <p className="text-base font-bold text-cyber-emerald">{(evalMetrics.recall * 100).toFixed(1)}%</p>
                </div>
                <div className="p-2.5 rounded bg-slate-900 border border-slate-800">
                  <p className="text-[10px] text-slate-500">F1 Score</p>
                  <p className="text-base font-bold text-slate-100">{(evalMetrics.f1_score * 100).toFixed(1)}%</p>
                </div>
                <div className="p-2.5 rounded bg-slate-900 border border-slate-800">
                  <p className="text-[10px] text-slate-500">ROC-AUC</p>
                  <p className="text-base font-bold text-cyber-cyan">{evalMetrics.roc_auc.toFixed(3)}</p>
                </div>
                <div className="p-2.5 rounded bg-slate-900 border border-slate-800">
                  <p className="text-[10px] text-slate-500">False Positive Rate</p>
                  <p className="text-base font-bold text-amber-400">{(evalMetrics.false_positive_rate * 100).toFixed(1)}%</p>
                </div>
                <div className="p-2.5 rounded bg-slate-900 border border-slate-800">
                  <p className="text-[10px] text-slate-500">Training Time</p>
                  <p className="text-base font-bold text-slate-200">{latestModel.training_duration_ms} ms</p>
                </div>
              </div>
            </div>

            {/* Baseline Comparison (Local Outlier Factor) */}
            <div className="cyber-card p-5 space-y-4 border-l-4 border-l-cyber-cyan">
              <div className="flex items-center justify-between border-b border-cyber-border pb-3">
                <div>
                  <h3 className="text-sm font-bold text-slate-100">Baseline: Local Outlier Factor (LOF)</h3>
                  <p className="text-[10px] text-slate-500">Density-based local reachability comparison</p>
                </div>
                <Badge variant="info">BASELINE</Badge>
              </div>

              {baselineComp ? (
                <div className="grid grid-cols-2 sm:grid-cols-3 gap-3 text-xs">
                  <div className="p-2.5 rounded bg-slate-900 border border-slate-800">
                    <p className="text-[10px] text-slate-500">Precision</p>
                    <p className="text-base font-bold text-cyber-cyan">{(baselineComp.precision * 100).toFixed(1)}%</p>
                  </div>
                  <div className="p-2.5 rounded bg-slate-900 border border-slate-800">
                    <p className="text-[10px] text-slate-500">Recall</p>
                    <p className="text-base font-bold text-cyber-cyan">{(baselineComp.recall * 100).toFixed(1)}%</p>
                  </div>
                  <div className="p-2.5 rounded bg-slate-900 border border-slate-800">
                    <p className="text-[10px] text-slate-500">F1 Score</p>
                    <p className="text-base font-bold text-slate-100">{(baselineComp.f1_score * 100).toFixed(1)}%</p>
                  </div>
                  <div className="p-2.5 rounded bg-slate-900 border border-slate-800">
                    <p className="text-[10px] text-slate-500">ROC-AUC</p>
                    <p className="text-base font-bold text-slate-300">{baselineComp.roc_auc.toFixed(3)}</p>
                  </div>
                  <div className="p-2.5 rounded bg-slate-900 border border-slate-800">
                    <p className="text-[10px] text-slate-500">PR-AUC</p>
                    <p className="text-base font-bold text-slate-300">{baselineComp.pr_auc.toFixed(3)}</p>
                  </div>
                  <div className="p-2.5 rounded bg-slate-900 border border-slate-800">
                    <p className="text-[10px] text-slate-500">Method</p>
                    <p className="text-base font-bold text-slate-300">k-NN Density</p>
                  </div>
                </div>
              ) : (
                <p className="text-xs text-slate-500">Baseline comparison statistics not available.</p>
              )}
            </div>
          </div>

          <div className="p-3 rounded-lg bg-slate-900/90 border border-slate-800 text-[11px] text-slate-500 flex items-center gap-2">
            <ShieldCheck className="w-4 h-4 text-cyber-emerald shrink-0" />
            <span>{evalMetrics.benchmark_disclaimer}</span>
          </div>
        </div>
      ) : null}

      {/* Feature Space Schema */}
      {latestModel?.feature_names && (
        <div className="cyber-card p-5 space-y-3 text-xs">
          <div className="border-b border-cyber-border pb-2">
            <h3 className="text-sm font-semibold text-slate-100 uppercase tracking-wider">
              Engineered Behavioral Feature Space ({latestModel.feature_names.length} Dimensions)
            </h3>
          </div>
          <div className="flex flex-wrap gap-2">
            {latestModel.feature_names.map((feat) => (
              <span key={feat} className="px-2.5 py-1 rounded bg-slate-900 border border-slate-800 text-slate-300 text-[11px]">
                {feat}
              </span>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};
