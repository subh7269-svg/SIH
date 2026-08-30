import React from 'react';

interface BadgeProps {
  children: React.ReactNode;
  variant?: 'critical' | 'high' | 'medium' | 'low' | 'info' | 'purple' | 'neutral' | 'success';
  size?: 'sm' | 'md' | 'lg';
  className?: string;
}

export const Badge: React.FC<BadgeProps> = ({
  children,
  variant = 'neutral',
  size = 'sm',
  className = '',
}) => {
  const variantStyles = {
    critical: 'bg-red-500/10 text-red-400 border-red-500/30 shadow-[0_0_10px_rgba(239,68,68,0.2)]',
    high: 'bg-orange-500/10 text-orange-400 border-orange-500/30',
    medium: 'bg-amber-500/10 text-amber-400 border-amber-500/30',
    low: 'bg-emerald-500/10 text-emerald-400 border-emerald-500/30',
    info: 'bg-cyan-500/10 text-cyan-400 border-cyan-500/30',
    purple: 'bg-purple-500/10 text-purple-400 border-purple-500/30',
    success: 'bg-emerald-500/10 text-emerald-400 border-emerald-500/30',
    neutral: 'bg-slate-800 text-slate-300 border-slate-700',
  };

  const sizeStyles = {
    sm: 'text-xs px-2 py-0.5',
    md: 'text-xs px-2.5 py-1 font-medium',
    lg: 'text-sm px-3 py-1.5 font-semibold',
  };

  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full border font-mono uppercase tracking-wider ${variantStyles[variant]} ${sizeStyles[size]} ${className}`}
    >
      {variant === 'critical' && <span className="w-1.5 h-1.5 rounded-full bg-red-400 animate-pulse" />}
      {variant === 'high' && <span className="w-1.5 h-1.5 rounded-full bg-orange-400" />}
      {children}
    </span>
  );
};
