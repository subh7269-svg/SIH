import React from 'react';
import { useQuery } from '@tanstack/react-query';
import { Link } from 'react-router-dom';
import { Boxes, Users, Activity, Radio, ArrowUpRight, Info } from 'lucide-react';
import { getClusters } from '../services/api';
import { Badge } from '../components/common/Badge';

export const ClustersPage: React.FC = () => {
  const { data: clustersData, isLoading } = useQuery({
    queryKey: ['clusters'],
    queryFn: () => getClusters(),
  });

  return (
    <div className="space-y-6 font-mono">
      {/* Header */}
      <div className="border-b border-cyber-border pb-4">
        <h1 className="text-xl font-bold text-slate-100 flex items-center gap-2">
          <Boxes className="w-5 h-5 text-cyber-purple" />
          <span>DBSCAN ENTITY CLUSTERING & BEHAVIORAL COHORTS</span>
        </h1>
        <p className="text-xs text-slate-400 mt-1">
          Unsupervised grouping of behaviorally correlated entities exhibiting similar velocity, fan-out, or network relay patterns.
        </p>
      </div>

      {/* Summary Row */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <div className="cyber-card p-4">
          <p className="text-[10px] text-slate-500 uppercase">Behavioral Cohorts Discovered</p>
          <p className="text-2xl font-bold text-slate-100 font-mono mt-1">
            {clustersData?.total_clusters || 0}
          </p>
          <p className="text-xs text-slate-400 mt-0.5">DBSCAN ε=0.7, MinSamples=3</p>
        </div>

        <div className="cyber-card p-4">
          <p className="text-[10px] text-slate-500 uppercase">Total Clustered Entities</p>
          <p className="text-2xl font-bold text-cyber-emerald font-mono mt-1">
            {clustersData?.clusters?.reduce((acc, c) => acc + (c.cluster_label !== -1 ? c.member_count : 0), 0) || 0}
          </p>
          <p className="text-xs text-slate-400 mt-0.5">Assigned to structured behavioral groups</p>
        </div>

        <div className="cyber-card p-4">
          <p className="text-[10px] text-slate-500 uppercase">Noise / Outlier Entities</p>
          <p className="text-2xl font-bold text-amber-400 font-mono mt-1">
            {clustersData?.noise_count || 0}
          </p>
          <p className="text-xs text-slate-400 mt-0.5">Entities with non-conforming traits</p>
        </div>
      </div>

      {/* Clusters List */}
      <div className="space-y-4">
        {isLoading ? (
          <div className="cyber-card p-12 text-center text-xs text-slate-500">
            Running density-based spatial clustering...
          </div>
        ) : !clustersData?.clusters || clustersData.clusters.length === 0 ? (
          <div className="cyber-card p-12 text-center text-xs text-slate-500">
            No clusters identified yet. Run demo mode or upload a dataset to compute behavioral groups.
          </div>
        ) : (
          clustersData.clusters.map((cluster) => (
            <div key={cluster.id} className="cyber-card p-5 space-y-4">
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-cyber-border pb-3">
                <div className="flex items-center gap-2.5">
                  <div className="p-2 rounded-lg bg-purple-500/10 border border-purple-500/30 text-purple-400">
                    <Boxes className="w-4 h-4" />
                  </div>
                  <div>
                    <h3 className="text-sm font-bold text-slate-100">{cluster.cluster_name}</h3>
                    <p className="text-xs text-slate-400">
                      Algorithm: <span className="text-cyber-cyan">{cluster.algorithm}</span> | Label ID: <span className="text-slate-300 font-bold">{cluster.cluster_label}</span>
                    </p>
                  </div>
                </div>

                <Badge variant={cluster.cluster_label === -1 ? 'neutral' : 'purple'} size="md">
                  {cluster.member_count} Members
                </Badge>
              </div>

              {/* Mean Characteristics */}
              {cluster.characteristics && Object.keys(cluster.characteristics).length > 0 && (
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 text-xs bg-slate-900/60 p-3 rounded-lg border border-slate-800">
                  <div>
                    <span className="text-slate-500 text-[10px]">Avg Velocity:</span>
                    <p className="font-bold text-slate-200">
                      {cluster.characteristics.tx_velocity_per_hour?.toFixed(2) || '0.00'} tx/hr
                    </p>
                  </div>
                  <div>
                    <span className="text-slate-500 text-[10px]">Avg Counterparties:</span>
                    <p className="font-bold text-slate-200">
                      {cluster.characteristics.unique_counterparties?.toFixed(1) || '0.0'} peers
                    </p>
                  </div>
                  <div>
                    <span className="text-slate-500 text-[10px]">Avg Observed IPs:</span>
                    <p className="font-bold text-slate-200">
                      {cluster.characteristics.unique_observed_ips?.toFixed(1) || '0.0'} IPs
                    </p>
                  </div>
                  <div>
                    <span className="text-slate-500 text-[10px]">Avg BTC Sent:</span>
                    <p className="font-bold text-cyber-emerald">
                      {cluster.characteristics.total_outgoing_btc?.toFixed(3) || '0.000'} BTC
                    </p>
                  </div>
                </div>
              )}

              {/* Sample Members */}
              <div>
                <p className="text-[10px] text-slate-500 uppercase tracking-wider mb-2">Member Entities</p>
                <div className="flex flex-wrap gap-2">
                  {cluster.member_ids?.slice(0, 10).map((id) => (
                    <Link
                      key={id}
                      to={`/entities/${encodeURIComponent(id)}`}
                      className="px-2.5 py-1 rounded bg-slate-800 hover:bg-slate-700 text-[11px] text-cyber-cyan border border-slate-700 flex items-center gap-1 transition-colors"
                    >
                      <span>{id.length > 18 ? `${id.slice(0, 8)}...${id.slice(-6)}` : id}</span>
                      <ArrowUpRight className="w-3 h-3 text-slate-400" />
                    </Link>
                  ))}
                  {cluster.member_ids?.length > 10 && (
                    <span className="px-2 py-1 text-[11px] text-slate-500">
                      +{cluster.member_ids.length - 10} more
                    </span>
                  )}
                </div>
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
};
