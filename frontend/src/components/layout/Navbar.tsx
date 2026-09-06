import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Search, ShieldAlert, Play, RefreshCw, Radio, HardDriveDownload, User as UserIcon } from 'lucide-react';
import { runDemo, resetDemo } from '../../services/api';

interface NavbarProps {
  onDemoSuccess?: () => void;
}

export const Navbar: React.FC<NavbarProps> = ({ onDemoSuccess }) => {
  const navigate = useNavigate();
  const [searchQuery, setSearchQuery] = useState('');
  const [isDemoRunning, setIsDemoRunning] = useState(false);
  const [demoMessage, setDemoMessage] = useState<string | null>(null);

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    if (searchQuery.trim()) {
      navigate(`/search?q=${encodeURIComponent(searchQuery.trim())}`);
    }
  };

  const handleRunDemo = async () => {
    try {
      setIsDemoRunning(true);
      setDemoMessage('Running synthetic pipeline & AI anomaly detector...');
      await runDemo(42);
      setDemoMessage('Demo pipeline completed successfully!');
      setTimeout(() => setDemoMessage(null), 4000);
      if (onDemoSuccess) onDemoSuccess();
      navigate('/');
    } catch (err: any) {
      setDemoMessage(`Demo failed: ${err.message}`);
    } finally {
      setIsDemoRunning(false);
    }
  };

  return (
    <header className="h-16 border-b border-cyber-border bg-cyber-bg/95 backdrop-blur-md sticky top-0 z-40 px-6 flex items-center justify-between">
      {/* Search Bar */}
      <form onSubmit={handleSearch} className="relative w-96">
        <Search className="w-4 h-4 absolute left-3.5 top-1/2 transform -translate-y-1/2 text-slate-400" />
        <input
          type="text"
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          placeholder="Search Wallet (bc1...), TXID, IP, or ASN..."
          className="w-full bg-cyber-card border border-cyber-border rounded-lg pl-10 pr-4 py-1.5 text-xs text-slate-100 placeholder-slate-500 focus:outline-none focus:border-cyber-emerald focus:ring-1 focus:ring-cyber-emerald transition-all font-mono"
        />
      </form>

      {/* Center demo status message */}
      {demoMessage && (
        <div className="text-xs font-mono text-cyber-emerald animate-pulse bg-emerald-500/10 px-3 py-1 rounded-full border border-emerald-500/30">
          {demoMessage}
        </div>
      )}

      {/* Action Buttons */}
      <div className="flex items-center gap-3">
        {/* Offline Badge */}
        <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-slate-900 border border-slate-800 text-[11px] font-mono text-emerald-400">
          <Radio className="w-3 h-3 text-emerald-400 animate-pulse" />
          <span>OFFLINE LOCAL MODE</span>
        </div>

        {/* 1-Click SIH Demo Trigger */}
        <button
          onClick={handleRunDemo}
          disabled={isDemoRunning}
          className="flex items-center gap-2 bg-gradient-to-r from-emerald-600 to-teal-600 hover:from-emerald-500 hover:to-teal-500 text-slate-950 font-bold px-3.5 py-1.5 rounded-lg text-xs transition-all shadow-glow-emerald disabled:opacity-50"
        >
          {isDemoRunning ? (
            <RefreshCw className="w-3.5 h-3.5 animate-spin text-slate-950" />
          ) : (
            <Play className="w-3.5 h-3.5 fill-current text-slate-950" />
          )}
          <span>{isDemoRunning ? 'Processing Demo...' : 'Run 1-Click SIH Demo'}</span>
        </button>

        {/* Investigator Profile */}
        <div className="flex items-center gap-2 pl-3 border-l border-slate-800 text-xs">
          <div className="w-7 h-7 rounded-full bg-emerald-500/20 border border-emerald-500/40 flex items-center justify-center text-emerald-400 font-mono font-bold">
            LF
          </div>
          <div className="hidden md:block">
            <p className="font-medium text-slate-200 text-[11px]">Lead Analyst</p>
            <p className="text-[10px] text-slate-500 font-mono">LF-9041</p>
          </div>
        </div>
      </div>
    </header>
  );
};
