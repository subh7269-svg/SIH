import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  Upload,
  Database,
  FileText,
  CheckCircle2,
  AlertTriangle,
  Trash2,
  RefreshCw,
  Clock,
  Layers,
  ArrowRight
} from 'lucide-react';
import { getDatasets, uploadDataset, deleteDataset, getDataset } from '../services/api';
import { Badge } from '../components/common/Badge';
import { Dataset } from '../types';

export const DatasetsPage: React.FC = () => {
  const queryClient = useQueryClient();
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [runMlAfter, setRunMlAfter] = useState<boolean>(true);
  const [selectedDataset, setSelectedDataset] = useState<Dataset | null>(null);
  const [uploadError, setUploadError] = useState<string | null>(null);

  const { data: datasetsData, isLoading } = useQuery({
    queryKey: ['datasets'],
    queryFn: getDatasets,
  });

  const uploadMutation = useMutation({
    mutationFn: (file: File) => uploadDataset(file, runMlAfter),
    onSuccess: (newDataset) => {
      queryClient.invalidateQueries({ queryKey: ['datasets'] });
      queryClient.invalidateQueries({ queryKey: ['alerts'] });
      setSelectedFile(null);
      setSelectedDataset(newDataset);
      setUploadError(null);
    },
    onError: (err: any) => {
      setUploadError(err.message || 'Failed to upload dataset.');
    },
  });

  const deleteMutation = useMutation({
    mutationFn: deleteDataset,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['datasets'] });
      setSelectedDataset(null);
    },
  });

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      setSelectedFile(e.target.files[0]);
      setUploadError(null);
    }
  };

  const handleUpload = () => {
    if (selectedFile) {
      uploadMutation.mutate(selectedFile);
    }
  };

  return (
    <div className="space-y-6 font-mono">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-cyber-border pb-4">
        <div>
          <h1 className="text-xl font-bold text-slate-100 flex items-center gap-2">
            <Database className="w-5 h-5 text-cyber-emerald" />
            <span>BULK DATA INGESTION & DATA QUALITY HUB</span>
          </h1>
          <p className="text-xs text-slate-400 mt-1">
            Streaming ingestion engine supporting CSV, JSON, and XML formats with offline GeoIP correlation.
          </p>
        </div>
      </div>

      {/* Upload Box */}
      <div className="cyber-card p-6 border-dashed border-2 border-cyber-border hover:border-cyber-emerald/50 transition-all">
        <div className="flex flex-col items-center justify-center text-center space-y-4">
          <div className="p-4 rounded-full bg-emerald-500/10 text-cyber-emerald">
            <Upload className="w-8 h-8" />
          </div>
          <div>
            <h3 className="text-sm font-semibold text-slate-100">
              Drag & drop Bitcoin Transaction / Network Metadata
            </h3>
            <p className="text-xs text-slate-400 mt-1">
              Supports <span className="text-cyber-cyan font-bold">.csv</span>, <span className="text-cyber-cyan font-bold">.json</span>, and <span className="text-cyber-cyan font-bold">.xml</span> files (Up to 100MB chunked streaming)
            </p>
          </div>

          <input
            type="file"
            id="dataset-upload"
            className="hidden"
            accept=".csv,.json,.xml"
            onChange={handleFileChange}
          />
          <label
            htmlFor="dataset-upload"
            className="px-4 py-2 rounded-lg bg-slate-800 hover:bg-slate-700 text-xs font-semibold text-slate-200 border border-slate-700 cursor-pointer transition-colors"
          >
            Browse Local File
          </label>

          {selectedFile && (
            <div className="flex flex-col items-center gap-3 pt-2">
              <div className="flex items-center gap-2 text-xs text-cyber-emerald bg-emerald-500/10 px-3 py-1.5 rounded-md border border-emerald-500/20">
                <FileText className="w-4 h-4" />
                <span>Selected: {selectedFile.name} ({(selectedFile.size / 1024).toFixed(1)} KB)</span>
              </div>

              <div className="flex items-center gap-2 text-xs text-slate-300">
                <input
                  type="checkbox"
                  id="run-ml"
                  checked={runMlAfter}
                  onChange={(e) => setRunMlAfter(e.target.checked)}
                  className="rounded bg-slate-900 border-slate-700 text-cyber-emerald focus:ring-0"
                />
                <label htmlFor="run-ml">Automatically run Isolation Forest ML & Clustering after ingestion</label>
              </div>

              <button
                onClick={handleUpload}
                disabled={uploadMutation.isPending}
                className="flex items-center gap-2 px-5 py-2 rounded-lg bg-cyber-emerald text-slate-950 font-bold text-xs hover:bg-emerald-400 transition-all shadow-glow-emerald disabled:opacity-50"
              >
                {uploadMutation.isPending ? (
                  <>
                    <RefreshCw className="w-4 h-4 animate-spin" />
                    <span>Processing Stream & Ingesting...</span>
                  </>
                ) : (
                  <>
                    <Upload className="w-4 h-4" />
                    <span>Start Ingestion Pipeline</span>
                  </>
                )}
              </button>
            </div>
          )}

          {uploadError && (
            <div className="text-xs text-red-400 bg-red-500/10 px-3 py-2 rounded border border-red-500/20 flex items-center gap-2">
              <AlertTriangle className="w-4 h-4 shrink-0" />
              <span>{uploadError}</span>
            </div>
          )}
        </div>
      </div>

      {/* Main Grid: Dataset List & Data Quality Report */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Datasets Table */}
        <div className="cyber-card p-5 lg:col-span-2 space-y-4">
          <div className="flex items-center justify-between border-b border-cyber-border pb-3">
            <h2 className="text-sm font-semibold text-slate-100 uppercase tracking-wider">
              Ingested Datasets ({datasetsData?.total || 0})
            </h2>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead>
                <tr className="border-b border-slate-800 text-slate-400 uppercase text-[10px]">
                  <th className="pb-3 pl-2">Filename</th>
                  <th className="pb-3">Format</th>
                  <th className="pb-3">Records (Valid/Total)</th>
                  <th className="pb-3">Status</th>
                  <th className="pb-3">Uploaded</th>
                  <th className="pb-3 pr-2 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60 text-slate-200">
                {isLoading ? (
                  <tr><td colSpan={6} className="py-6 text-center text-slate-500">Loading datasets...</td></tr>
                ) : !datasetsData?.datasets || datasetsData.datasets.length === 0 ? (
                  <tr><td colSpan={6} className="py-6 text-center text-slate-500">No datasets uploaded yet.</td></tr>
                ) : (
                  datasetsData.datasets.map((ds) => (
                    <tr
                      key={ds.id}
                      onClick={() => setSelectedDataset(ds)}
                      className={`hover:bg-slate-800/40 cursor-pointer transition-colors ${
                        selectedDataset?.id === ds.id ? 'bg-slate-800/60 border-l-2 border-cyber-emerald' : ''
                      }`}
                    >
                      <td className="py-3 pl-2 font-medium text-slate-100 flex items-center gap-2">
                        <FileText className="w-3.5 h-3.5 text-cyber-cyan" />
                        <span>{ds.filename}</span>
                      </td>
                      <td className="py-3 uppercase text-slate-400">{ds.format}</td>
                      <td className="py-3">
                        <span className="text-cyber-emerald font-bold">{ds.processed_records}</span>
                        <span className="text-slate-500"> / {ds.total_records}</span>
                      </td>
                      <td className="py-3">
                        <Badge variant={ds.status === 'COMPLETED' ? 'success' : ds.status === 'FAILED' ? 'critical' : 'info'}>
                          {ds.status}
                        </Badge>
                      </td>
                      <td className="py-3 text-slate-500 text-[11px]">
                        {new Date(ds.uploaded_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                      </td>
                      <td className="py-3 pr-2 text-right">
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            deleteMutation.mutate(ds.id);
                          }}
                          className="p-1 text-slate-500 hover:text-red-400 transition-colors"
                          title="Delete Dataset"
                        >
                          <Trash2 className="w-3.5 h-3.5" />
                        </button>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>

        {/* Data Quality Report Panel */}
        <div className="cyber-card p-5 space-y-4">
          <div className="flex items-center justify-between border-b border-cyber-border pb-3">
            <h2 className="text-sm font-semibold text-slate-100 uppercase tracking-wider flex items-center gap-1.5">
              <CheckCircle2 className="w-4 h-4 text-cyber-emerald" />
              <span>Data Quality Report</span>
            </h2>
          </div>

          {selectedDataset?.data_quality_metrics ? (
            <div className="space-y-4 text-xs">
              <div className="p-3 rounded-lg bg-slate-900/80 border border-slate-800 space-y-2">
                <div className="flex justify-between">
                  <span className="text-slate-400">Total Rows Evaluated:</span>
                  <span className="font-bold text-slate-100">{selectedDataset.data_quality_metrics.total_records}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-400">Valid Ingested Records:</span>
                  <span className="font-bold text-cyber-emerald">{selectedDataset.data_quality_metrics.valid_records}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-400">Rejected / Malformed:</span>
                  <span className="font-bold text-red-400">{selectedDataset.data_quality_metrics.rejected_records}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-400">Duplicates Detected:</span>
                  <span className="font-bold text-amber-400">{selectedDataset.data_quality_metrics.duplicate_records}</span>
                </div>
              </div>

              {/* Entity Breakdown */}
              <div className="space-y-2">
                <p className="text-[10px] text-slate-500 uppercase tracking-wider font-semibold">Indexed Entities</p>
                <div className="grid grid-cols-2 gap-2 text-center">
                  <div className="p-2 rounded bg-slate-900 border border-slate-800">
                    <p className="text-[10px] text-slate-500">Wallets</p>
                    <p className="text-sm font-bold text-slate-100">{selectedDataset.data_quality_metrics.unique_wallets}</p>
                  </div>
                  <div className="p-2 rounded bg-slate-900 border border-slate-800">
                    <p className="text-[10px] text-slate-500">Relay IPs</p>
                    <p className="text-sm font-bold text-slate-100">{selectedDataset.data_quality_metrics.unique_src_ips}</p>
                  </div>
                  <div className="p-2 rounded bg-slate-900 border border-slate-800">
                    <p className="text-[10px] text-slate-500">Countries</p>
                    <p className="text-sm font-bold text-slate-100">{selectedDataset.data_quality_metrics.unique_countries}</p>
                  </div>
                  <div className="p-2 rounded bg-slate-900 border border-slate-800">
                    <p className="text-[10px] text-slate-500">ASNs</p>
                    <p className="text-sm font-bold text-slate-100">{selectedDataset.data_quality_metrics.unique_asns}</p>
                  </div>
                </div>
              </div>

              {/* Rejection Reasons if any */}
              {Object.keys(selectedDataset.data_quality_metrics.rejected_reasons || {}).length > 0 && (
                <div className="p-3 rounded-lg bg-red-500/5 border border-red-500/20 space-y-1.5">
                  <p className="text-[10px] font-semibold text-red-400 uppercase">Rejection Log</p>
                  {Object.entries(selectedDataset.data_quality_metrics.rejected_reasons).map(([reason, count]) => (
                    <div key={reason} className="flex justify-between text-[11px] text-slate-300">
                      <span className="truncate max-w-[180px]">{reason}</span>
                      <span className="text-red-400 font-bold">x{count}</span>
                    </div>
                  ))}
                </div>
              )}
            </div>
          ) : (
            <div className="py-12 text-center text-xs text-slate-500">
              Select a dataset from the list to view its comprehensive Data Quality & validation metrics.
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
