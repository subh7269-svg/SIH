"""
REST API Router for LeadForge Transaction-Wallet-Network Correlation Engine.
Endpoints for async job execution, status monitoring, transaction inspection,
investigation lead prioritization, and heterogeneous graph exploration.
"""
from typing import Optional, List, Dict, Any
from pathlib import Path
import json
import pandas as pd
from fastapi import APIRouter, HTTPException, Query, BackgroundTasks, status
from pydantic import BaseModel, Field

from backend.app.correlation.config import correlation_settings
from backend.app.correlation.job_manager import job_manager
from backend.app.correlation.engine import CorrelationEngine, run_correlation_background
from backend.app.correlation.validator import validate_dataset

router = APIRouter(tags=["Correlation Engine"])

class CorrelationRunRequest(BaseModel):
    chunk_size: Optional[int] = Field(default=50000, description="Streaming chunk size")
    time_window_seconds: Optional[float] = Field(default=120.0, description="Temporal correlation window in seconds")
    max_transactions: Optional[int] = Field(default=10000, description="Maximum transactions to process (None for all)")
    dataset_dir: Optional[str] = Field(default=None, description="Custom dataset directory override")

class CorrelationRunResponse(BaseModel):
    job_id: str
    status: str
    message: str

def _load_correlations_df() -> Optional[pd.DataFrame]:
    path = correlation_settings.OUTPUT_DIR / "transaction_correlations.csv"
    if path.exists():
        return pd.read_csv(path, low_memory=False)
    return None

def _load_leads_df() -> Optional[pd.DataFrame]:
    path = correlation_settings.OUTPUT_DIR / "investigation_leads.csv"
    if path.exists():
        return pd.read_csv(path, low_memory=False)
    return None

# 1. POST /api/correlation/run
@router.post("/correlation/run", response_model=CorrelationRunResponse, status_code=status.HTTP_202_ACCEPTED)
def run_correlation(request: CorrelationRunRequest, background_tasks: BackgroundTasks):
    """
    Triggers asynchronous correlation pipeline in background.
    Returns immediately with a job identifier.
    """
    job_id = job_manager.create_job(params=request.model_dump())
    custom_dir = Path(request.dataset_dir) if request.dataset_dir else None

    # Spawn background worker daemon
    run_correlation_background(
        job_id=job_id,
        chunk_size=request.chunk_size or correlation_settings.CHUNK_SIZE,
        max_transactions=request.max_transactions,
        time_window_seconds=request.time_window_seconds or correlation_settings.CORRELATION_TIME_WINDOW_SECONDS,
        dataset_dir=custom_dir
    )

    return CorrelationRunResponse(
        job_id=job_id,
        status="started",
        message="Correlation processing started in background thread."
    )

# 2. GET /api/correlation/status and /status/{job_id}
@router.get("/correlation/status")
@router.get("/correlation/status/{job_id}")
def get_correlation_status(job_id: Optional[str] = None):
    """Returns real-time progress, step transitions, and summary metrics."""
    job = job_manager.get_job(job_id)
    if not job:
        # Check if output files already exist on disk
        leads_df = _load_leads_df()
        if leads_df is not None:
            return {
                "status": "ready",
                "message": "Previous correlation outputs available on disk.",
                "total_leads": len(leads_df)
            }
        return {"status": "idle", "message": "No correlation jobs have been executed yet."}
    return job

# 3. GET /api/correlation/validation-report
@router.get("/correlation/validation-report")
def get_validation_report():
    """Returns dataset schema validation report."""
    report_file = correlation_settings.OUTPUT_DIR / "dataset_validation_report.json"
    if report_file.exists():
        with open(report_file, "r", encoding="utf-8") as f:
            return json.load(f)
    return validate_dataset()

# 4. GET /api/transactions/{txid}
@router.get("/transactions/{txid}")
def get_transaction(txid: str):
    """Returns complete transaction information."""
    df = _load_correlations_df()
    if df is None:
        raise HTTPException(status_code=404, detail="No correlation records generated yet. Run correlation first.")

    matches = df[df["txid"].astype(str) == str(txid)]
    if matches.empty:
        raise HTTPException(status_code=404, detail=f"Transaction {txid} not found in correlation database.")

    row = matches.iloc[0].to_dict()
    # Clean NaN values
    clean_row = {k: (None if pd.isna(v) else v) for k, v in row.items()}
    return clean_row

# 5. GET /api/transactions/{txid}/correlations
@router.get("/transactions/{txid}/correlations")
def get_transaction_correlations(txid: str):
    """Returns wallet correlations, network observations, and related transactions."""
    df = _load_correlations_df()
    if df is None:
        raise HTTPException(status_code=404, detail="No correlation records generated yet.")

    matches = df[df["txid"].astype(str) == str(txid)]
    if matches.empty:
        raise HTTPException(status_code=404, detail=f"Transaction {txid} not found.")

    row = matches.iloc[0]

    input_wallets = [w for w in str(row.get("input_wallets", "")).split(";") if w and w != "nan"]
    output_wallets = [w for w in str(row.get("output_wallets", "")).split(";") if w and w != "nan"]
    related_wallets = [w for w in str(row.get("related_wallets", "")).split(";") if w and w != "nan"]

    return {
        "txid": txid,
        "wallet_correlations": {
            "input_wallets": input_wallets,
            "output_wallets": output_wallets,
            "related_wallets": related_wallets,
            "wallet_classes": row.get("wallet_classes"),
            "total_wallets": len(related_wallets)
        },
        "network_correlations": {
            "network_timestamp": None if pd.isna(row.get("network_timestamp")) else row.get("network_timestamp"),
            "time_difference_seconds": None if pd.isna(row.get("time_difference_seconds")) else float(row.get("time_difference_seconds")),
            "src_ip": None if pd.isna(row.get("src_ip")) else str(row.get("src_ip")),
            "src_port": None if pd.isna(row.get("src_port")) else int(row.get("src_port")),
            "dst_ip": None if pd.isna(row.get("dst_ip")) else str(row.get("dst_ip")),
            "dst_port": None if pd.isna(row.get("dst_port")) else int(row.get("dst_port")),
            "network_txid": None if pd.isna(row.get("network_txid")) else str(row.get("network_txid")),
            "correlation_method": row.get("correlation_method", "none"),
            "network_confidence": float(row.get("network_confidence", 0.0)),
            "forensic_statement": "network observation temporally correlated with transaction"
        }
    }

# 6. GET /api/investigations
@router.get("/investigations")
def get_investigation_leads(
    priority: Optional[str] = Query(None, description="Filter by priority: HIGH, MEDIUM, LOW"),
    minimum_score: Optional[float] = Query(None, description="Minimum risk score (0 - 100)"),
    transaction_class: Optional[str] = Query(None, description="Filter by class: illicit, licit, unknown"),
    date: Optional[str] = Query(None, description="Date filter"),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0)
):
    """Returns ranked investigation leads with configurable forensic filters."""
    df = _load_leads_df()
    if df is None or df.empty:
        return {"total": 0, "leads": [], "message": "No investigation leads available. Run correlation first."}

    # Filters
    if priority and priority.upper() != "ALL":
        df = df[df["priority"].astype(str).str.upper() == priority.upper()]

    if minimum_score is not None:
        df = df[df["risk_score"] >= minimum_score]

    if transaction_class:
        df = df[df["tx_class"].astype(str).str.lower() == transaction_class.lower()]

    if date:
        df = df[df["timestamp"].astype(str).str.contains(date)]

    total = len(df)
    page_df = df.iloc[offset : offset + limit]

    leads = []
    for _, r in page_df.iterrows():
        lead_dict = r.to_dict()
        clean_lead = {k: (None if pd.isna(v) else v) for k, v in lead_dict.items()}
        leads.append(clean_lead)

    return {
        "total": total,
        "limit": limit,
        "offset": offset,
        "leads": leads
    }

# 7. GET /api/investigations/{txid}
@router.get("/investigations/{txid}")
def get_investigation_lead_detail(txid: str):
    """Returns full investigation lead forensic dossier."""
    leads_df = _load_leads_df()
    corr_df = _load_correlations_df()

    if leads_df is None or corr_df is None:
        raise HTTPException(status_code=404, detail="Correlation records not found.")

    lead_matches = leads_df[leads_df["txid"].astype(str) == str(txid)]
    corr_matches = corr_df[corr_df["txid"].astype(str) == str(txid)]

    if lead_matches.empty:
        raise HTTPException(status_code=404, detail=f"Investigation lead {txid} not found.")

    lead = {k: (None if pd.isna(v) else v) for k, v in lead_matches.iloc[0].to_dict().items()}
    corr = {k: (None if pd.isna(v) else v) for k, v in corr_matches.iloc[0].to_dict().items()} if not corr_matches.empty else {}

    evidence_list = str(lead.get("evidence", "")).split(" | ") if lead.get("evidence") else []

    return {
        "txid": txid,
        "risk_score": lead.get("risk_score"),
        "priority": lead.get("priority"),
        "evidence": evidence_list,
        "transaction_information": {
            "timestamp": lead.get("timestamp"),
            "amount": lead.get("amount"),
            "fee": lead.get("fee"),
            "tx_class": lead.get("tx_class"),
            "fan_in": lead.get("fan_in"),
            "fan_out": lead.get("fan_out"),
            "script_type": corr.get("script_type", "P2PKH")
        },
        "wallet_information": {
            "input_wallets": [w for w in str(corr.get("input_wallets", "")).split(";") if w and w != "None"],
            "output_wallets": [w for w in str(corr.get("output_wallets", "")).split(";") if w and w != "None"],
            "related_wallets": [w for w in str(corr.get("related_wallets", "")).split(";") if w and w != "None"],
            "wallet_classes": corr.get("wallet_classes", "{}")
        },
        "network_correlation": {
            "src_ip": corr.get("src_ip"),
            "src_port": corr.get("src_port"),
            "dst_ip": corr.get("dst_ip"),
            "dst_port": corr.get("dst_port"),
            "time_difference_seconds": corr.get("time_difference_seconds"),
            "correlation_method": corr.get("correlation_method"),
            "network_confidence": corr.get("network_confidence")
        },
        "ml_anomaly_information": {
            "ml_anomaly_score": lead.get("ml_anomaly_score"),
            "ml_anomaly_label": lead.get("ml_anomaly_label"),
            "model": "IsolationForest"
        }
    }

# 8. GET /api/graph/{txid}
@router.get("/graph/{txid}")
def get_transaction_subgraph(txid: str, hops: int = Query(1, ge=1, le=3)):
    """Returns multi-hop Cytoscape.js subgraph around transaction."""
    graph_file = correlation_settings.OUTPUT_DIR / "graph_edges.csv"
    corr_df = _load_correlations_df()

    from backend.app.correlation.graph_service import GraphService
    gs = GraphService()

    if graph_file.exists():
        df_edges = pd.read_csv(graph_file)
        # Populate graph from edges
        for _, r in df_edges.iterrows():
            s = str(r["source"])
            t = str(r["target"])
            s_type = str(r["source_type"])
            t_type = str(r["target_type"])
            rel = str(r["relationship"])
            gs.graph.add_node(s, node_type=s_type, label=f"{s[:10]}...")
            gs.graph.add_node(t, node_type=t_type, label=f"{t[:10]}...")
            gs.graph.add_edge(s, t, relationship=rel)
    elif corr_df is not None:
        matches = corr_df[corr_df["txid"].astype(str) == str(txid)]
        if not matches.empty:
            r = matches.iloc[0]
            in_w = [w for w in str(r.get("input_wallets", "")).split(";") if w and w != "None"]
            out_w = [w for w in str(r.get("output_wallets", "")).split(";") if w and w != "None"]
            gs.add_transaction_edges(txid, in_w, out_w, str(r.get("src_ip")))

    return gs.get_subgraph_cytoscape(str(txid), hops=hops)
