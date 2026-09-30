import React, { useState, useEffect } from 'react';
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
  ArrowRight,
  HardDrive,
  Zap,
} from 'lucide-react';
import { getDatasets, uploadDataset, deleteDataset, getDataset, ingestLocalDataset } from '../services/api';
import { Badge } from '../components/common/Badge';
import { Dataset } from '../types';

export const DatasetsPage: React.FC = () => {
  const queryClient = useQueryClient();
  const [selectedFiles, setSelectedFiles] = useState<File[]>([]);
  const [fileStatuses, setFileStatuses] = useState<Record<string, { status: 'QUEUED' | 'INGESTING' | 'PROCESSING' | 'COMPLETED' | 'FAILED'; error?: string; dataset?: Dataset }>>({});
  const [isUploading, setIsUploading] = useState<boolean>(false);
  const [isDragging, setIsDragging] = useState<boolean>(false);
  const [runMlAfter, setRunMlAfter] = useState<boolean>(true);
  const [selectedDataset, setSelectedDataset] = useState<Dataset | null>(null);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<'upload' | 'local'>('upload');
  const [localFilePath, setLocalFilePath] = useState<string>('C:\\Users\\ASUS\\Documents\\DATASET\\correlation_output\\unified_correlated_dataset_part_001.csv');
  const [isIngestingLocal, setIsIngestingLocal] = useState<boolean>(false);


  const { data: datasetsData, isLoading, refetch: refetchDatasets } = useQuery({
    queryKey: ['datasets'],
    queryFn: getDatasets,
    refetchInterval: 3_000,
  });

  // Keep fileStatuses and selectedDataset synchronized with polled datasetsData strictly by ID
  useEffect(() => {
    if (!datasetsData?.datasets || datasetsData.datasets.length === 0) return;

    setFileStatuses(prev => {
      let changed = false;
      const next = { ...prev };

      for (const [filename, fileState] of Object.entries(next)) {
        if (fileState.dataset?.id) {
          const matching = datasetsData.datasets.find(d => d.id === fileState.dataset!.id);
          if (matching && matching.status !== fileState.status) {
            next[filename] = {
              status: matching.status as any,
              error: matching.error_summary,
              dataset: matching,
            };
            changed = true;
          }
        }
      }
      return changed ? next : prev;
    });

    // Also update selectedDataset if it has updated in the background
    setSelectedDataset(prev => {
      if (!prev) return prev;
      const updated = datasetsData.datasets.find(d => d.id === prev.id);
      if (updated && (updated.status !== prev.status || updated.processed_records !== prev.processed_records)) {
        return updated;
      }
      return prev;
    });
  }, [datasetsData]);

  const deleteMutation = useMutation({
    mutationFn: deleteDataset,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['datasets'] });
      setSelectedDataset(null);
    },
  });

  const formatFileSize = (bytes: number): string => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    if (bytes < 1024 * 1024 * 1024) return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
    return `${(bytes / (1024 * 1024 * 1024)).toFixed(2)} GB`;
  };

  const addFiles = (newFiles: FileList | File[]) => {
    const validExts = ['.csv', '.json', '.xml'];
    const filtered: File[] = [];
    for (let i = 0; i < newFiles.length; i++) {
      const file = newFiles[i];
      const lower = file.name.toLowerCase();
      if (validExts.some(ext => lower.endsWith(ext))) {
        filtered.push(file);
      }
    }
    if (filtered.length === 0) {
      setUploadError('Please select valid .csv, .json, or .xml files.');
      return;
    }
    setSelectedFiles(prev => {
      const existingNames = new Set(prev.map(f => f.name));
      const combined = [...prev, ...filtered.filter(f => !existingNames.has(f.name))];
      return combined;
    });
    setUploadError(null);
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      addFiles(e.target.files);
      e.target.value = '';
    }
  };

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(true);
  };

  const handleDragLeave = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      addFiles(e.dataTransfer.files);
    }
  };

  const removeFile = (index: number) => {
    setSelectedFiles(prev => prev.filter((_, idx) => idx !== index));
  };

  const handleUploadAll = async () => {
    if (selectedFiles.length === 0 || isUploading) return;

    setIsUploading(true);
    setUploadError(null);

    const initialStatuses: Record<string, { status: 'QUEUED' | 'INGESTING' | 'PROCESSING' | 'COMPLETED' | 'FAILED'; error?: string; dataset?: Dataset }> = {};
    selectedFiles.forEach(f => {
      initialStatuses[f.name] = { status: 'QUEUED' };
    });
    setFileStatuses(initialStatuses);

    let lastDataset: Dataset | null = null;
    let anyFailed = false;

    for (const file of selectedFiles) {
      setFileStatuses(prev => ({
        ...prev,
        [file.name]: { status: 'INGESTING' },
      }));

      try {
        // Backend returns immediately with status=PENDING/PROCESSING and processes in background
        const dataset = await uploadDataset(file, runMlAfter);
        lastDataset = dataset;

        if (dataset.status === 'FAILED') {
          anyFailed = true;
          setFileStatuses(prev => ({
            ...prev,
            [file.name]: { status: 'FAILED', error: dataset.error_summary || 'Ingestion failed on server', dataset },
          }));
        } else if (dataset.status === 'COMPLETED') {
          setFileStatuses(prev => ({
            ...prev,
            [file.name]: { status: 'COMPLETED', dataset },
          }));
        } else {
          // Dataset is PENDING/PROCESSING — successfully queued for background worker
          setFileStatuses(prev => ({
            ...prev,
            [file.name]: { status: 'PROCESSING', dataset },
          }));
        }
        // Immediately refetch so the new dataset shows in the table
        queryClient.invalidateQueries({ queryKey: ['datasets'] });
      } catch (err: any) {
        anyFailed = true;
        const msg = err?.message || 'Upload failed. Check server connection or file format.';
        setFileStatuses(prev => ({
          ...prev,
          [file.name]: { status: 'FAILED', error: msg },
        }));
      }
    }

    if (lastDataset) {
      setSelectedDataset(lastDataset);
    }

    setIsUploading(false);
    if (anyFailed) {
      setUploadError('Some files failed to upload. Successfully queued datasets are processing in the background.');
    }
  };

  const handleLocalIngest = async (pathOverride?: string) => {
    const targetPath = (pathOverride || localFilePath).trim();
    if (!targetPath) {
      setUploadError('Please provide a valid local disk file path.');
      return;
    }

    setIsIngestingLocal(true);
    setUploadError(null);

    try {
      const ds = await ingestLocalDataset(targetPath, runMlAfter);
      setSelectedDataset(ds);
      queryClient.invalidateQueries({ queryKey: ['datasets'] });
      setLocalFilePath('');
    } catch (err: any) {
      setUploadError(err?.message || 'Local file ingestion failed.');
    } finally {
      setIsIngestingLocal(false);
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
            Upload multiple files at once or stream directly from local NVMe/SSD disk • CSV / JSON / XML
          </p>
        </div>
      </div>

      {/* Mode Switcher: Browser Upload vs Direct Local Disk */}
      <div className="flex items-center gap-3 border-b border-cyber-border/80 pb-2">
        <button
          type="button"
          onClick={() => setActiveTab('upload')}
          className={`flex items-center gap-2 px-4 py-2 rounded-t-lg text-xs font-semibold border-b-2 transition-all ${
            activeTab === 'upload'
              ? 'border-cyber-emerald text-cyber-emerald bg-cyber-emerald/10'
              : 'border-transparent text-slate-400 hover:text-slate-200'
          }`}
        >
          <Upload className="w-4 h-4" />
          <span>Browser Multi-File Upload</span>
        </button>
        <button
          type="button"
          onClick={() => setActiveTab('local')}
          className={`flex items-center gap-2 px-4 py-2 rounded-t-lg text-xs font-semibold border-b-2 transition-all ${
            activeTab === 'local'
              ? 'border-cyber-cyan text-cyber-cyan bg-cyber-cyan/10'
              : 'border-transparent text-slate-400 hover:text-slate-200'
          }`}
        >
          <HardDrive className="w-4 h-4" />
          <span>Direct Local Disk Ingestion (Instant 0-Upload)</span>
          <span className="px-1.5 py-0.5 rounded text-[10px] bg-cyber-cyan/20 text-cyber-cyan border border-cyber-cyan/30">Recommended for &gt;100MB</span>
        </button>
      </div>

      {/* Direct Local Disk Ingestion Box */}
      {activeTab === 'local' && (
        <div className="cyber-card p-6 border border-cyber-cyan/40 bg-slate-900/60 space-y-4">
          <div className="flex items-start justify-between flex-wrap gap-2">
            <div className="space-y-1">
              <h3 className="text-sm font-bold text-slate-100 flex items-center gap-2">
                <HardDrive className="w-4 h-4 text-cyber-cyan" />
                <span>Direct Local Disk Streaming Ingestion</span>
              </h3>
              <p className="text-xs text-slate-400">
                Bypasses browser multipart HTTP upload entirely. Streams raw Bitcoin transaction &amp; network data directly from your local drive at native speed (~2 GB/s).
              </p>
            </div>
            <span className="px-2 py-1 rounded text-[10px] font-mono bg-cyber-emerald/10 text-cyber-emerald border border-cyber-emerald/30">
              FASTEST FOR 650MB+ FILES
            </span>
          </div>

          <div className="space-y-2">
            <label className="text-xs font-semibold text-slate-300">Local Absolute File Path (.csv, .json, .xml):</label>
            <div className="flex flex-col sm:flex-row gap-2">
              <input
                type="text"
                value={localFilePath}
                onChange={(e) => setLocalFilePath(e.target.value)}
                placeholder="C:\Users\ASUS\Documents\DATASET\correlation_output\unified_correlated_dataset_part_001.csv"
                className="flex-1 bg-slate-950 border border-slate-700 rounded-lg px-3 py-2 text-xs font-mono text-slate-200 focus:outline-none focus:border-cyber-cyan"
                disabled={isIngestingLocal}
              />
              <button
                type="button"
                onClick={() => handleLocalIngest()}
                disabled={isIngestingLocal || !localFilePath.trim()}
                className="px-5 py-2 rounded-lg bg-cyber-cyan text-slate-950 font-bold text-xs hover:bg-cyan-300 transition-all flex items-center justify-center gap-2 disabled:opacity-50 shrink-0"
              >
                {isIngestingLocal ? (
                  <>
                    <RefreshCw className="w-4 h-4 animate-spin" />
                    <span>Ingesting from Disk...</span>
                  </>
                ) : (
                  <>
                    <Zap className="w-4 h-4" />
                    <span>Start Direct Disk Ingestion</span>
                  </>
                )}
              </button>
            </div>
          </div>

          {/* Quick Preset Buttons */}
          <div className="flex flex-wrap items-center gap-2 pt-1 text-xs">
            <span className="text-slate-400 text-[11px]">Quick Preset:</span>
            <button
              type="button"
              onClick={() => {
                const path = 'C:\\Users\\ASUS\\Documents\\DATASET\\correlation_output\\unified_correlated_dataset_part_001.csv';
                setLocalFilePath(path);
                handleLocalIngest(path);
              }}
              disabled={isIngestingLocal}
              className="px-2.5 py-1 rounded bg-slate-800 hover:bg-slate-700 text-cyber-cyan border border-cyber-cyan/30 text-[11px] flex items-center gap-1.5 transition-colors"
            >
              <Zap className="w-3 h-3" />
              <span>Ingest unified_correlated_dataset_part_001.csv (658 MB)</span>
            </button>
          </div>

          <div className="flex items-center gap-2 text-xs text-slate-300 pt-2 border-t border-slate-800">
            <input
              type="checkbox"
              id="run-ml-local"
              checked={runMlAfter}
              onChange={(e) => setRunMlAfter(e.target.checked)}
              disabled={isIngestingLocal}
              className="rounded bg-slate-900 border-slate-700 text-cyber-emerald focus:ring-0"
            />
            <label htmlFor="run-ml-local">Automatically run Isolation Forest ML &amp; Clustering after ingestion</label>
          </div>

          {uploadError && (
            <div className="text-xs text-red-400 bg-red-500/10 px-3 py-2 rounded border border-red-500/20 flex items-center gap-2">
              <AlertTriangle className="w-4 h-4 shrink-0" />
              <span>{uploadError}</span>
            </div>
          )}
        </div>
      )}

      {/* Upload Box */}
      {activeTab === 'upload' && (
      <div
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
        className={`cyber-card p-6 border-dashed border-2 transition-all ${
          isDragging
            ? 'border-cyber-emerald bg-emerald-500/10'
            : 'border-cyber-border hover:border-cyber-emerald/50'
        }`}
      >
        <div className="flex flex-col items-center justify-center text-center space-y-4">
          <div className="p-4 rounded-full bg-emerald-500/10 text-cyber-emerald">
            <Upload className="w-8 h-8" />
          </div>
          <div>
            <h3 className="text-sm font-semibold text-slate-100">
              Drag & drop Bitcoin Transaction / Network Metadata
            </h3>
            <p className="text-xs text-slate-400 mt-1">
              Supports large <span className="text-cyber-cyan font-bold">CSV</span>, <span className="text-cyber-cyan font-bold">JSON</span>, and <span className="text-cyber-cyan font-bold">XML</span> files with chunked streaming
            </p>
          </div>

          <input
            type="file"
            id="dataset-upload"
            className="hidden"
            accept=".csv,.json,.xml"
            multiple
            onChange={handleFileChange}
          />
          <div className="flex items-center gap-2">
            <label
              htmlFor="dataset-upload"
              className="px-4 py-2 rounded-lg bg-slate-800 hover:bg-slate-700 text-xs font-semibold text-slate-200 border border-slate-700 cursor-pointer transition-colors"
            >
              Browse Files (Multiple Allowed)
            </label>
            {selectedFiles.length > 0 && !isUploading && (
              <button
                type="button"
                onClick={() => { setSelectedFiles([]); setFileStatuses({}); }}
                className="px-3 py-2 rounded-lg bg-slate-900 hover:bg-slate-800 text-xs text-slate-400 border border-slate-800"
              >
                Clear Selection
              </button>
            )}
          </div>

          {selectedFiles.length > 0 && (
            <div className="w-full max-w-2xl flex flex-col gap-3 pt-2 text-left">
              {/* Selected Files List */}
              <div className="bg-slate-900/90 border border-slate-800 rounded-lg p-3 max-h-56 overflow-y-auto space-y-2">
                <div className="text-[11px] font-bold text-slate-400 uppercase tracking-wider flex justify-between">
                  <span>Selected Files ({selectedFiles.length})</span>
                  <span>Total Size: {formatFileSize(selectedFiles.reduce((acc, f) => acc + f.size, 0))}</span>
                </div>
                {selectedFiles.map((file, idx) => {
                  const statusInfo = fileStatuses[file.name];
                  return (
                    <div
                      key={idx}
                      className="flex flex-col gap-1 text-xs bg-slate-950/80 px-3 py-2.5 rounded border border-slate-800/80"
                    >
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-2 min-w-0">
                          <FileText className="w-4 h-4 text-cyber-cyan shrink-0" />
                          <span className="truncate text-slate-200 font-medium">{file.name}</span>
                          <span className="text-[10px] text-slate-500 shrink-0">({formatFileSize(file.size)})</span>
                        </div>
                        <div className="flex items-center gap-2 shrink-0 ml-3">
                          {statusInfo ? (
                            statusInfo.status === 'INGESTING' ? (
                              <span className="flex items-center gap-1 text-[11px] text-cyber-cyan font-bold animate-pulse">
                                <RefreshCw className="w-3 h-3 animate-spin" /> Uploading...
                              </span>
                            ) : statusInfo.status === 'PROCESSING' ? (
                              <span className="flex items-center gap-1 text-[11px] text-cyber-cyan font-bold">
                                <RefreshCw className="w-3 h-3 animate-spin" /> Ingesting in background...
                              </span>
                            ) : statusInfo.status === 'COMPLETED' ? (
                              <span className="flex items-center gap-1 text-[11px] text-cyber-emerald font-bold">
                                <CheckCircle2 className="w-3 h-3" /> Completed
                              </span>
                            ) : statusInfo.status === 'FAILED' ? (
                              <span className="flex items-center gap-1 text-[11px] text-red-400 font-bold">
                                <AlertTriangle className="w-3 h-3" /> Failed
                              </span>
                            ) : (
                              <span className="text-[11px] text-slate-500">Queued</span>
                            )
                          ) : (
                            <button
                              type="button"
                              disabled={isUploading}
                              onClick={() => removeFile(idx)}
                              className="text-slate-500 hover:text-red-400 transition-colors p-1"
                              title="Remove file"
                            >
                              <Trash2 className="w-3.5 h-3.5" />
                            </button>
                          )}
                        </div>
                      </div>
                      {statusInfo?.status === 'FAILED' && statusInfo.error && (
                        <div className="text-[10px] text-red-400/90 pl-6 flex items-center gap-1">
                          <span>Reason:</span>
                          <span className="font-mono break-all">{statusInfo.error}</span>
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>

              <div className="flex items-center gap-2 text-xs text-slate-300">
                <input
                  type="checkbox"
                  id="run-ml"
                  checked={runMlAfter}
                  onChange={(e) => setRunMlAfter(e.target.checked)}
                  disabled={isUploading}
                  className="rounded bg-slate-900 border-slate-700 text-cyber-emerald focus:ring-0"
                />
                <label htmlFor="run-ml">Automatically run Isolation Forest ML & Clustering after ingestion</label>
              </div>

              <button
                onClick={handleUploadAll}
                disabled={isUploading || selectedFiles.length === 0}
                className="flex items-center justify-center gap-2 w-full py-2.5 rounded-lg bg-cyber-emerald text-slate-950 font-bold text-xs hover:bg-emerald-400 transition-all shadow-glow-emerald disabled:opacity-50"
              >
                {isUploading ? (
                  <>
                    <RefreshCw className="w-4 h-4 animate-spin" />
                    <span>Processing & Streaming Files Independently...</span>
                  </>
                ) : (
                  <>
                    <Upload className="w-4 h-4" />
                    <span>Start Multi-File Ingestion Pipeline ({selectedFiles.length} {selectedFiles.length === 1 ? 'file' : 'files'})</span>
                  </>
                )}
              </button>
            </div>
          )}

          {uploadError && (
            <div className="text-xs text-red-400 bg-red-500/10 px-3 py-2 rounded border border-red-500/20 flex items-center gap-2 max-w-xl">
              <AlertTriangle className="w-4 h-4 shrink-0" />
              <span>{uploadError}</span>
            </div>
          )}
        </div>
      </div>
      )}

      {/* Main Grid: Dataset List & Data Quality Report */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Datasets Table */}
        <div className="cyber-card p-5 lg:col-span-2 space-y-4">
          <div className="flex items-center justify-between border-b border-cyber-border pb-3">
            <h2 className="text-sm font-semibold text-slate-100 uppercase tracking-wider">
              Ingested Datasets ({datasetsData?.total || 0})
            </h2>
            <button
              onClick={() => refetchDatasets()}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-xs font-medium text-slate-300 border border-slate-700 transition-colors"
              title="Refresh dataset list"
            >
              <RefreshCw className="w-3 h-3" />
              Refresh
            </button>
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
                        <span className="truncate max-w-[170px]" title={ds.filename}>{ds.filename}</span>
                      </td>
                      <td className="py-3 uppercase text-slate-400">{ds.format}</td>
                      <td className="py-3">
                        {ds.status === 'PROCESSING' ? (
                          <div className="flex flex-col gap-1 w-44">
                            <div className="flex justify-between text-[10px]">
                              <span className="text-cyber-emerald font-bold">
                                {ds.processed_records.toLocaleString()} valid
                              </span>
                              <span className="text-slate-400 font-mono">
                                {ds.total_records > 0
                                  ? `${Math.round((ds.processed_records / ds.total_records) * 100)}%`
                                  : 'streaming...'}
                              </span>
                            </div>
                            <div className="w-full bg-slate-800 rounded-full h-1.5 overflow-hidden">
                              <div
                                className="bg-cyber-emerald h-1.5 rounded-full transition-all duration-300"
                                style={{
                                  width: `${ds.total_records > 0 ? Math.min(100, Math.round((ds.processed_records / ds.total_records) * 100)) : 20}%`
                                }}
                              />
                            </div>
                            <span className="text-[9px] text-slate-500 font-mono">
                              of {ds.total_records.toLocaleString()} rows evaluated
                            </span>
                          </div>
                        ) : (
                          <div className="flex flex-col">
                            <div className="flex items-center gap-1">
                              <span className="text-cyber-emerald font-bold">{ds.processed_records.toLocaleString()}</span>
                              <span className="text-slate-400 text-[11px]">valid</span>
                            </div>
                            <span className="text-[10px] text-slate-500 font-mono">
                              {ds.total_records.toLocaleString()} rows total
                            </span>
                          </div>
                        )}
                      </td>
                      <td className="py-3">
                        <div className="flex flex-col gap-0.5">
                          {ds.status === 'PROCESSING' ? (
                            <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-bold bg-cyan-500/10 text-cyber-cyan border border-cyber-cyan/30 animate-pulse w-fit">
                              <RefreshCw className="w-3 h-3 animate-spin" /> INGESTING
                            </span>
                          ) : (
                            <Badge variant={ds.status === 'COMPLETED' ? 'success' : ds.status === 'FAILED' ? 'critical' : 'info'}>
                              {ds.status}
                            </Badge>
                          )}
                          {ds.status === 'FAILED' && ds.error_summary && (
                            <span className="text-[10px] text-red-400 max-w-[150px] truncate" title={ds.error_summary}>
                              {ds.error_summary}
                            </span>
                          )}
                        </div>
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
            {selectedDataset && (
              <span className="text-[10px] text-slate-400 font-mono truncate max-w-[160px]">
                {selectedDataset.filename}
              </span>
            )}
          </div>

          {selectedDataset ? (
            <div className="space-y-4 text-xs">
              {/* If Ingestion Failed, show prominent error reason banner */}
              {selectedDataset.status === 'FAILED' && selectedDataset.error_summary && (
                <div className="p-3 rounded-lg bg-red-500/10 border border-red-500/30 text-xs space-y-1">
                  <div className="flex items-center gap-1.5 font-bold text-red-400 uppercase text-[10px]">
                    <AlertTriangle className="w-3.5 h-3.5 shrink-0" />
                    <span>Ingestion Failure Reason</span>
                  </div>
                  <p className="text-[11px] text-red-300 font-mono break-words leading-relaxed">
                    {selectedDataset.error_summary}
                  </p>
                </div>
              )}

              {/* Data Quality Metric Cards */}
              <div className="p-3 rounded-lg bg-slate-900/80 border border-slate-800 space-y-2">
                <div className="flex justify-between">
                  <span className="text-slate-400">Total Rows Evaluated:</span>
                  <span className="font-bold text-slate-100">
                    {selectedDataset.data_quality_metrics?.total_records ?? selectedDataset.total_records}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-400">Valid Ingested Records:</span>
                  <span className="font-bold text-cyber-emerald">
                    {selectedDataset.data_quality_metrics?.valid_records ?? selectedDataset.processed_records}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-400">Rejected / Malformed:</span>
                  <span className="font-bold text-red-400">
                    {selectedDataset.data_quality_metrics?.rejected_records ?? selectedDataset.rejected_records}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-400">Duplicates Detected:</span>
                  <span className="font-bold text-amber-400">
                    {selectedDataset.data_quality_metrics?.duplicate_records ?? 0}
                  </span>
                </div>
              </div>

              {/* Entity Breakdown if metrics present */}
              {selectedDataset.data_quality_metrics && (
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
              )}

              {/* Rejection Reasons if any */}
              {selectedDataset.data_quality_metrics?.rejected_reasons &&
                Object.keys(selectedDataset.data_quality_metrics.rejected_reasons).length > 0 && (
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
