"""
Master Correlation Engine Orchestrator.
Coordinates the end-to-end multi-layer forensic correlation pipeline:
1. Transaction Ingestion (chunked stream)
2. Class Correlation (txs_classes.csv)
3. Wallet Correlation (AddrTx/TxAddr edgelists & wallet classes)
4. Network Correlation (exact TXID & temporal proximity window)
5. Correlation Record Export (transaction_correlations.csv)
6. Investigation Lead Scoring (explainable 0-100 score + reasons)
7. Heterogeneous Graph Generation (graph_edges.csv)
8. Isolation Forest Anomaly Detection (ml_anomaly_score, ml_anomaly_label)
"""
import os
import logging
from pathlib import Path
from typing import Dict, Any, Optional, List
import pandas as pd
import threading

from backend.app.correlation.config import correlation_settings
from backend.app.correlation.validator import validate_dataset, find_dataset_file
from backend.app.correlation.transaction_ingestion import stream_transactions
from backend.app.correlation.wallet_correlator import WalletCorrelator
from backend.app.correlation.network_correlator import NetworkCorrelator
from backend.app.correlation.feature_service import extract_features
from backend.app.correlation.risk_service import RiskService
from backend.app.correlation.graph_service import GraphService
from backend.app.correlation.job_manager import job_manager
from backend.app.ml.train import train_isolation_forest
from backend.app.ml.predict import predict_anomalies
from backend.app.ml.model_loader import get_model_paths

logger = logging.getLogger("tracex.correlation.engine")

class CorrelationEngine:
    """Master orchestrator for TraceX correlation pipeline."""
    def __init__(self, dataset_dir: Optional[Path] = None, output_dir: Optional[Path] = None):
        self.dataset_dir = dataset_dir
        self.output_dir = output_dir or correlation_settings.OUTPUT_DIR
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.risk_service = RiskService(correlation_settings)
        self.graph_service = GraphService()
        self.wallet_correlator = WalletCorrelator(self.dataset_dir)
        self.network_correlator = NetworkCorrelator(self.dataset_dir)

    def run(
        self,
        job_id: Optional[str] = None,
        chunk_size: int = correlation_settings.CHUNK_SIZE,
        max_transactions: Optional[int] = None,
        time_window_seconds: float = correlation_settings.CORRELATION_TIME_WINDOW_SECONDS
    ) -> Dict[str, Any]:
        """
        Executes the full correlation workflow synchronously or inside a background thread.
        """
        logger.info(f"Starting correlation pipeline (job_id={job_id}, max_txs={max_transactions}, chunk_size={chunk_size})...")

        try:
            # Pre-flight Validation
            if job_id:
                job_manager.update_progress(job_id, step="validating_dataset", progress_pct=5.0)
            validation_report = validate_dataset(self.dataset_dir)

            tx_file = find_dataset_file("txs_features.csv", self.dataset_dir)
            if not tx_file:
                err_msg = "txs_features.csv could not be found in any dataset path."
                if job_id:
                    job_manager.mark_failed(job_id, err_msg)
                raise FileNotFoundError(err_msg)

            # Step 2: Load Transaction Classes
            if job_id:
                job_manager.update_progress(job_id, step="loading_transaction_classes", progress_pct=10.0)
            self.wallet_correlator.load_transaction_classes()

            # Step 3: Load Wallet Classes & Edgelists
            if job_id:
                job_manager.update_progress(job_id, step="indexing_wallets_and_edgelists", progress_pct=20.0)
            self.wallet_correlator.load_wallet_classes()
            self.wallet_correlator.load_edgelists()

            # Step 4: Load & Index Network Observations
            if job_id:
                job_manager.update_progress(job_id, step="indexing_network_data", progress_pct=30.0)
            self.network_correlator.time_window_seconds = time_window_seconds
            net_obs_count = self.network_correlator.load_network_data()

            # Step 1 & 5 & 6: Stream transactions, correlate, score
            if job_id:
                job_manager.update_progress(job_id, step="streaming_and_correlating_transactions", progress_pct=40.0)

            all_correlations: List[Dict[str, Any]] = []
            all_leads: List[Dict[str, Any]] = []
            all_feature_records: List[Dict[str, Any]] = []

            total_txs_processed = 0
            correlated_count = 0
            high_priority_count = 0
            all_unique_wallets = set()

            tx_stream = stream_transactions(tx_file, chunk_size=chunk_size, max_transactions=max_transactions)

            for chunk_idx, chunk_df in enumerate(tx_stream):
                for _, row in chunk_df.iterrows():
                    txid = row["txid"]
                    ts = row["timestamp"]

                    # Correlate Wallet Layer
                    wallet_info = self.wallet_correlator.correlate_transaction(
                        txid=txid,
                        inline_inputs=row.get("input_addresses"),
                        inline_outputs=row.get("output_addresses")
                    )

                    # Correlate Network Layer
                    net_info = self.network_correlator.correlate(txid=txid, tx_timestamp=ts)
                    if net_info["correlation_method"] != "none":
                        correlated_count += 1

                    # Extract Behavioral & Topological Features
                    features = extract_features(row.to_dict(), wallet_info, net_info)

                    # Calculate Explainable Investigation Lead Score
                    lead = self.risk_service.calculate_investigation_lead(
                        txid=txid,
                        features=features,
                        tx_class=wallet_info["tx_class"],
                        network_info=net_info
                    )
                    if lead["priority"] == "HIGH":
                        high_priority_count += 1

                    # Add Graph Edges
                    self.graph_service.add_transaction_edges(
                        txid=txid,
                        input_wallets=wallet_info["input_wallets"],
                        output_wallets=wallet_info["output_wallets"],
                        src_ip=net_info.get("src_ip")
                    )

                    for w in wallet_info["related_wallets"]:
                        all_unique_wallets.add(w)

                    # Assemble Complete Correlation Record
                    corr_record = {
                        "txid": txid,
                        "timestamp": ts,
                        "tx_class": wallet_info["tx_class"],
                        "fee": row["fee"],
                        "script_type": row["script_type"],
                        "input_count": row["input_count"],
                        "output_count": row["output_count"],
                        "fan_in": row["fan_in"],
                        "fan_out": row["fan_out"],
                        "total_input_amount": row["total_input_amount"],
                        "amount_per_output": row["amount_per_output"],
                        "input_wallets": ";".join(wallet_info["input_wallets"]),
                        "output_wallets": ";".join(wallet_info["output_wallets"]),
                        "related_wallets": ";".join(wallet_info["related_wallets"]),
                        "wallet_classes": str(wallet_info["wallet_classes"]),
                        "network_timestamp": net_info.get("network_timestamp"),
                        "time_difference_seconds": net_info.get("time_difference_seconds"),
                        "src_ip": net_info.get("src_ip"),
                        "src_port": net_info.get("src_port"),
                        "dst_ip": net_info.get("dst_ip"),
                        "dst_port": net_info.get("dst_port"),
                        "network_txid": net_info.get("network_txid"),
                        "correlation_method": net_info.get("correlation_method"),
                        "network_confidence": net_info.get("network_confidence")
                    }
                    all_correlations.append(corr_record)

                    lead_record = {
                        "txid": txid,
                        "timestamp": ts,
                        "amount": row["total_input_amount"],
                        "fee": row["fee"],
                        "tx_class": wallet_info["tx_class"],
                        "fan_in": row["fan_in"],
                        "fan_out": row["fan_out"],
                        "wallet_count": len(wallet_info["related_wallets"]),
                        "network_confidence": net_info.get("network_confidence", 0.0),
                        "risk_score": lead["risk_score"],
                        "priority": lead["priority"],
                        "evidence": lead["evidence_text"]
                    }
                    all_leads.append(lead_record)

                    feat_dict = {**features, "txid": txid}
                    all_feature_records.append(feat_dict)

                    total_txs_processed += 1

                # Update live job progress
                if job_id:
                    prog = min(80.0, 40.0 + (total_txs_processed / (max_transactions or 100000)) * 40.0)
                    job_manager.update_progress(
                        job_id,
                        step="streaming_and_correlating_transactions",
                        progress_pct=prog,
                        processed=total_txs_processed,
                        metrics={
                            "transactions_processed": total_txs_processed,
                            "wallets_connected": len(all_unique_wallets),
                            "correlated_transactions": correlated_count,
                            "investigation_leads": total_txs_processed,
                            "high_priority_leads": high_priority_count
                        }
                    )

            # Step 8: ML Anomaly Detection (Isolation Forest)
            if job_id:
                job_manager.update_progress(job_id, step="running_ml_anomaly_detection", progress_pct=85.0)

            # Check if model exists, otherwise train on sample
            model_path, _ = get_model_paths(correlation_settings.MODELS_DIR)
            if not model_path.exists() and len(all_feature_records) >= 10:
                logger.info("No pre-trained Isolation Forest detected. Training model on feature sample...")
                train_isolation_forest(
                    all_feature_records,
                    models_dir=correlation_settings.MODELS_DIR,
                    max_samples=min(10000, len(all_feature_records))
                )

            # Predict anomaly scores
            ml_results = predict_anomalies(all_feature_records, models_dir=correlation_settings.MODELS_DIR)
            for i, res in enumerate(ml_results):
                all_leads[i]["ml_anomaly_score"] = res["ml_anomaly_score"]
                all_leads[i]["ml_anomaly_label"] = res["ml_anomaly_label"]
                all_correlations[i]["ml_anomaly_score"] = res["ml_anomaly_score"]

            # Step 5 & 7: Write Output Files
            if job_id:
                job_manager.update_progress(job_id, step="exporting_output_files", progress_pct=95.0)

            # 1. transaction_correlations.csv
            df_corr = pd.DataFrame(all_correlations)
            corr_file = self.output_dir / "transaction_correlations.csv"
            df_corr.to_csv(corr_file, index=False)

            # 2. investigation_leads.csv (sorted by risk_score desc)
            df_leads = pd.DataFrame(all_leads)
            if not df_leads.empty:
                df_leads.sort_values(by="risk_score", ascending=False, inplace=True)
            leads_file = self.output_dir / "investigation_leads.csv"
            df_leads.to_csv(leads_file, index=False)

            # 3. graph_edges.csv
            graph_file = self.output_dir / "graph_edges.csv"
            self.graph_service.export_edges_csv(graph_file)

            final_metrics = {
                "transactions_processed": total_txs_processed,
                "wallets_connected": len(all_unique_wallets),
                "network_observations": net_obs_count,
                "correlated_transactions": correlated_count,
                "investigation_leads": len(df_leads),
                "high_priority_leads": high_priority_count
            }

            if job_id:
                job_manager.mark_completed(job_id, metrics=final_metrics)

            logger.info(f"Correlation pipeline finished successfully! Processed {total_txs_processed} transactions.")
            return {
                "status": "success",
                "job_id": job_id,
                "metrics": final_metrics,
                "outputs": {
                    "transaction_correlations": str(corr_file),
                    "investigation_leads": str(leads_file),
                    "graph_edges": str(graph_file),
                    "validation_report": str(self.output_dir / "dataset_validation_report.json")
                }
            }

        except Exception as e:
            logger.error(f"Correlation pipeline failed: {str(e)}", exc_info=True)
            if job_id:
                job_manager.mark_failed(job_id, str(e))
            raise

def run_correlation_background(
    job_id: str,
    chunk_size: int,
    max_transactions: Optional[int],
    time_window_seconds: float,
    dataset_dir: Optional[Path] = None
):
    """Entry point for executing correlation in a detached background daemon thread."""
    def _worker():
        engine = CorrelationEngine(dataset_dir=dataset_dir)
        engine.run(
            job_id=job_id,
            chunk_size=chunk_size,
            max_transactions=max_transactions,
            time_window_seconds=time_window_seconds
        )

    thread = threading.Thread(target=_worker, daemon=True)
    thread.start()
    return thread
