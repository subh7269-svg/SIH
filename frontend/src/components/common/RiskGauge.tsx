import React from 'react';

interface RiskGaugeProps {
  score: number; // 0 - 100
  size?: 'sm' | 'md' | 'lg';
  showLabel?: boolean;
}

export const RiskGauge: React.FC<RiskGaugeProps> = ({
  score,
  size = 'md',
  showLabel = true,
}) => {
  const clamped = Math.max(0, Math.min(100, score));

  let color = '#10B981'; // low
  let severity = 'LOW';
  if (clamped >= 80) {
    color = '#EF4444'; // critical
    severity = 'CRITICAL';
  } else if (clamped >= 60) {
    color = '#F97316'; // high
    severity = 'HIGH';
  } else if (clamped >= 35) {
    color = '#FBBF24'; // medium
    severity = 'MEDIUM';
  }

  const dimensions = {
    sm: { stroke: 4, radius: 18, sizePx: 44, text: 'text-xs' },
    md: { stroke: 6, radius: 28, sizePx: 70, text: 'text-sm' },
    lg: { stroke: 8, radius: 42, sizePx: 104, text: 'text-xl' },
  }[size];

  const circumference = 2 * Math.PI * dimensions.radius;
  const strokeDashoffset = circumference - (clamped / 100) * circumference;

  return (
    <div className="flex items-center gap-3">
      <div className="relative inline-flex items-center justify-center" style={{ width: dimensions.sizePx, height: dimensions.sizePx }}>
        <svg className="transform -rotate-90" width={dimensions.sizePx} height={dimensions.sizePx}>
          <circle
            cx={dimensions.sizePx / 2}
            cy={dimensions.sizePx / 2}
            r={dimensions.radius}
            stroke="#1E293B"
            strokeWidth={dimensions.stroke}
            fill="transparent"
          />
          <circle
            cx={dimensions.sizePx / 2}
            cy={dimensions.sizePx / 2}
            r={dimensions.radius}
            stroke={color}
            strokeWidth={dimensions.stroke}
            strokeDasharray={circumference}
            strokeDashoffset={strokeDashoffset}
            strokeLinecap="round"
            fill="transparent"
            className="transition-all duration-700 ease-out"
          />
        </svg>
        <span className={`absolute font-mono font-bold text-slate-100 ${dimensions.text}`}>
          {clamped}
        </span>
      </div>

      {showLabel && (
        <div>
          <div className="text-xs text-slate-400 font-mono">PRIORITY SCORE</div>
          <div className="text-sm font-semibold tracking-wide font-mono" style={{ color }}>
            {severity} RISK
          </div>
        </div>
      )}
    </div>
  );
};
