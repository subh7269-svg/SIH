"""
Dynamic column detection and schema mapper for heterogeneous forensic CSVs.
Supports reasonable variations in column naming across Elliptic, Elliptic++,
Bitcoin core dumps, and network capture logs.
"""
from typing import Dict, List, Optional
import pandas as pd

COLUMN_ALIASES = {
    "txid": [
        "txid", "tx_id", "transaction_id", "txId", "tx_hash", "hash", "txid1"
    ],
    "timestamp": [
        "timestamp", "time", "datetime", "block_time", "time_step", "Time step", "timestep", "date"
    ],
    "fee": [
        "fee", "fees", "transaction_fee", "tx_fee", "fee_btc", "miner_fee"
    ],
    "script_type": [
        "script_type", "script", "type", "output_script_type", "address_type"
    ],
    "input_addresses": [
        "input_addresses", "input_address", "inputs", "in_addresses", "sender_addresses", "from_address"
    ],
    "output_addresses": [
        "output_addresses", "output_address", "outputs", "out_addresses", "recipient_addresses", "to_address"
    ],
    "input_amounts": [
        "input_amounts", "input_amount", "input_value", "in_BTC_total", "total_BTC", "amount", "value"
    ],
    "output_amounts": [
        "output_amounts", "output_amount", "output_value", "out_BTC_total"
    ],
    "tx_class": [
        "class", "label", "tx_class", "category", "illicit_flag"
    ],
    "wallet_address": [
        "address", "wallet", "wallet_address", "input_address", "output_address", "addr"
    ],
    "wallet_class": [
        "class", "wallet_class", "label", "category", "entity_type"
    ],
    "network_timestamp": [
        "timestamp", "time", "datetime", "packet_time", "capture_time", "observed_at"
    ],
    "src_ip": [
        "src_ip", "source_ip", "ip", "client_ip", "relay_ip", "src"
    ],
    "src_port": [
        "src_port", "source_port", "sport", "port", "client_port"
    ],
    "dst_ip": [
        "dst_ip", "destination_ip", "target_ip", "dst", "server_ip"
    ],
    "dst_port": [
        "dst_port", "destination_port", "dport", "server_port"
    ]
}

def detect_column(available_columns: List[str], standard_name: str) -> Optional[str]:
    """
    Detects which column in available_columns corresponds to standard_name.
    Matches case-insensitively and handles whitespace/underscores.
    """
    candidates = COLUMN_ALIASES.get(standard_name, [standard_name])
    clean_map = {str(col).strip().lower(): col for col in available_columns}

    # 1. Exact canonical alias match
    for cand in candidates:
        if cand.lower() in clean_map:
            return clean_map[cand.lower()]

    # 2. Substring or relaxed match
    for cand in candidates:
        for clean_col, orig_col in clean_map.items():
            if cand.lower() in clean_col:
                return orig_col

    return None

def detect_schema(columns: List[str], target_type: str = "transaction") -> Dict[str, Optional[str]]:
    """
    Detects mapping from standard column names to actual dataframe column names.
    target_type can be 'transaction', 'network', 'wallet', or 'tx_class'.
    """
    schema_keys = {
        "transaction": ["txid", "timestamp", "fee", "script_type", "input_addresses", "output_addresses", "input_amounts"],
        "network": ["timestamp", "src_ip", "src_port", "dst_ip", "dst_port", "txid"],
        "wallet": ["wallet_address", "wallet_class"],
        "tx_class": ["txid", "tx_class"]
    }.get(target_type, ["txid"])

    return {key: detect_column(columns, key) for key in schema_keys}

def normalize_txid(val) -> str:
    """Normalizes txid representation removing float decimals (e.g. 3321.0 -> 3321)."""
    if val is None or pd.isna(val):
        return ""
    s = str(val).strip()
    if s.endswith(".0"):
        try:
            return str(int(float(s)))
        except Exception:
            return s
    return s
