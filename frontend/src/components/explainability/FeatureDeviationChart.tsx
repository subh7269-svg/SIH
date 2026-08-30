import React from 'react';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  ReferenceLine,
  Cell,
} from 'recharts';

interface FeatureDeviationChartProps {
  deviations: Record<
    string,
    {
      value: number;
      baseline_mean: number;
      baseline_median: number;
      z_score: number;
      ratio_to_median: number;
    }
  >;
}

export const FeatureDeviationChart: React.FC<FeatureDeviationChartProps> = ({ deviations }) => {
  const chartData = Object.entries(deviations)
    .map(([key, data]) => ({
      feature: key.replace(/_/g, ' '),
      z_score: data.z_score,
      value: data.value,
      baseline: data.baseline_median,
    }))
    .sort((a, b) => Math.abs(b.z_score) - Math.abs(a.z_score))
    .slice(0, 6);

  if (chartData.length === 0) {
    return (
      <div className="p-6 text-center text-xs text-slate-500 font-mono">
        No feature deviation data computed for this entity yet.
      </div>
    );
  }

  return (
    <div className="w-full h-64 font-mono text-xs">
      <ResponsiveContainer width="100%" height="100%">
        <BarChart
          data={chartData}
          layout="vertical"
          margin={{ top: 10, right: 30, left: 80, bottom: 5 }}
        >
          <XAxis
            type="number"
            stroke="#64748B"
            tick={{ fill: '#94A3B8', fontSize: 10 }}
            domain={[-2, 'auto']}
          />
          <YAxis
            type="category"
            dataKey="feature"
            stroke="#64748B"
            tick={{ fill: '#CBD5E1', fontSize: 10 }}
            width={110}
          />
          <Tooltip
            contentStyle={{
              backgroundColor: '#0F172A',
              borderColor: '#334155',
              borderRadius: '8px',
              fontFamily: 'JetBrains Mono, monospace',
              fontSize: '11px',
            }}
            formatter={(value: any, name: any) => [
              `+${value} σ (Dev vs Baseline)`,
              'z-Score Deviation',
            ]}
          />
          <ReferenceLine x={0} stroke="#475569" strokeDasharray="3 3" />
          <Bar dataKey="z_score" radius={[0, 4, 4, 0]}>
            {chartData.map((entry, index) => {
              const color =
                entry.z_score >= 2.0
                  ? '#EF4444' // Critical
                  : entry.z_score >= 1.0
                  ? '#F97316' // High
                  : '#10B981'; // Normal
              return <Cell key={`cell-${index}`} fill={color} />;
            })}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
};
