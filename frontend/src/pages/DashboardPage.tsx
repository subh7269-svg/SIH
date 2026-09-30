import React from 'react';
import { useQuery } from '@tanstack/react-query';
import { useNavigate, Link } from 'react-router-dom';
import {
  ShieldAlert,
  Activity,
  Database,
  Users,
  Network,
  Cpu,
  ArrowUpRight,
  TrendingUp,
  AlertCircle,
  Clock,
  Radio,
  FileText
} from 'lucide-react';
import { getAlerts, getDatasets, getModels, getClusters, getTemporalVolume } from '../services/api';
import { StatCard } from '../components/common/StatCard';
import { Badge } from '../components/common/Badge';
import { RiskGauge } from '../components/common/RiskGauge';
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell
} from 'recharts';

export const DashboardPage: React.FC = () => {
  const navigate = useNavigate();

  const { data: alertsData, isLoading: alertsLoading } = useQuery({
    queryKey: ['alerts'],
    queryFn: () => getAlerts({ limit: 10 }),
  });

  const { data: datasetsData } = useQuery({
    queryKey: ['datasets'],
    queryFn: getDatasets,
  });

  const { data: modelsData } = useQuery({
    queryKey: ['models'],
    queryFn: getModels,
  });

  const { data: clustersData } = useQuery({
    queryKey: ['clusters'],
    queryFn: () => getClusters(),
  });

  const { data: temporalData } = useQuery({
    queryKey: ['temporal-volume'],
    queryFn: getTemporalVolume,
  });

  const activeDataset = datasetsData?.datasets?.[0];
  const dq = activeDataset?.data_quality_metrics;

  const totalTxs = dq?.total_records || 0;
  const totalWallets = dq?.unique_wallets || 0;
  const totalIps = dq?.unique_src_ips || 0;
  const criticalCount = alertsData?.critical_count || 0;
  const highCount = alertsData?.high_count || 0;

  // Severity Distribution Data
  const severityChartData = [
    { name: 'Critical', value: alertsData?.critical_count || 0, color: '#EF4444' },
    { name: 'High', value: alertsData?.high_count || 0, color: '#F97316' },
    { name: 'Medium', value: alertsData?.medium_count || 0, color: '#FBBF24' },
    { name: 'Low', value: alertsData?.low_count || 0, color: '#10B981' },
  ].filter((d) => d.value > 0);

  // Real activity data from backend — show only hours that have activity,
  // sampled to a max of 12 ticks on the X axis for readability.
  const hasTemporalData = temporalData?.has_data ?? false;
  const activityData = hasTemporalData
    ? (temporalData!.hourly_data
        .filter((_, i) => i % 2 === 0) // Show every 2h for clean axis
        .map((d) => ({
          time: d.time,
          volume: d.volume > 0 ? d.volume : d.tx_count,
          alerts: d.alerts,
        })))
    : [];

  return (
    <div className="space-y-6">
      {/* Top Banner Notice */}
      <div className="p-4 rounded-xl bg-gradient-to-r from-slate-900 via-slate-850 to-slate-900 border border-cyber-border flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
            <h1 className="text-base font-bold text-slate-100 font-mono tracking-wide">
              INVESTIGATIVE INTELLIGENCE OVERVIEW
            </h1>
          </div>
          <p className="text-xs text-slate-400 mt-1 font-mono">
            {activeDataset ? (
              <>Active Dataset: <span className="text-cyber-emerald font-semibold">{activeDataset.filename}</span> ({activeDataset.processed_records} records indexed)</>
            ) : (
              <>No dataset loaded yet. Click <span className="text-cyber-emerald font-bold">"Run 1-Click SIH Demo"</span> or upload CSV/JSON/XML in Ingestion Hub.</>
            )}
          </p>
        </div>

        <div className="flex items-center gap-2 shrink-0">
          <Link
            to="/graph"
            className="flex items-center gap-1.5 px-3.5 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-xs font-mono text-slate-200 border border-slate-700 transition-colors"
          >
            <Network className="w-3.5 h-3.5 text-cyber-cyan" />
            <span>Launch Graph Visualizer</span>
          </Link>
          <Link
            to="/datasets"
            className="flex items-center gap-1.5 px-3.5 py-1.5 rounded-lg bg-cyber-emerald/10 hover:bg-cyber-emerald/20 text-xs font-mono text-cyber-emerald border border-cyber-emerald/30 transition-colors"
          >
            <Database className="w-3.5 h-3.5" />
            <span>Ingestion Hub</span>
          </Link>
        </div>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard
          title="Indexed Transactions"
          value={totalTxs.toLocaleString()}
          subtitle={`${dq?.unique_txids || 0} unique TXIDs`}
          icon={Activity}
          accentColor="cyan"
        />
        <StatCard
          title="Observed Wallets"
          value={totalWallets.toLocaleString()}
          subtitle={`${dq?.total_btc_volume || 0} BTC Transferred`}
          icon={Users}
          accentColor="emerald"
        />
        <StatCard
          title="Network Relay IPs"
          value={totalIps.toLocaleString()}
          subtitle={`${dq?.unique_countries || 0} Countries | ${dq?.unique_asns || 0} ASNs`}
          icon={Radio}
          accentColor="purple"
        />
        <StatCard
          title="Prioritized Leads"
          value={(criticalCount + highCount).toLocaleString()}
          subtitle={`${criticalCount} Critical | ${highCount} High Risk`}
          icon={ShieldAlert}
          accentColor="rose"
        />
      </div>

      {/* Main Grid: Activity Timeline & Risk Distribution */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Activity & Volume Timeline */}
        <div className="cyber-card p-5 lg:col-span-2 space-y-4">
          <div className="flex items-center justify-between border-b border-cyber-border pb-3">
            <div className="flex items-center gap-2">
              <Activity className="w-4 h-4 text-cyber-cyan" />
              <h2 className="text-sm font-semibold text-slate-100 font-mono uppercase tracking-wider">
                Observed Volume & Anomaly Bursts
              </h2>
            </div>
            <span className="text-xs font-mono text-slate-500">
              {hasTemporalData
                ? `${temporalData!.total_transactions.toLocaleString()} TXs · ${temporalData!.total_volume_btc.toFixed(4)} BTC`
                : 'UTC Temporal Distribution'}
            </span>
          </div>

          <div className="h-64 w-full">
            {!hasTemporalData ? (
              <div className="h-full flex flex-col items-center justify-center text-slate-500 gap-3">
                <Activity className="w-10 h-10 text-slate-700" />
                <p className="text-xs font-mono text-center">
                  No transaction data ingested yet.<br />
                  Upload a dataset or run the 1-Click Demo to see real temporal activity.
                </p>
              </div>
            ) : (
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={activityData} margin={{ top: 10, right: 10, left: 0, bottom: 0 }}>
                  <defs>
                    <linearGradient id="colorVol" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#06B6D4" stopOpacity={0.4} />
                      <stop offset="95%" stopColor="#06B6D4" stopOpacity={0.0} />
                    </linearGradient>
                  </defs>
                  <XAxis dataKey="time" stroke="#64748B" tick={{ fill: '#94A3B8', fontSize: 11 }} />
                  <YAxis stroke="#64748B" tick={{ fill: '#94A3B8', fontSize: 11 }} />
                  <Tooltip
                    contentStyle={{
                      backgroundColor: '#0F172A',
                      borderColor: '#334155',
                      borderRadius: '8px',
                      fontFamily: 'JetBrains Mono, monospace',
                      fontSize: '11px',
                    }}
                  />
                  <Area type="monotone" dataKey="volume" stroke="#06B6D4" strokeWidth={2} fillOpacity={1} fill="url(#colorVol)" name="Volume (BTC)" />
                </AreaChart>
              </ResponsiveContainer>
            )}
          </div>
        </div>

        {/* Severity Breakdown */}
        <div className="cyber-card p-5 space-y-4">
          <div className="flex items-center justify-between border-b border-cyber-border pb-3">
            <div className="flex items-center gap-2">
              <ShieldAlert className="w-4 h-4 text-cyber-rose" />
              <h2 className="text-sm font-semibold text-slate-100 font-mono uppercase tracking-wider">
                Risk Distribution
              </h2>
            </div>
            <span className="text-xs font-mono text-slate-400">Total: {alertsData?.total || 0}</span>
          </div>

          <div className="h-44 flex items-center justify-center">
            {severityChartData.length > 0 ? (
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie
                    data={severityChartData}
                    cx="50%"
                    cy="50%"
                    innerRadius={45}
                    outerRadius={70}
                    paddingAngle={4}
                    dataKey="value"
                  >
                    {severityChartData.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={entry.color} />
                    ))}
                  </Pie>
                  <Tooltip
                    contentStyle={{
                      backgroundColor: '#0F172A',
                      borderColor: '#334155',
                      borderRadius: '8px',
                      fontFamily: 'JetBrains Mono, monospace',
                      fontSize: '11px',
                    }}
                  />
                </PieChart>
              </ResponsiveContainer>
            ) : (
              <p className="text-xs text-slate-500 font-mono">No alerts generated yet.</p>
            )}
          </div>

          {/* Breakdown Legend */}
          <div className="grid grid-cols-2 gap-2 text-xs font-mono">
            <div className="p-2 rounded bg-slate-900/60 border border-slate-800 flex items-center justify-between">
              <span className="text-red-400">CRITICAL</span>
              <span className="font-bold text-slate-100">{criticalCount}</span>
            </div>
            <div className="p-2 rounded bg-slate-900/60 border border-slate-800 flex items-center justify-between">
              <span className="text-orange-400">HIGH</span>
              <span className="font-bold text-slate-100">{highCount}</span>
            </div>
            <div className="p-2 rounded bg-slate-900/60 border border-slate-800 flex items-center justify-between">
              <span className="text-amber-400">MEDIUM</span>
              <span className="font-bold text-slate-100">{alertsData?.medium_count || 0}</span>
            </div>
            <div className="p-2 rounded bg-slate-900/60 border border-slate-800 flex items-center justify-between">
              <span className="text-emerald-400">LOW</span>
              <span className="font-bold text-slate-100">{alertsData?.low_count || 0}</span>
            </div>
          </div>
        </div>
      </div>

      {/* Top Ranked Investigative Leads Table */}
      <div className="cyber-card p-5 space-y-4">
        <div className="flex items-center justify-between border-b border-cyber-border pb-3">
          <div className="flex items-center gap-2">
            <ShieldAlert className="w-4 h-4 text-cyber-emerald" />
            <h2 className="text-sm font-semibold text-slate-100 font-mono uppercase tracking-wider">
              Top Prioritized Investigative Leads
            </h2>
          </div>
          <Link
            to="/alerts"
            className="text-xs font-mono text-cyber-emerald hover:underline flex items-center gap-1"
          >
            <span>View All ({alertsData?.total || 0})</span>
            <ArrowUpRight className="w-3.5 h-3.5" />
          </Link>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs font-mono">
            <thead>
              <tr className="border-b border-slate-800 text-slate-400 uppercase text-[10px]">
                <th className="pb-3 pl-2">Entity ID</th>
                <th className="pb-3">Type</th>
                <th className="pb-3">Priority / Severity</th>
                <th className="pb-3">ML Anomaly Score</th>
                <th className="pb-3">Primary Behavioral Reason</th>
                <th className="pb-3">Status</th>
                <th className="pb-3 pr-2 text-right">Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/60 text-slate-200">
              {alertsLoading ? (
                <tr>
                  <td colSpan={7} className="py-8 text-center text-slate-500">
                    Loading investigative alerts...
                  </td>
                </tr>
              ) : !alertsData?.alerts || alertsData.alerts.length === 0 ? (
                <tr>
                  <td colSpan={7} className="py-8 text-center text-slate-500">
                    No anomalous entities flagged yet. Run demo mode or upload dataset to start AI detection.
                  </td>
                </tr>
              ) : (
                alertsData.alerts.map((alert) => (
                  <tr
                    key={alert.id}
                    className="hover:bg-slate-800/30 transition-colors group cursor-pointer"
                    onClick={() => navigate(`/entities/${encodeURIComponent(alert.entity_id)}`)}
                  >
                    <td className="py-3.5 pl-2 font-semibold text-slate-100 flex items-center gap-2">
                      <span className="text-cyber-cyan group-hover:text-cyber-emerald transition-colors">
                        {alert.entity_id.length > 20
                          ? `${alert.entity_id.slice(0, 10)}...${alert.entity_id.slice(-8)}`
                          : alert.entity_id}
                      </span>
                    </td>
                    <td className="py-3.5 text-slate-400">{alert.entity_type}</td>
                    <td className="py-3.5">
                      <div className="flex items-center gap-2">
                        <Badge
                          variant={
                            alert.severity.toLowerCase() as any
                          }
                        >
                          {alert.severity} ({alert.priority_score}/100)
                        </Badge>
                      </div>
                    </td>
                    <td className="py-3.5 font-bold text-cyber-emerald">
                      {alert.anomaly_score.toFixed(2)}
                    </td>
                    <td className="py-3.5 text-slate-300 max-w-xs truncate">
                      {alert.reasons?.[0] || 'Statistical outlier'}
                    </td>
                    <td className="py-3.5">
                      <span className="px-2 py-0.5 rounded bg-slate-800 text-[10px] text-slate-300 border border-slate-700">
                        {alert.status}
                      </span>
                    </td>
                    <td className="py-3.5 pr-2 text-right">
                      <Link
                        to={`/entities/${encodeURIComponent(alert.entity_id)}`}
                        className="inline-flex items-center gap-1 px-2.5 py-1 rounded bg-slate-800 hover:bg-slate-700 text-[11px] text-slate-200 border border-slate-700 transition-colors"
                        onClick={(e) => e.stopPropagation()}
                      >
                        <span>Inspect Dossier</span>
                        <ArrowUpRight className="w-3 h-3" />
                      </Link>
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
