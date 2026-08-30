import React from 'react';
import { NavLink } from 'react-router-dom';
import {
  LayoutDashboard,
  Database,
  BellRing,
  Search,
  Network,
  Boxes,
  Cpu,
  FileSpreadsheet,
  Settings,
  ShieldCheck,
  Zap
} from 'lucide-react';

const NAV_ITEMS = [
  { name: 'Dashboard', path: '/', icon: LayoutDashboard },
  { name: 'Datasets & Ingestion', path: '/datasets', icon: Database },
  { name: 'Investigative Alerts', path: '/alerts', icon: BellRing },
  { name: 'Entity Search', path: '/search', icon: Search },
  { name: 'Graph Explorer', path: '/graph', icon: Network },
  { name: 'Entity Clusters', path: '/clusters', icon: Boxes },
  { name: 'ML Model Studio', path: '/models', icon: Cpu },
  { name: 'Forensic Reports', path: '/reports', icon: FileSpreadsheet },
  { name: 'System & Audit', path: '/settings', icon: Settings },
];

export const Sidebar: React.FC = () => {
  return (
    <aside className="w-64 border-r border-cyber-border bg-cyber-card/40 flex flex-col shrink-0">
      {/* Brand Header */}
      <div className="h-16 px-6 flex items-center gap-3 border-b border-cyber-border">
        <div className="w-8 h-8 rounded-lg bg-gradient-to-tr from-emerald-600 to-cyan-500 p-0.5 flex items-center justify-center shadow-glow-emerald">
          <Zap className="w-5 h-5 text-slate-950 fill-current" />
        </div>
        <div>
          <span className="font-bold font-mono text-base tracking-wider text-slate-100">
            Trace<span className="text-cyber-emerald">X</span>
          </span>
          <span className="block text-[9px] font-mono text-slate-500 uppercase tracking-widest">
            SIH 2026 • SIH26146
          </span>
        </div>
      </div>

      {/* Navigation Links */}
      <nav className="flex-1 px-3 py-4 space-y-1 overflow-y-auto">
        {NAV_ITEMS.map((item) => {
          const Icon = item.icon;
          return (
            <NavLink
              key={item.path}
              to={item.path}
              className={({ isActive }) =>
                `flex items-center gap-3 px-3.5 py-2.5 rounded-lg text-xs font-medium transition-all ${
                  isActive
                    ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 font-semibold shadow-sm'
                    : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/40'
                }`
              }
            >
              <Icon className="w-4 h-4 shrink-0" />
              <span>{item.name}</span>
            </NavLink>
          );
        })}
      </nav>

      {/* Legal & Compliance Disclaimer Box */}
      <div className="p-3 m-3 rounded-lg bg-slate-900/90 border border-slate-800 text-[10px] text-slate-500 leading-relaxed font-mono">
        <div className="flex items-center gap-1 text-slate-400 font-semibold mb-1">
          <ShieldCheck className="w-3.5 h-3.5 text-cyber-emerald" />
          <span>INVESTIGATIVE USE</span>
        </div>
        Alerts are statistical anomaly leads. Correlations do not prove ownership or intent.
      </div>
    </aside>
  );
};
