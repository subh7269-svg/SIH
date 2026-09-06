import React, { useState } from 'react';
import { useQuery, useMutation } from '@tanstack/react-query';
import {
  FileSpreadsheet,
  Download,
  Printer,
  ShieldCheck,
  Search,
  CheckCircle2,
  AlertTriangle,
  FileText
} from 'lucide-react';
import { generateReport, getAlerts } from '../services/api';
import { InvestigationReport } from '../types';

export const ReportsPage: React.FC = () => {
  const [targetEntityId, setTargetEntityId] = useState('');
  const [reportTitle, setReportTitle] = useState('Forensic Lead Intelligence Brief');
  const [analystNotes, setAnalystNotes] = useState('Priority anomalous lead flagged for manual investigator verification.');
  const [generatedReport, setGeneratedReport] = useState<InvestigationReport | null>(null);

  const { data: alertsData } = useQuery({
    queryKey: ['alerts'],
    queryFn: () => getAlerts({ limit: 10 }),
  });

  const reportMutation = useMutation({
    mutationFn: generateReport,
    onSuccess: (data) => {
      setGeneratedReport(data);
    },
  });

  const handleGenerate = (e: React.FormEvent) => {
    e.preventDefault();
    if (targetEntityId.trim()) {
      reportMutation.mutate({
        title: reportTitle,
        entity_id: targetEntityId.trim(),
        include_evidence: true,
        analyst_notes: analystNotes,
      });
    }
  };

  const handlePrint = () => {
    window.print();
  };

  const handleDownloadMarkdown = () => {
    if (!generatedReport) return;
    const blob = new Blob([generatedReport.markdown_content], { type: 'text/markdown;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `${generatedReport.report_id}.md`;
    link.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="space-y-6 font-mono">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-cyber-border pb-4 print:hidden">
        <div>
          <h1 className="text-xl font-bold text-slate-100 flex items-center gap-2">
            <FileSpreadsheet className="w-5 h-5 text-cyber-emerald" />
            <span>FORENSIC INVESTIGATION REPORT GENERATOR</span>
          </h1>
          <p className="text-xs text-slate-400 mt-1">
            Export structured, evidence-backed investigative briefs distinguishing empirical data from statistical model inference.
          </p>
        </div>
      </div>

      {/* Generator Form */}
      <div className="cyber-card p-5 space-y-4 print:hidden">
        <form onSubmit={handleGenerate} className="grid grid-cols-1 md:grid-cols-3 gap-4 text-xs">
          <div>
            <label className="block text-slate-400 mb-1">Target Entity Identifier</label>
            <input
              type="text"
              value={targetEntityId}
              onChange={(e) => setTargetEntityId(e.target.value)}
              placeholder="bc1q... / Wallet / TXID"
              className="w-full bg-slate-900 border border-slate-700 rounded-lg p-2.5 text-slate-100 placeholder-slate-500 focus:outline-none focus:border-cyber-emerald"
            />
            {/* Quick picker from alerts */}
            {alertsData?.alerts && alertsData.alerts.length > 0 && (
              <div className="flex items-center gap-1.5 mt-2 flex-wrap text-[10px]">
                <span className="text-slate-500">Quick Select:</span>
                {alertsData.alerts.slice(0, 3).map((a) => (
                  <button
                    key={a.id}
                    type="button"
                    onClick={() => setTargetEntityId(a.entity_id)}
                    className="text-cyber-cyan hover:underline"
                  >
                    {a.entity_id.slice(0, 10)}...
                  </button>
                ))}
              </div>
            )}
          </div>

          <div>
            <label className="block text-slate-400 mb-1">Report Title</label>
            <input
              type="text"
              value={reportTitle}
              onChange={(e) => setReportTitle(e.target.value)}
              className="w-full bg-slate-900 border border-slate-700 rounded-lg p-2.5 text-slate-100 focus:outline-none focus:border-cyber-emerald"
            />
          </div>

          <div className="flex items-end">
            <button
              type="submit"
              disabled={reportMutation.isPending || !targetEntityId.trim()}
              className="w-full py-2.5 px-4 bg-cyber-emerald text-slate-950 font-bold rounded-lg hover:bg-emerald-400 transition-all shadow-glow-emerald disabled:opacity-50 text-xs flex items-center justify-center gap-2"
            >
              <FileSpreadsheet className="w-4 h-4" />
              <span>{reportMutation.isPending ? 'Compiling Brief...' : 'Compile Forensic Report'}</span>
            </button>
          </div>
        </form>
      </div>

      {/* Generated Report Preview */}
      {generatedReport ? (
        <div className="space-y-4">
          {/* Action Bar */}
          <div className="flex items-center justify-between print:hidden">
            <span className="text-xs text-cyber-emerald font-bold flex items-center gap-1.5">
              <CheckCircle2 className="w-4 h-4" />
              <span>Report Ready: {generatedReport.report_id}</span>
            </span>

            <div className="flex items-center gap-2">
              <button
                onClick={handlePrint}
                className="flex items-center gap-1.5 px-3 py-1.5 rounded bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 text-xs transition-colors"
              >
                <Printer className="w-3.5 h-3.5" />
                <span>Print / Save PDF</span>
              </button>
              <button
                onClick={handleDownloadMarkdown}
                className="flex items-center gap-1.5 px-3 py-1.5 rounded bg-cyber-emerald text-slate-950 font-bold text-xs hover:bg-emerald-400 transition-all shadow-glow-emerald"
              >
                <Download className="w-3.5 h-3.5" />
                <span>Download Markdown</span>
              </button>
            </div>
          </div>

          {/* Formatted Report Document */}
          <div className="cyber-card p-8 space-y-6 text-xs bg-slate-950 text-slate-200 border border-slate-700 shadow-2xl print:border-none print:shadow-none print:p-0">
            {/* Report Header */}
            <div className="border-b border-slate-800 pb-4 flex justify-between items-start">
              <div>
                <span className="text-[10px] text-cyber-emerald uppercase font-bold tracking-widest block">
                  LEADFORGE FORENSIC INTELLIGENCE BRIEF
                </span>
                <h2 className="text-lg font-bold text-slate-100 mt-1">{generatedReport.title}</h2>
                <p className="text-slate-400 text-[11px] mt-0.5">
                  Target: <span className="text-cyber-cyan font-bold">{generatedReport.entity_id}</span> ({generatedReport.entity_type})
                </p>
              </div>
              <div className="text-right text-[11px] text-slate-400 space-y-0.5">
                <p>Report ID: <span className="text-slate-200 font-bold">{generatedReport.report_id}</span></p>
                <p>Generated: {new Date(generatedReport.generated_at).toUTCString()}</p>
                <p>Classification: <span className="text-amber-400 font-bold">LAW ENFORCEMENT SENSITIVE</span></p>
              </div>
            </div>

            {/* Mandatory Compliance Disclaimer */}
            <div className="p-3.5 rounded-lg bg-red-500/10 border border-red-500/30 text-[11px] text-red-300 leading-relaxed">
              <span className="font-bold text-red-200 uppercase block mb-1">MANDATORY FORENSIC DISCLAIMER</span>
              {generatedReport.disclaimer}
            </div>

            {/* Risk Assessment Scorecard */}
            <div className="grid grid-cols-3 gap-4 text-center">
              <div className="p-3 rounded bg-slate-900 border border-slate-800">
                <p className="text-[10px] text-slate-400 uppercase">Composite Priority Score</p>
                <p className="text-xl font-bold text-cyber-emerald mt-1">{generatedReport.risk_score}/100</p>
              </div>
              <div className="p-3 rounded bg-slate-900 border border-slate-800">
                <p className="text-[10px] text-slate-400 uppercase">Severity Category</p>
                <p className="text-xl font-bold text-orange-400 mt-1">{generatedReport.severity}</p>
              </div>
              <div className="p-3 rounded bg-slate-900 border border-slate-800">
                <p className="text-[10px] text-slate-400 uppercase">Isolation Forest Outlier Score</p>
                <p className="text-xl font-bold text-cyber-cyan mt-1">{generatedReport.anomaly_score.toFixed(2)}</p>
              </div>
            </div>

            {/* Mathematical Explainability */}
            <div className="space-y-2">
              <h3 className="text-xs font-bold text-slate-100 uppercase tracking-wider border-b border-slate-800 pb-1">
                1. Mathematical Explainability & Deviation Reasons
              </h3>
              <ul className="space-y-1.5 list-disc pl-5 text-slate-300">
                {generatedReport.explanation.map((reason, idx) => (
                  <li key={idx}>{reason}</li>
                ))}
              </ul>
            </div>

            {/* Transaction Evidence */}
            {generatedReport.transaction_evidence?.length > 0 && (
              <div className="space-y-2">
                <h3 className="text-xs font-bold text-slate-100 uppercase tracking-wider border-b border-slate-800 pb-1">
                  2. Associated Blockchain Transaction Records
                </h3>
                <div className="overflow-x-auto">
                  <table className="w-full text-left text-[11px]">
                    <thead>
                      <tr className="text-slate-500 border-b border-slate-800">
                        <th className="pb-1">TXID</th>
                        <th className="pb-1">Volume (BTC)</th>
                        <th className="pb-1">Timestamp</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-800/40 text-slate-300">
                      {generatedReport.transaction_evidence.slice(0, 5).map((tx, idx) => (
                        <tr key={idx}>
                          <td className="py-1.5 font-bold text-cyber-cyan">{tx.txid}</td>
                          <td className="py-1.5">{tx.input_total || tx.output_total || '-'}</td>
                          <td className="py-1.5 text-slate-500">{tx.timestamp || 'N/A'}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}

            {/* Network Layer Observations */}
            {generatedReport.network_observations?.length > 0 && (
              <div className="space-y-2">
                <h3 className="text-xs font-bold text-slate-100 uppercase tracking-wider border-b border-slate-800 pb-1">
                  3. Network Wire Observations (Relay Provenance)
                </h3>
                <p className="text-[10px] text-slate-500">
                  Network relay records demonstrate P2P propagation endpoints and do not assert cryptographic ownership.
                </p>
                <div className="overflow-x-auto">
                  <table className="w-full text-left text-[11px]">
                    <thead>
                      <tr className="text-slate-500 border-b border-slate-800">
                        <th className="pb-1">Relay IP</th>
                        <th className="pb-1">Country Jurisdiction</th>
                        <th className="pb-1">Autonomous System (ASN)</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-800/40 text-slate-300">
                      {generatedReport.network_observations.slice(0, 5).map((ipo, idx) => (
                        <tr key={idx}>
                          <td className="py-1.5 font-bold text-purple-400">{ipo.ip}</td>
                          <td className="py-1.5">{ipo.country}</td>
                          <td className="py-1.5 text-slate-400">{ipo.asn}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}
          </div>
        </div>
      ) : (
        <div className="cyber-card p-12 text-center text-xs text-slate-500">
          Enter an entity identifier above and click "Compile Forensic Report" to generate an exportable intelligence lead brief.
        </div>
      )}
    </div>
  );
};
