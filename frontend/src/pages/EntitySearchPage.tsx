import React, { useState, useEffect } from 'react';
import { useSearchParams, useNavigate } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { Search, Wallet, Activity, Radio, ArrowUpRight, ShieldAlert, Hash } from 'lucide-react';
import { searchEntities } from '../services/api';
import { Badge } from '../components/common/Badge';

export const EntitySearchPage: React.FC = () => {
  const [searchParams, setSearchParams] = useSearchParams();
  const navigate = useNavigate();
  const initialQuery = searchParams.get('q') || '';
  const [searchTerm, setSearchTerm] = useState(initialQuery);

  const { data: searchData, isLoading, refetch } = useQuery({
    queryKey: ['search', searchTerm],
    queryFn: () => searchEntities(searchTerm),
    enabled: searchTerm.length > 0,
  });

  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (searchTerm.trim()) {
      setSearchParams({ q: searchTerm.trim() });
    }
  };

  const getEntityIcon = (type: string) => {
    switch (type) {
      case 'WALLET':
        return <Wallet className="w-4 h-4 text-cyber-emerald" />;
      case 'TRANSACTION':
        return <Activity className="w-4 h-4 text-cyber-cyan" />;
      case 'IP':
        return <Radio className="w-4 h-4 text-cyber-purple" />;
      default:
        return <Hash className="w-4 h-4 text-slate-400" />;
    }
  };

  return (
    <div className="space-y-6 font-mono">
      {/* Search Header */}
      <div className="border-b border-cyber-border pb-4">
        <h1 className="text-xl font-bold text-slate-100 flex items-center gap-2">
          <Search className="w-5 h-5 text-cyber-emerald" />
          <span>MULTI-TYPE ENTITY INTELLIGENCE SEARCH</span>
        </h1>
        <p className="text-xs text-slate-400 mt-1">
          Query cross-layer metadata by Bitcoin Address (bc1...), Transaction ID (TXID), IP Address, or ASN.
        </p>
      </div>

      {/* Big Search Input */}
      <form onSubmit={handleSearchSubmit} className="relative max-w-3xl">
        <Search className="w-5 h-5 absolute left-4 top-1/2 transform -translate-y-1/2 text-slate-400" />
        <input
          type="text"
          value={searchTerm}
          onChange={(e) => setSearchTerm(e.target.value)}
          placeholder="Enter Bitcoin Address, TXID, IP, or ASN..."
          className="w-full bg-cyber-card border border-cyber-border rounded-xl pl-12 pr-28 py-3.5 text-sm text-slate-100 placeholder-slate-500 focus:outline-none focus:border-cyber-emerald focus:ring-1 focus:ring-cyber-emerald shadow-lg"
        />
        <button
          type="submit"
          className="absolute right-2 top-1/2 transform -translate-y-1/2 px-4 py-2 bg-cyber-emerald text-slate-950 font-bold rounded-lg text-xs hover:bg-emerald-400 transition-all shadow-glow-emerald"
        >
          Search
        </button>
      </form>

      {/* Results Section */}
      <div className="space-y-4">
        <div className="flex items-center justify-between text-xs text-slate-400">
          <span>
            {searchTerm ? (
              <>Results for <span className="text-cyber-cyan font-bold">"{searchTerm}"</span> ({searchData?.total_results || 0} matches)</>
            ) : (
              'Enter a search query above to inspect entity records.'
            )}
          </span>
        </div>

        {isLoading ? (
          <div className="cyber-card p-12 text-center text-xs text-slate-500">
            Scanning entity indices...
          </div>
        ) : searchData?.results && searchData.results.length > 0 ? (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {searchData.results.map((res) => (
              <div
                key={res.entity_id}
                onClick={() => navigate(`/entities/${encodeURIComponent(res.entity_id)}`)}
                className="cyber-card p-4 hover:border-cyber-emerald/50 cursor-pointer transition-all space-y-3 group"
              >
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <div className="p-2 rounded-lg bg-slate-900 border border-slate-800">
                      {getEntityIcon(res.entity_type)}
                    </div>
                    <div>
                      <span className="text-xs font-bold text-slate-100 group-hover:text-cyber-emerald transition-colors font-mono">
                        {res.label}
                      </span>
                      <span className="block text-[10px] text-slate-500 uppercase">{res.entity_type}</span>
                    </div>
                  </div>

                  {res.risk_score > 0 && (
                    <Badge variant={res.risk_score >= 60 ? 'critical' : 'medium'}>
                      Risk: {res.risk_score}/100
                    </Badge>
                  )}
                </div>

                <p className="text-xs text-slate-400 border-t border-slate-800/80 pt-2 font-mono">
                  {res.subtext}
                </p>

                <div className="flex items-center justify-between text-[11px] text-slate-500 pt-1">
                  <span className="truncate max-w-[200px] text-[10px]">{res.entity_id}</span>
                  <span className="flex items-center gap-1 text-cyber-cyan group-hover:underline">
                    <span>Inspect Dossier</span>
                    <ArrowUpRight className="w-3 h-3" />
                  </span>
                </div>
              </div>
            ))}
          </div>
        ) : searchTerm ? (
          <div className="cyber-card p-12 text-center text-xs text-slate-500">
            No entities matching "{searchTerm}" found in indexed datasets.
          </div>
        ) : null}
      </div>
    </div>
  );
};
