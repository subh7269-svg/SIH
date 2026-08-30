import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Link, useNavigate } from 'react-router-dom';
import {
  BellRing,
  ShieldAlert,
  Filter,
  CheckCircle2,
  AlertTriangle,
  ArrowUpRight,
  UserCheck,
  FileSpreadsheet,
  Clock,
  MessageSquare
} from 'lucide-react';
import { getAlerts, updateAlertStatus } from '../services/api';
import { Badge } from '../components/common/Badge';
import { Alert } from '../types';

export const AlertsPage: React.FC = () => {
  const queryClient = useQueryClient();
  const navigate = useNavigate();

  const [severityFilter, setSeverityFilter] = useState<string>('');
  const [statusFilter, setStatusFilter] = useState<string>('');
  const [selectedAlertForTriage, setSelectedAlertForTriage] = useState<Alert | null>(null);
  const [triageStatus, setTriageStatus] = useState<string>('REVIEWING');
  const [triageNote, setTriageNote] = useState<string>('');

  const { data: alertsData, isLoading } = useQuery({
    queryKey: ['alerts', severityFilter, statusFilter],
    queryFn: () =>
      getAlerts({
        severity: severityFilter || undefined,
        status: statusFilter || undefined,
        limit: 50,
      }),
  });

  const triageMutation = useMutation({
    mutationFn: ({ id, status, note }: { id: string; status: string; note: string }) =>
      updateAlertStatus(id, status, note),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['alerts'] });
      setSelectedAlertForTriage(null);
      setTriageNote('');
    },
  });

  const handleTriageSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (selectedAlertForTriage) {
      triageMutation.mutate({
        id: selectedAlertForTriage.id,
        status: triageStatus,
        note: triageNote,
      });
    }
  };

  return (
    <div className="space-y-6 font-mono">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-cyber-border pb-4">
        <div>
          <h1 className="text-xl font-bold text-slate-100 flex items-center gap-2">
            <BellRing className="w-5 h-5 text-cyber-emerald" />
            <span>PRIORITIZED INVESTIGATIVE ALERTS</span>
          </h1>
          <p className="text-xs text-slate-400 mt-1">
            Ranked anomaly detection leads prioritized by composite behavioral and graph risk scores.
          </p>
        </div>
      </div>

      {/* Filter Toolbar */}
      <div className="cyber-card p-4 flex flex-wrap items-center justify-between gap-4">
        {/* Severity Tabs */}
        <div className="flex items-center gap-1">
          {['', 'CRITICAL', 'HIGH', 'MEDIUM', 'LOW'].map((sev) => (
            <button
              key={sev}
              onClick={() => setSeverityFilter(sev)}
              className={`px-3 py-1.5 rounded-lg text-xs font-semibold uppercase transition-all ${
                severityFilter === sev
                  ? 'bg-cyber-emerald text-slate-950 shadow-glow-emerald'
                  : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800'
              }`}
            >
              {sev || 'All Severities'}
            </button>
          ))}
        </div>

        {/* Status Filter */}
        <div className="flex items-center gap-2 text-xs">
          <Filter className="w-3.5 h-3.5 text-slate-400" />
          <span className="text-slate-400">Status:</span>
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="bg-slate-900 border border-slate-700 text-slate-200 rounded px-2.5 py-1 text-xs focus:outline-none focus:border-cyber-emerald"
          >
            <option value="">All Statuses</option>
            <option value="NEW">NEW</option>
            <option value="REVIEWING">REVIEWING</option>
            <option value="ESCALATED">ESCALATED</option>
            <option value="DISMISSED">DISMISSED</option>
            <option value="RESOLVED">RESOLVED</option>
          </select>
        </div>
      </div>

      {/* Alerts Table */}
      <div className="cyber-card p-5 space-y-4">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead>
              <tr className="border-b border-slate-800 text-slate-400 uppercase text-[10px]">
                <th className="pb-3 pl-2">Lead / Target Entity</th>
                <th className="pb-3">Priority Score</th>
                <th className="pb-3">Severity</th>
                <th className="pb-3">ML Anomaly Score</th>
                <th className="pb-3">Top Empirical Reason</th>
                <th className="pb-3">Status</th>
                <th className="pb-3 pr-2 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/60 text-slate-200">
              {isLoading ? (
                <tr>
                  <td colSpan={7} className="py-8 text-center text-slate-500">
                    Loading alerts...
                  </td>
                </tr>
              ) : !alertsData?.alerts || alertsData.alerts.length === 0 ? (
                <tr>
                  <td colSpan={7} className="py-8 text-center text-slate-500">
                    No investigative alerts match current filter criteria.
                  </td>
                </tr>
              ) : (
                alertsData.alerts.map((alert) => (
                  <tr
                    key={alert.id}
                    className="hover:bg-slate-800/30 transition-colors cursor-pointer group"
                    onClick={() => navigate(`/entities/${encodeURIComponent(alert.entity_id)}`)}
                  >
                    <td className="py-3.5 pl-2 font-medium text-slate-100">
                      <div className="flex items-center gap-2">
                        <span className="text-cyber-cyan group-hover:text-cyber-emerald transition-colors font-bold">
                          {alert.entity_id.length > 22
                            ? `${alert.entity_id.slice(0, 10)}...${alert.entity_id.slice(-8)}`
                            : alert.entity_id}
                        </span>
                        <span className="text-[10px] text-slate-500 uppercase">({alert.entity_type})</span>
                      </div>
                    </td>
                    <td className="py-3.5 font-bold font-mono">
                      <span className="text-slate-100">{alert.priority_score}</span>
                      <span className="text-slate-500 text-[10px]">/100</span>
                    </td>
                    <td className="py-3.5">
                      <Badge variant={alert.severity.toLowerCase() as any}>
                        {alert.severity}
                      </Badge>
                    </td>
                    <td className="py-3.5 font-bold text-cyber-emerald">
                      {alert.anomaly_score.toFixed(2)}
                    </td>
                    <td className="py-3.5 text-slate-300 max-w-sm truncate">
                      {alert.reasons?.[0] || 'Statistical outlier'}
                    </td>
                    <td className="py-3.5">
                      <span
                        className={`px-2 py-0.5 rounded text-[10px] font-semibold border ${
                          alert.status === 'NEW'
                            ? 'bg-blue-500/10 text-blue-400 border-blue-500/20'
                            : alert.status === 'REVIEWING'
                            ? 'bg-amber-500/10 text-amber-400 border-amber-500/20'
                            : alert.status === 'ESCALATED'
                            ? 'bg-red-500/10 text-red-400 border-red-500/20'
                            : 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20'
                        }`}
                      >
                        {alert.status}
                      </span>
                    </td>
                    <td className="py-3.5 pr-2 text-right">
                      <div className="flex items-center justify-end gap-2" onClick={(e) => e.stopPropagation()}>
                        <button
                          onClick={() => {
                            setSelectedAlertForTriage(alert);
                            setTriageStatus(alert.status);
                          }}
                          className="px-2 py-1 rounded bg-slate-800 hover:bg-slate-700 text-[11px] text-slate-200 border border-slate-700 transition-colors"
                        >
                          Triage
                        </button>
                        <Link
                          to={`/entities/${encodeURIComponent(alert.entity_id)}`}
                          className="p-1 rounded bg-slate-800 hover:bg-slate-700 text-slate-300 transition-colors"
                          title="Open Dossier"
                        >
                          <ArrowUpRight className="w-3.5 h-3.5" />
                        </Link>
                      </div>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Triage Modal */}
      {selectedAlertForTriage && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm p-4">
          <div className="cyber-card p-6 max-w-md w-full space-y-4 border border-cyber-borderLight">
            <div className="flex items-center justify-between border-b border-cyber-border pb-3">
              <div className="flex items-center gap-2">
                <UserCheck className="w-4 h-4 text-cyber-emerald" />
                <h3 className="text-sm font-semibold text-slate-100 uppercase">Triage Investigative Lead</h3>
              </div>
              <button
                onClick={() => setSelectedAlertForTriage(null)}
                className="text-slate-400 hover:text-slate-100 text-sm"
              >
                ✕
              </button>
            </div>

            <div className="text-xs space-y-2 bg-slate-900/80 p-3 rounded-lg border border-slate-800">
              <p className="text-slate-400 truncate">
                Target: <span className="text-cyber-cyan font-bold">{selectedAlertForTriage.entity_id}</span>
              </p>
              <p className="text-slate-400">
                Priority: <span className="text-cyber-emerald font-bold">{selectedAlertForTriage.priority_score}/100</span> ({selectedAlertForTriage.severity})
              </p>
            </div>

            <form onSubmit={handleTriageSubmit} className="space-y-4 text-xs">
              <div>
                <label className="block text-slate-400 mb-1">Update Lead Status</label>
                <select
                  value={triageStatus}
                  onChange={(e) => setTriageStatus(e.target.value)}
                  className="w-full bg-slate-900 border border-slate-700 rounded p-2 text-slate-100 focus:outline-none focus:border-cyber-emerald"
                >
                  <option value="NEW">NEW</option>
                  <option value="REVIEWING">REVIEWING</option>
                  <option value="ESCALATED">ESCALATED</option>
                  <option value="DISMISSED">DISMISSED</option>
                  <option value="RESOLVED">RESOLVED</option>
                </select>
              </div>

              <div>
                <label className="block text-slate-400 mb-1">Analyst Case Note</label>
                <textarea
                  value={triageNote}
                  onChange={(e) => setTriageNote(e.target.value)}
                  placeholder="Record investigative reasoning, hypothesis, or justification..."
                  rows={3}
                  className="w-full bg-slate-900 border border-slate-700 rounded p-2 text-slate-100 placeholder-slate-500 focus:outline-none focus:border-cyber-emerald resize-none"
                />
              </div>

              <div className="flex justify-end gap-2 pt-2">
                <button
                  type="button"
                  onClick={() => setSelectedAlertForTriage(null)}
                  className="px-3 py-1.5 rounded bg-slate-800 hover:bg-slate-700 text-slate-300 transition-colors"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={triageMutation.isPending}
                  className="px-4 py-1.5 rounded bg-cyber-emerald text-slate-950 font-bold hover:bg-emerald-400 transition-all shadow-glow-emerald disabled:opacity-50"
                >
                  {triageMutation.isPending ? 'Saving...' : 'Save Triage Decision'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
