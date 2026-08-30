import React from 'react';
import { LucideIcon } from 'lucide-react';

interface StatCardProps {
  title: string;
  value: string | number;
  subtitle?: string;
  icon: LucideIcon;
  trend?: {
    value: string;
    isPositive?: boolean;
  };
  accentColor?: 'emerald' | 'cyan' | 'rose' | 'amber' | 'purple';
}

export const StatCard: React.FC<StatCardProps> = ({
  title,
  value,
  subtitle,
  icon: Icon,
  trend,
  accentColor = 'emerald',
}) => {
  const colorMap = {
    emerald: {
      bg: 'bg-emerald-500/10',
      text: 'text-emerald-400',
      border: 'border-emerald-500/20',
      glow: 'shadow-glow-emerald',
    },
    cyan: {
      bg: 'bg-cyan-500/10',
      text: 'text-cyan-400',
      border: 'border-cyan-500/20',
      glow: 'shadow-glow-cyan',
    },
    rose: {
      bg: 'bg-rose-500/10',
      text: 'text-rose-400',
      border: 'border-rose-500/20',
      glow: 'shadow-glow-rose',
    },
    amber: {
      bg: 'bg-amber-500/10',
      text: 'text-amber-400',
      border: 'border-amber-500/20',
      glow: '',
    },
    purple: {
      bg: 'bg-purple-500/10',
      text: 'text-purple-400',
      border: 'border-purple-500/20',
      glow: '',
    },
  };

  const scheme = colorMap[accentColor];

  return (
    <div className="cyber-card p-5 relative overflow-hidden group">
      <div className="flex items-center justify-between">
        <div>
          <p className="text-xs font-medium text-slate-400 uppercase tracking-wider">{title}</p>
          <p className="text-2xl font-bold text-slate-100 mt-1 font-mono tracking-tight">{value}</p>
          {subtitle && <p className="text-xs text-slate-500 mt-1">{subtitle}</p>}
        </div>
        <div className={`p-3 rounded-xl ${scheme.bg} ${scheme.border} border text-slate-100 group-hover:scale-110 transition-transform duration-300`}>
          <Icon className={`w-6 h-6 ${scheme.text}`} />
        </div>
      </div>
      {trend && (
        <div className="mt-3 flex items-center gap-1.5 text-xs">
          <span className={`font-mono font-semibold ${trend.isPositive ? 'text-emerald-400' : 'text-rose-400'}`}>
            {trend.value}
          </span>
          <span className="text-slate-500">vs benchmark</span>
        </div>
      )}
    </div>
  );
};
