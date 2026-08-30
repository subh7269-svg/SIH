import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  Settings as SettingsIcon,
  ShieldCheck,
  Radio,
  RefreshCw,
  Trash2,
  CheckCircle2,
  Database,
  Lock,
  Cpu
} from 'lucide-react';
import { getAuditLogs, resetDemo } from '../services/api';

export const SettingsPage: React.FC = () => {
  const queryClient = useQueryClient();
  const [resetMessage, setResetMessage] = useState<string | null>(null);

  const { data: auditLogs, isLoading } = useQuery({
    queryKey: ['audit-logs'],
    queryFn: () => getAuditLogs(50),
  });

  const resetMutation = useMutation({
    mutationFn: resetDemo,
    onSuccess: () => {
      queryClient.invalidateQueries();
      setResetMessage('All investigative data and graphs reset to clean state.');
      setTimeout(() => setResetMessage(null), 3000);
    },
  });

  return (
    <div className="space-y-6 font-mono">
      {/* Header */}
      <div className="border-b border-cyber-border pb-4">
        <h1 className="text-xl font-bold text-slate-100 flex items-center gap-2">
          <SettingsIcon className="w-5 h-5 text-cyber-emerald" />
          <span>SYSTEM HEALTH & IMMUTABLE AUDIT TRAIL</span>
        </h1>
        <p className="text-xs text-slate-400 mt-1">
          Compliance logs, offline environment status, and state management.
        </p>
      </div>

      {/* System Status Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <div className="cyber-card p-4 space-y-2">
          <div className="flex items-center gap-2 text-cyber-emerald">
            <Radio className="w-4 h-4" />
            <span className="text-xs font-bold uppercase">Offline GeoIP Engine</span>
          </div>
          <p className="text-xs text-slate-300">Embedded Subnet DB Loaded</p>
          <p className="text-[10px] text-slate-500">Zero external API dependencies</p>
        </div>

        <div className="cyber-card p-4 space-y-2">
          <div className="flex items-center gap-2 text-cyber-cyan">
            <Database className="w-4 h-4" />
            <span className="text-xs font-bold uppercase">Persistence Engine</span>
          </div>
          <p className="text-xs text-slate-300">SQLAlchemy 2.0 ORM Active</p>
          <p className="text-[10px] text-slate-500">SQLite Local / PostgreSQL Docker</p>
        </div>

        <div className="cyber-card p-4 space-y-2">
          <div className="flex items-center gap-2 text-cyber-purple">
            <Cpu className="w-4 h-4" />
            <span className="text-xs font-bold uppercase">ML Inference Engine</span>
          </div>
          <p className="text-xs text-slate-300">Isolation Forest & DBSCAN</p>
          <p className="text-[10px] text-slate-500">Scikit-learn 1.4+ / NetworkX 3.2</p>
        </div>
      </div>

      {/* Clean Slate Reset */}
      <div className="cyber-card p-5 space-y-3 border-l-4 border-l-amber-500">
        <div className="flex items-center justify-between">
          <div>
            <h3 className="text-sm font-bold text-slate-100">Reset System Database</h3>
            <p className="text-xs text-slate-400 mt-0.5">
              Purges all uploaded datasets, correlated entities, graphs, alerts, and model artifacts for a fresh hackathon demo.
            </p>
          </div>
          <button
            onClick={() => resetMutation.mutate()}
            disabled={resetMutation.isPending}
            className="flex items-center gap-2 px-3.5 py-1.5 rounded-lg bg-red-500/10 hover:bg-red-500/20 text-red-400 border border-red-500/30 text-xs font-bold transition-all disabled:opacity-50"
          >
            {resetMutation.isPending ? <RefreshCw className="w-3.5 h-3.5 animate-spin" /> : <Trash2 className="w-3.5 h-3.5" />}
            <span>Reset All Data</span>
          </button>
        </div>
        {resetMessage && (
          <p className="text-xs text-cyber-emerald font-bold animate-pulse">{resetMessage}</p>
        )}
      </div>

      {/* Audit Logs Table */}
      <div className="cyber-card p-5 space-y-4">
        <div className="flex items-center justify-between border-b border-cyber-border pb-3">
          <div className="flex items-center gap-2">
            <ShieldCheck className="w-4 h-4 text-cyber-emerald" />
            <h2 className="text-sm font-semibold text-slate-100 uppercase tracking-wider">
              Investigator Audit Log ({auditLogs?.length || 0} Events)
            </h2>
          </div>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead>
              <tr className="border-b border-slate-800 text-slate-400 uppercase text-[10px]">
                <th className="pb-3 pl-2">Timestamp (UTC)</th>
                <th className="pb-3">Investigator</th>
                <th className="pb-3">Action</th>
                <th className="pb-3">Target</th>
                <th className="pb-3 pr-2">Metadata Details</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/60 text-slate-200">
              {isLoading ? (
                <tr><td colSpan={5} className="py-6 text-center text-slate-500">Loading audit trail...</td></tr>
              ) : !auditLogs || auditLogs.length === 0 ? (
                <tr><td colSpan={5} className="py-6 text-center text-slate-500">No audit events recorded yet.</td></tr>
              ) : (
                auditLogs.map((log: any) => (
                  <tr key={log.id} className="hover:bg-slate-800/30">
                    <td className="py-2.5 pl-2 text-slate-400 text-[11px]">{log.timestamp}</td>
                    <td className="py-2.5 font-bold text-cyber-cyan">{log.user_name}</td>
                    <td className="py-2.5">
                      <span className="px-2 py-0.5 rounded bg-slate-900 border border-slate-800 text-[10px] text-cyber-emerald">
                        {log.action}
                      </span>
                    </td>
                    <td className="py-2.5 text-slate-300">
                      {log.target_type && `${log.target_type}: `}
                      <span className="text-slate-400 text-[11px]">{log.target_id || '-'}</span>
                    </td>
                    <td className="py-2.5 pr-2 text-slate-500 text-[10px] truncate max-w-xs">
                      {JSON.stringify(log.details || {})}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};
