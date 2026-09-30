export interface DataQualityMetrics {
  total_records: number;
  valid_records: number;
  rejected_records: number;
  duplicate_records: number;
  missing_fields_count: number;
  unique_wallets: number;
  unique_txids: number;
  unique_src_ips: number;
  unique_countries: number;
  unique_asns: number;
  time_min?: string;
  time_max?: string;
  total_btc_volume: number;
  avg_fee: number;
  field_completeness: Record<string, number>;
  rejected_reasons: Record<string, number>;
}

export interface Dataset {
  id: string;
  filename: string;
  format: 'csv' | 'json' | 'xml';
  size_bytes: number;
  status: 'PENDING' | 'PROCESSING' | 'COMPLETED' | 'FAILED';
  total_records: number;
  processed_records: number;
  rejected_records: number;
  data_quality_metrics?: DataQualityMetrics;
  error_summary?: string;
  uploaded_at: string;
  completed_at?: string;
}

export interface GraphNode {
  id: string;
  label: string;
  type: 'WALLET' | 'TRANSACTION' | 'IP' | 'ASN' | 'COUNTRY';
  risk_score: number;
  anomaly_score: number;
  is_focal?: boolean;
  properties?: Record<string, any>;
}

export interface GraphEdge {
  id: string;
  source: string;
  target: string;
  type: 'INPUT_OF' | 'OUTPUT_TO' | 'OBSERVED_IN' | 'BELONGS_TO_ASN' | 'LOCATED_IN' | 'TRANSFERS_TO';
  label?: string;
  amount?: number;
  timestamp?: string;
  properties?: Record<string, any>;
}

export interface GraphData {
  nodes: GraphNode[];
  edges: GraphEdge[];
  node_count: number;
  edge_count: number;
  focal_node_id?: string;
  metadata?: Record<string, any>;
}

export interface Alert {
  id: string;
  dataset_id?: string;
  entity_id: string;
  entity_type: 'WALLET' | 'IP' | 'TRANSACTION';
  anomaly_score: number;
  raw_anomaly_score?: number;
  validation_score?: number;
  priority_score: number;
  severity: 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL';
  confidence: number;
  status: 'NEW' | 'REVIEWING' | 'DISMISSED' | 'ESCALATED' | 'RESOLVED';
  reasons: string[];
  explanation_details: Record<string, any>;
  evidence_summary: {
    related_transactions?: string[];
    observed_ips?: string[];
    subscores?: {
      ml_score: number;
      velocity_score: number;
      counterparty_score: number;
      network_score: number;
      graph_score: number;
    };
    metrics?: Record<string, any>;
    contextual_validation?: Record<string, any>;
  };
  supporting_evidence?: Array<{
    feature: string;
    observed_value: any;
    baseline_value: any;
    deviation_type: string;
    reason: string;
  }>;
  counter_evidence?: Array<{
    feature: string;
    observed_value: any;
    baseline_value: any;
    counter_type: string;
    reason: string;
  }>;
  historical_context?: Record<string, any>;
  behavioural_deviation?: Record<string, any>;
  validation_explanation?: string;
  assigned_to?: string;
  notes?: Array<{
    timestamp: string;
    user: string;
    note: string;
    status_change?: string;
  }>;
  created_at: string;
  updated_at: string;
}

export interface ReplayStage {
  stage_id: string;
  stage_name: string;
  order: number;
  status: string;
  timestamp?: string;
  summary: string;
  data: Record<string, any>;
}

export interface InvestigationReplay {
  replay_id: string;
  alert_id: string;
  entity_id: string;
  entity_type: string;
  priority_score: number;
  severity: 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL';
  status: string;
  dataset_id?: string;
  created_at: string;
  stages: ReplayStage[];
  graph_data?: GraphData;
}

export interface EntitySearchResult {
  entity_id: string;
  entity_type: 'WALLET' | 'TRANSACTION' | 'IP' | 'ASN';
  label: string;
  subtext: string;
  risk_score: number;
  anomaly_score: number;
  metadata: Record<string, any>;
}

export interface EntityDossier {
  entity_id: string;
  entity_type: 'WALLET' | 'TRANSACTION' | 'IP' | 'ASN';
  risk_score: number;
  anomaly_score: number;
  raw_anomaly_score?: number;
  validation_score?: number;
  confidence?: number;
  severity: 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL';
  first_seen?: string;
  last_seen?: string;
  total_volume_btc: number;
  transaction_count: number;
  unique_counterparties: number;
  observed_ips: Array<{
    ip: string;
    country?: string;
    asn?: string;
    timestamp?: string;
  }>;
  observed_countries: string[];
  observed_asns: string[];
  features: Record<string, any>;
  explanation_reasons: string[];
  feature_deviations: Record<string, any>;
  supporting_evidence?: Array<{
    feature: string;
    observed_value: any;
    baseline_value: any;
    deviation_type: string;
    reason: string;
  }>;
  counter_evidence?: Array<{
    feature: string;
    observed_value: any;
    baseline_value: any;
    counter_type: string;
    reason: string;
  }>;
  historical_context?: Record<string, any>;
  behavioural_deviation?: Record<string, any>;
  validation_explanation?: string;
  recent_transactions: Array<{
    txid: string;
    timestamp?: string;
    input_total?: number;
    output_total?: number;
    fee?: number;
    script_type?: string;
  }>;
  related_alerts: Array<{
    id: string;
    severity: string;
    priority_score: number;
    raw_anomaly_score?: number;
    validation_score?: number;
    confidence?: number;
    status: string;
    created_at: string;
  }>;
  cluster_info?: {
    cluster_label: number;
    cluster_name: string;
    algorithm: string;
    member_count: number;
  };
}

export interface MLModelArtifact {
  id: string;
  model_name: string;
  model_type: string;
  version: string;
  is_active: number;
  feature_names: string[];
  evaluation_metrics: {
    precision: number;
    recall: number;
    f1_score: number;
    roc_auc: number;
    pr_auc: number;
    false_positive_rate: number;
    training_duration_ms: number;
    baseline_comparison?: {
      model: string;
      precision: number;
      recall: number;
      f1_score: number;
      roc_auc: number;
      pr_auc: number;
    };
    benchmark_disclaimer: string;
  };
  training_duration_ms: number;
  dataset_records_count: number;
  trained_at: string;
}

export interface EntityCluster {
  id: string;
  dataset_id?: string;
  cluster_label: number;
  cluster_name: string;
  algorithm: string;
  member_count: number;
  member_ids: string[];
  characteristics: Record<string, any>;
  created_at: string;
}

export interface InvestigationReport {
  report_id: string;
  generated_at: string;
  title: string;
  entity_id: string;
  entity_type: string;
  risk_score: number;
  anomaly_score: number;
  severity: string;
  disclaimer: string;
  explanation: string[];
  feature_breakdown: Record<string, any>;
  transaction_evidence: any[];
  network_observations: any[];
  analyst_notes?: string;
  markdown_content: string;
}

export interface User {
  id: string;
  username: string;
  email: string;
  role: 'INVESTIGATOR' | 'ADMIN';
  full_name: string;
  badge_number: string;
}

// -------------------------------------------------------------
// Correlation Engine Types
// -------------------------------------------------------------
export interface CorrelationMetrics {
  transactions_processed: number;
  wallets_connected: number;
  network_observations: number;
  correlated_transactions: number;
  investigation_leads: number;
  high_priority_leads: number;
}

export interface CorrelationStatus {
  job_id?: string;
  status: string;
  step?: string;
  progress_pct?: number;
  processed_transactions?: number;
  total_transactions?: number;
  started_at?: string;
  completed_at?: string;
  metrics?: CorrelationMetrics;
  total_leads?: number;
  error?: string;
}

export interface InvestigationLeadItem {
  txid: string;
  timestamp: string | number;
  amount: number;
  fee: number;
  tx_class: string;
  fan_in: number;
  fan_out: number;
  wallet_count: number;
  network_confidence: number;
  risk_score: number;
  priority: 'HIGH' | 'MEDIUM' | 'LOW';
  evidence: string;
  ml_anomaly_score?: number;
  ml_anomaly_label?: number;
}

export interface InvestigationLeadDetail {
  txid: string;
  risk_score: number;
  priority: 'HIGH' | 'MEDIUM' | 'LOW';
  evidence: string[];
  transaction_information: {
    timestamp: string | number;
    amount: number;
    fee: number;
    tx_class: string;
    fan_in: number;
    fan_out: number;
    script_type: string;
  };
  wallet_information: {
    input_wallets: string[];
    output_wallets: string[];
    related_wallets: string[];
    wallet_classes: string;
  };
  network_correlation: {
    src_ip?: string;
    src_port?: number;
    dst_ip?: string;
    dst_port?: number;
    time_difference_seconds?: number;
    correlation_method?: string;
    network_confidence?: number;
  };
  ml_anomaly_information: {
    ml_anomaly_score?: number;
    ml_anomaly_label?: number;
    model: string;
  };
}
