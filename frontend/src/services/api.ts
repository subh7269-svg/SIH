import {
  Dataset,
  Alert,
  EntitySearchResult,
  EntityDossier,
  GraphData,
  MLModelArtifact,
  EntityCluster,
  InvestigationReport,
  User,
} from '../types';

const BASE_URL = '/api/v1';

async function handleResponse<T>(res: Response): Promise<T> {
  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    const message = errorData?.error?.message || errorData?.detail || `API error: ${res.status} ${res.statusText}`;
    throw new Error(message);
  }
  return res.json();
}

// -------------------------------------------------------------
// Datasets
// -------------------------------------------------------------
export async function getDatasets(): Promise<{ total: number; datasets: Dataset[] }> {
  const res = await fetch(`${BASE_URL}/datasets`);
  return handleResponse(res);
}

export async function getDataset(id: string): Promise<Dataset> {
  const res = await fetch(`${BASE_URL}/datasets/${id}`);
  return handleResponse(res);
}

export async function uploadDataset(file: File, runMl: boolean = true): Promise<Dataset> {
  const formData = new FormData();
  formData.append('file', file);
  formData.append('run_ml', String(runMl));

  const res = await fetch(`${BASE_URL}/datasets`, {
    method: 'POST',
    body: formData,
  });
  return handleResponse(res);
}

export async function deleteDataset(id: string): Promise<{ status: string }> {
  const res = await fetch(`${BASE_URL}/datasets/${id}`, {
    method: 'DELETE',
  });
  return handleResponse(res);
}

// -------------------------------------------------------------
// Alerts
// -------------------------------------------------------------
export async function getAlerts(params?: {
  severity?: string;
  status?: string;
  min_score?: number;
  dataset_id?: string;
  limit?: number;
}): Promise<{
  total: number;
  critical_count: number;
  high_count: number;
  medium_count: number;
  low_count: number;
  alerts: Alert[];
}> {
  const query = new URLSearchParams();
  if (params?.severity) query.set('severity', params.severity);
  if (params?.status) query.set('status', params.status);
  if (params?.min_score !== undefined) query.set('min_score', String(params.min_score));
  if (params?.dataset_id) query.set('dataset_id', params.dataset_id);
  if (params?.limit) query.set('limit', String(params.limit));

  const res = await fetch(`${BASE_URL}/alerts?${query.toString()}`);
  return handleResponse(res);
}

export async function getAlert(id: string): Promise<Alert> {
  const res = await fetch(`${BASE_URL}/alerts/${id}`);
  return handleResponse(res);
}

export async function updateAlertStatus(
  id: string,
  status: string,
  note?: string,
  assigned_to?: string
): Promise<Alert> {
  const res = await fetch(`${BASE_URL}/alerts/${id}/status`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ status, note, assigned_to }),
  });
  return handleResponse(res);
}

// -------------------------------------------------------------
// Entities & Search
// -------------------------------------------------------------
export async function searchEntities(q: string): Promise<{ query: string; total_results: number; results: EntitySearchResult[] }> {
  const res = await fetch(`${BASE_URL}/entities/search?q=${encodeURIComponent(q)}`);
  return handleResponse(res);
}

export async function getEntityDossier(entityId: string): Promise<EntityDossier> {
  const res = await fetch(`${BASE_URL}/entities/${encodeURIComponent(entityId)}`);
  return handleResponse(res);
}

// -------------------------------------------------------------
// Graph Explorer
// -------------------------------------------------------------
export async function getGraphOverview(limit: number = 60): Promise<GraphData> {
  const res = await fetch(`${BASE_URL}/graph/overview?limit=${limit}`);
  return handleResponse(res);
}

export async function getEntityGraph(entityId: string, k: number = 2): Promise<GraphData> {
  const res = await fetch(`${BASE_URL}/graph/entity/${encodeURIComponent(entityId)}?k=${k}`);
  return handleResponse(res);
}

export async function getPathGraph(sourceId: string, targetId: string): Promise<GraphData> {
  const res = await fetch(`${BASE_URL}/graph/path`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ source_id: sourceId, target_id: targetId }),
  });
  return handleResponse(res);
}

// -------------------------------------------------------------
// ML & Models
// -------------------------------------------------------------
export async function getModels(): Promise<MLModelArtifact[]> {
  const res = await fetch(`${BASE_URL}/models`);
  return handleResponse(res);
}

export async function trainModel(params: {
  dataset_id?: string;
  model_type: string;
  contamination: number;
}): Promise<any> {
  const res = await fetch(`${BASE_URL}/models/train`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(params),
  });
  return handleResponse(res);
}

// -------------------------------------------------------------
// Clusters
// -------------------------------------------------------------
export async function getClusters(datasetId?: string): Promise<{
  total_clusters: number;
  noise_count: number;
  clusters: EntityCluster[];
}> {
  const query = datasetId ? `?dataset_id=${datasetId}` : '';
  const res = await fetch(`${BASE_URL}/clusters${query}`);
  return handleResponse(res);
}

// -------------------------------------------------------------
// Reports
// -------------------------------------------------------------
export async function generateReport(params: {
  title: string;
  entity_id: string;
  include_evidence?: boolean;
  analyst_notes?: string;
}): Promise<InvestigationReport> {
  const res = await fetch(`${BASE_URL}/reports/generate`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(params),
  });
  return handleResponse(res);
}

// -------------------------------------------------------------
// Demo Mode
// -------------------------------------------------------------
export async function runDemo(seed: number = 42): Promise<any> {
  const res = await fetch(`${BASE_URL}/demo/run?seed=${seed}`, {
    method: 'POST',
  });
  return handleResponse(res);
}

export async function resetDemo(): Promise<any> {
  const res = await fetch(`${BASE_URL}/demo/reset`, {
    method: 'POST',
  });
  return handleResponse(res);
}

// -------------------------------------------------------------
// Audit Logs
// -------------------------------------------------------------
export async function getAuditLogs(limit: number = 40): Promise<any[]> {
  const res = await fetch(`${BASE_URL}/investigations/audit-logs?limit=${limit}`);
  return handleResponse(res);
}
