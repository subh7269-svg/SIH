"""
Network observation correlation module.
Correlates blockchain transactions with network wire observations (network_data.csv).
Supports:
1. Exact TXID match (confidence = 1.0)
2. Temporal window proximity search (configurable window, e.g. +/- 120s)
Decaying confidence formula: max(0.0, 1.0 - time_difference_seconds / time_window)
Forensic compliance: Never claims IP ownership of wallet; strictly identifies temporal network correlation.
"""
import bisect
import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime, timezone
import pandas as pd
import numpy as np

from backend.app.correlation.config import correlation_settings
from backend.app.correlation.column_detector import detect_schema
from backend.app.correlation.validator import find_dataset_file

logger = logging.getLogger("tracex.correlation.network")

def parse_epoch_seconds(val: Any) -> Optional[float]:
    """Converts datetime string, timestamp, or epoch int to float epoch seconds."""
    if val is None or pd.isna(val):
        return None
    if isinstance(val, (int, float, np.integer, np.floating)):
        # If small integer (e.g. Elliptic time step 1..49), scale as synthetic block step (3 hours each)
        if val < 1000000:
            return float(val * 10800.0)
        return float(val)
    try:
        dt = pd.to_datetime(val)
        if dt.tzinfo is None:
            dt = dt.tz_localize(timezone.utc)
        return dt.timestamp()
    except Exception:
        return None

class NetworkCorrelator:
    """
    Indexed network observation repository supporting fast O(1) TXID lookup
    and O(log N) binary search temporal window correlation.
    """
    def __init__(self, dataset_dir: Optional[Path] = None, time_window_seconds: Optional[float] = None):
        self.dataset_dir = dataset_dir
        self.time_window_seconds = (
            time_window_seconds
            if time_window_seconds is not None
            else correlation_settings.CORRELATION_TIME_WINDOW_SECONDS
        )
        self.exact_txid_map: Dict[str, Dict[str, Any]] = {}
        self.sorted_temporal_observations: List[Tuple[float, Dict[str, Any]]] = []
        self.timestamps_index: List[float] = []
        self.is_loaded = False

    def load_network_data(self, file_path: Optional[Path] = None) -> int:
        """Loads and indexes network_data.csv."""
        fpath = file_path or find_dataset_file("network_data.csv", self.dataset_dir)
        if not fpath:
            logger.warning("network_data.csv not found. Operating with zero network observations.")
            self.is_loaded = True
            return 0

        logger.info(f"Loading network observations from {fpath}")
        df = pd.read_csv(fpath)
        schema = detect_schema(list(df.columns), "network")

        time_col = schema.get("timestamp") or df.columns[0]
        src_ip_col = schema.get("src_ip") or "src_ip"
        src_port_col = schema.get("src_port") or "src_port"
        dst_ip_col = schema.get("dst_ip") or "dst_ip"
        dst_port_col = schema.get("dst_port") or "dst_port"
        txid_col = schema.get("txid") or "txid"

        raw_observations = []
        for _, row in df.iterrows():
            raw_time = row.get(time_col)
            epoch_sec = parse_epoch_seconds(raw_time)
            txid = str(row[txid_col]).strip() if txid_col in row and pd.notna(row[txid_col]) else None
            src_ip = str(row[src_ip_col]).strip() if src_ip_col in row and pd.notna(row[src_ip_col]) else "127.0.0.1"
            dst_ip = str(row[dst_ip_col]).strip() if dst_ip_col in row and pd.notna(row[dst_ip_col]) else "127.0.0.1"
            
            src_port = None
            if src_port_col in row and pd.notna(row[src_port_col]):
                try:
                    src_port = int(row[src_port_col])
                except Exception:
                    src_port = 8333
            else:
                src_port = 8333

            dst_port = None
            if dst_port_col in row and pd.notna(row[dst_port_col]):
                try:
                    dst_port = int(row[dst_port_col])
                except Exception:
                    dst_port = 8333
            else:
                dst_port = 8333

            record = {
                "timestamp": str(raw_time),
                "epoch_seconds": epoch_sec,
                "src_ip": src_ip,
                "src_port": src_port,
                "dst_ip": dst_ip,
                "dst_port": dst_port,
                "txid": txid
            }

            # 1. Exact TXID mapping if present
            if txid and txid.lower() not in ("none", "nan", ""):
                self.exact_txid_map[txid] = record

            # 2. Temporal index if timestamp valid
            if epoch_sec is not None:
                raw_observations.append((epoch_sec, record))

        # Sort temporal observations for binary search
        raw_observations.sort(key=lambda x: x[0])
        self.sorted_temporal_observations = raw_observations
        self.timestamps_index = [x[0] for x in raw_observations]

        self.is_loaded = True
        logger.info(
            f"Network data indexed: {len(self.exact_txid_map)} exact TXID entries, "
            f"{len(self.sorted_temporal_observations)} temporal records."
        )
        return len(df)

    def correlate(self, txid: str, tx_timestamp: Any) -> Dict[str, Any]:
        """
        Correlates a transaction with network data.
        Returns correlation details including confidence and method.
        """
        # Step 1: Check Exact TXID match
        if txid in self.exact_txid_map:
            obs = self.exact_txid_map[txid]
            tx_epoch = parse_epoch_seconds(tx_timestamp)
            net_epoch = obs["epoch_seconds"]
            dt = abs(tx_epoch - net_epoch) if (tx_epoch and net_epoch) else 0.0

            return {
                "network_timestamp": obs["timestamp"],
                "time_difference_seconds": round(dt, 2),
                "src_ip": obs["src_ip"],
                "src_port": obs["src_port"],
                "dst_ip": obs["dst_ip"],
                "dst_port": obs["dst_port"],
                "network_txid": obs["txid"],
                "correlation_method": "exact_txid",
                "network_confidence": 1.0,
                "observation_note": "network observation exactly matched by transaction identifier (TXID)"
            }

        # Step 2: Temporal Window Proximity Search
        tx_epoch = parse_epoch_seconds(tx_timestamp)
        if tx_epoch is not None and self.timestamps_index:
            window = self.time_window_seconds
            left_bound = tx_epoch - window
            right_bound = tx_epoch + window

            idx_left = bisect.bisect_left(self.timestamps_index, left_bound)
            idx_right = bisect.bisect_right(self.timestamps_index, right_bound)

            # Find closest observation within [idx_left, idx_right)
            best_diff = float("inf")
            best_obs = None
            for idx in range(idx_left, min(idx_right, len(self.sorted_temporal_observations))):
                obs_epoch, obs_data = self.sorted_temporal_observations[idx]
                diff = abs(tx_epoch - obs_epoch)
                if diff < best_diff:
                    best_diff = diff
                    best_obs = obs_data

            if best_obs and best_diff <= window:
                confidence = max(0.0, 1.0 - (best_diff / window))
                return {
                    "network_timestamp": best_obs["timestamp"],
                    "time_difference_seconds": round(best_diff, 2),
                    "src_ip": best_obs["src_ip"],
                    "src_port": best_obs["src_port"],
                    "dst_ip": best_obs["dst_ip"],
                    "dst_port": best_obs["dst_port"],
                    "network_txid": best_obs.get("txid"),
                    "correlation_method": "timestamp_window",
                    "network_confidence": round(confidence, 4),
                    "observation_note": "network observation temporally correlated with transaction within observation window"
                }

        # No correlation found
        return {
            "network_timestamp": None,
            "time_difference_seconds": None,
            "src_ip": None,
            "src_port": None,
            "dst_ip": None,
            "dst_port": None,
            "network_txid": None,
            "correlation_method": "none",
            "network_confidence": 0.0,
            "observation_note": "no network observation correlated"
        }
