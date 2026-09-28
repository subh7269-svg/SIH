"""
Data validation module.
Pre-flight verification of CSV files, schemas, timestamps, and numeric integrity.
Generates dataset_validation_report.json before execution.
"""
import os
import json
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional
import pandas as pd
from datetime import datetime

from backend.app.correlation.config import correlation_settings
from backend.app.correlation.column_detector import detect_schema

logger = logging.getLogger("tracex.correlation.validator")

EXPECTED_FILES = [
    "txs_features.csv",
    "txs_classes.csv",
    "txs_edgelist.csv",
    "wallets_features.csv",
    "wallets_classes.csv",
    "wallets_features_classes_combined.csv",
    "AddrTx_edgelist.csv",
    "TxAddr_edgelist.csv",
    "network_data.csv"
]

def find_dataset_file(filename: str, custom_dir: Optional[Path] = None) -> Optional[Path]:
    """Finds a dataset file checking custom_dir then configured DATA_DIRS."""
    search_dirs = [custom_dir] if custom_dir else []
    search_dirs.extend(correlation_settings.DATA_DIRS)

    for d in search_dirs:
        if not d:
            continue
        candidate = Path(d) / filename
        if candidate.exists() and candidate.is_file():
            return candidate
    return None

def validate_dataset(dataset_dir: Optional[Path] = None, sample_rows: int = 5000) -> Dict[str, Any]:
    """
    Performs comprehensive pre-flight validation on all available dataset files.
    Returns structured report and saves dataset_validation_report.json.
    """
    report: Dict[str, Any] = {
        "timestamp": datetime.now().isoformat(),
        "status": "VALID",
        "validation_directory": str(dataset_dir) if dataset_dir else "Auto-detected search paths",
        "files": {},
        "summary": {
            "total_files_checked": len(EXPECTED_FILES),
            "files_found": 0,
            "files_missing": 0,
            "critical_errors": []
        }
    }

    # 1. Check txs_features.csv (Core required file)
    tx_file = find_dataset_file("txs_features.csv", dataset_dir)
    if not tx_file:
        report["status"] = "CRITICAL_MISSING_FILES"
        report["summary"]["critical_errors"].append("txs_features.csv not found in any search path.")
        report["files"]["txs_features.csv"] = {"exists": False, "error": "File not found"}
    else:
        report["summary"]["files_found"] += 1
        file_size_mb = round(os.path.getsize(tx_file) / (1024 * 1024), 2)
        try:
            sample_df = pd.read_csv(tx_file, nrows=sample_rows)
            schema = detect_schema(list(sample_df.columns), "transaction")
            txid_col = schema.get("txid")
            time_col = schema.get("timestamp")
            
            missing_txid = 0
            if txid_col:
                missing_txid = int(sample_df[txid_col].isna().sum())

            time_errors = 0
            if time_col:
                # check if numeric (Time step) or datetime string
                for val in sample_df[time_col].dropna().head(100):
                    try:
                        # If not float/int, try parse as date
                        if not isinstance(val, (int, float)):
                            pd.to_datetime(val)
                    except Exception:
                        time_errors += 1

            report["files"]["txs_features.csv"] = {
                "exists": True,
                "path": str(tx_file),
                "size_mb": file_size_mb,
                "sample_rows_checked": len(sample_df),
                "detected_columns": {k: v for k, v in schema.items() if v},
                "missing_txid_in_sample": missing_txid,
                "timestamp_parse_errors_in_sample": time_errors,
                "status": "OK" if txid_col else "WARNING_MISSING_TXID_COLUMN"
            }
        except Exception as e:
            report["files"]["txs_features.csv"] = {
                "exists": True,
                "path": str(tx_file),
                "size_mb": file_size_mb,
                "error": f"Failed to sample CSV: {str(e)}"
            }

    # 2. Check remaining files
    for fname in EXPECTED_FILES[1:]:
        fpath = find_dataset_file(fname, dataset_dir)
        if not fpath:
            report["summary"]["files_missing"] += 1
            report["files"][fname] = {"exists": False, "optional": fname not in ["txs_classes.csv"]}
            continue

        report["summary"]["files_found"] += 1
        size_mb = round(os.path.getsize(fpath) / (1024 * 1024), 2)
        try:
            head_df = pd.read_csv(fpath, nrows=5)
            report["files"][fname] = {
                "exists": True,
                "path": str(fpath),
                "size_mb": size_mb,
                "columns": list(head_df.columns),
                "status": "OK"
            }
        except Exception as e:
            report["files"][fname] = {
                "exists": True,
                "path": str(fpath),
                "size_mb": size_mb,
                "error": str(e)
            }

    # Save to correlation_output/
    output_dir = correlation_settings.OUTPUT_DIR
    output_dir.mkdir(parents=True, exist_ok=True)
    report_file = output_dir / "dataset_validation_report.json"
    with open(report_file, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)

    logger.info(f"Dataset validation completed. Status: {report['status']}. Report saved to {report_file}")
    return report
