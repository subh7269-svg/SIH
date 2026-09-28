"""
Chunked streaming transaction ingestion module.
Processes large transaction CSVs (600+ MB) without exhausting memory.
Extracts txid, timestamp, fee, script_type, addresses, and amounts.
Computes fan_in, fan_out, input_count, output_count, total_input_amount, amount_per_output.
"""
import logging
from pathlib import Path
from typing import Generator, Dict, Any, List, Optional
import pandas as pd
import numpy as np

from backend.app.correlation.config import correlation_settings
from backend.app.correlation.column_detector import detect_schema

logger = logging.getLogger("tracex.correlation.ingestion")

def safe_parse_list(val: Any) -> List[str]:
    """Safely extracts a list of strings from string, list, or null."""
    if val is None or pd.isna(val):
        return []
    if isinstance(val, (list, tuple, set)):
        return [str(x).strip() for x in val if str(x).strip()]
    s = str(val).strip()
    if not s or s == "[]":
        return []
    # Strip brackets if present
    if s.startswith("[") and s.endswith("]"):
        s = s[1:-1]
    # Split on comma, semicolon, space
    delimiter = "," if "," in s else (";" if ";" in s else None)
    parts = s.split(delimiter) if delimiter else s.split()
    return [p.strip().strip("'").strip('"') for p in parts if p.strip()]

def safe_parse_amounts(val: Any) -> List[float]:
    """Safely parses float amounts from string or list."""
    if val is None or pd.isna(val):
        return []
    if isinstance(val, (int, float)):
        return [float(val)]
    items = safe_parse_list(val)
    parsed = []
    for item in items:
        try:
            parsed.append(float(item))
        except (ValueError, TypeError):
            continue
    return parsed

def stream_transactions(
    file_path: Path,
    chunk_size: int = correlation_settings.CHUNK_SIZE,
    max_transactions: Optional[int] = None
) -> Generator[pd.DataFrame, None, None]:
    """
    Generator streaming processed transaction DataFrames chunk by chunk.
    Enforces chunk_size and avoids loading the entire 662MB file into memory.
    """
    total_yielded = 0
    logger.info(f"Initiating chunked stream of transactions from {file_path} (chunk_size={chunk_size})")

    # Read first 1 row to detect schema
    header_df = pd.read_csv(file_path, nrows=1)
    schema = detect_schema(list(header_df.columns), "transaction")

    txid_col = schema.get("txid") or header_df.columns[0]
    time_col = schema.get("timestamp")
    fee_col = schema.get("fee")
    script_col = schema.get("script_type")
    in_addr_col = schema.get("input_addresses")
    out_addr_col = schema.get("output_addresses")
    in_amt_col = schema.get("input_amounts")
    out_amt_col = schema.get("output_amounts")

    # Check for specific Elliptic++ feature columns if present
    cols = header_df.columns
    has_num_inputs = "num_input_addresses" in cols
    has_num_outputs = "num_output_addresses" in cols
    has_in_degree = "in_txs_degree" in cols
    has_out_degree = "out_txs_degree" in cols
    has_total_btc = "total_BTC" in cols
    has_fees = "fees" in cols

    reader = pd.read_csv(
        file_path,
        chunksize=chunk_size,
        low_memory=False
    )

    for chunk_idx, raw_chunk in enumerate(reader):
        processed_records = []

        for _, row in raw_chunk.iterrows():
            from backend.app.correlation.column_detector import normalize_txid
            txid = normalize_txid(row.get(txid_col)) if pd.notna(row.get(txid_col)) else None
            if not txid or txid.lower() in ("nan", "none", ""):
                continue

            # Timestamp parsing
            timestamp_val = row.get(time_col) if time_col else None
            if pd.isna(timestamp_val):
                timestamp_val = "1970-01-01T00:00:00Z"
            elif isinstance(timestamp_val, (int, float, np.integer, np.floating)):
                # If numeric time step, format as block/step timestamp
                timestamp_val = int(timestamp_val)
            else:
                timestamp_val = str(timestamp_val).strip()

            # Fee
            fee_val = 0.0
            raw_fee = row.get(fee_col) if fee_col else (row.get("fees") if has_fees else 0.0)
            if pd.notna(raw_fee):
                try:
                    fee_val = float(raw_fee)
                except (ValueError, TypeError):
                    fee_val = 0.0

            # Script Type
            script_type = "P2PKH"
            if script_col and pd.notna(row.get(script_col)):
                script_type = str(row.get(script_col)).strip()

            # Addresses & Amounts
            in_addresses = safe_parse_list(row.get(in_addr_col)) if in_addr_col else []
            out_addresses = safe_parse_list(row.get(out_addr_col)) if out_addr_col else []
            in_amounts = safe_parse_amounts(row.get(in_amt_col)) if in_amt_col else []

            # Determine Counts and Degrees
            # 1. Input count & fan_in
            if has_num_inputs and pd.notna(row.get("num_input_addresses")):
                input_count = int(row.get("num_input_addresses"))
            elif in_addresses:
                input_count = len(in_addresses)
            elif has_in_degree and pd.notna(row.get("in_txs_degree")):
                input_count = int(row.get("in_txs_degree"))
            else:
                input_count = 1

            fan_in = input_count

            # 2. Output count & fan_out
            if has_num_outputs and pd.notna(row.get("num_output_addresses")):
                output_count = int(row.get("num_output_addresses"))
            elif out_addresses:
                output_count = len(out_addresses)
            elif has_out_degree and pd.notna(row.get("out_txs_degree")):
                output_count = int(row.get("out_txs_degree"))
            else:
                output_count = 1

            fan_out = output_count

            # 3. Total amount & amount per output
            if in_amounts:
                total_input_amount = float(sum(in_amounts))
            elif has_total_btc and pd.notna(row.get("total_BTC")):
                total_input_amount = float(row.get("total_BTC"))
            elif in_amt_col and pd.notna(row.get(in_amt_col)):
                try:
                    total_input_amount = float(row.get(in_amt_col))
                except (ValueError, TypeError):
                    total_input_amount = 0.0
            else:
                total_input_amount = 0.0

            amount_per_output = total_input_amount / max(1, output_count)

            record = {
                "txid": txid,
                "timestamp": timestamp_val,
                "fee": fee_val,
                "script_type": script_type,
                "input_count": input_count,
                "output_count": output_count,
                "fan_in": fan_in,
                "fan_out": fan_out,
                "total_input_amount": total_input_amount,
                "amount_per_output": amount_per_output,
                "input_addresses": in_addresses,
                "output_addresses": out_addresses,
            }
            processed_records.append(record)
            total_yielded += 1

            if max_transactions and total_yielded >= max_transactions:
                break

        df_out = pd.DataFrame(processed_records)
        yield df_out

        if max_transactions and total_yielded >= max_transactions:
            logger.info(f"Reached configured limit of {max_transactions} transactions.")
            break
