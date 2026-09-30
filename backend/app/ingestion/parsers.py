import io
import json
import csv
import ast
import xml.etree.ElementTree as ET
import pandas as pd
from typing import Iterator, Dict, Any, List, Union
from backend.app.core.errors import InvalidFileFormatError

def parse_list_field(val: Any) -> List[Any]:
    """Helper to safely parse string representations of lists in CSV/JSON/XML."""
    if val is None or (isinstance(val, float) and pd.isna(val)):
        return []
    if isinstance(val, list):
        return val
    if isinstance(val, (int, float)):
        return [val]
    val_str = str(val).strip()
    if not val_str:
        return []
    # Check if JSON array string or Python literal
    if (val_str.startswith("[") and val_str.endswith("]")) or (val_str.startswith("(") and val_str.endswith(")")):
        try:
            parsed = json.loads(val_str)
            if isinstance(parsed, list):
                return parsed
        except Exception:
            try:
                parsed = ast.literal_eval(val_str)
                if isinstance(parsed, (list, tuple)):
                    return list(parsed)
            except Exception:
                pass
        # Strip brackets and split by comma/semicolon/pipe
        inner = val_str[1:-1].strip()
        if not inner:
            return []
        val_str = inner

    # Split by semicolon, comma, or pipe if multi-value
    if ";" in val_str:
        return [x.strip() for x in val_str.split(";") if x.strip()]
    if "|" in val_str:
        return [x.strip() for x in val_str.split("|") if x.strip()]
    if "," in val_str:
        return [x.strip() for x in val_str.split(",") if x.strip()]

    return [val_str]

def find_col(row_dict: dict, *candidates: str) -> Any:
    """Finds a column value matching any of the candidate names case-insensitively and ignoring punctuation."""
    norm_candidates = {c.lower().replace("_", "").replace("-", "").replace(" ", "") for c in candidates}
    for k, v in row_dict.items():
        if k and str(k).lower().replace("_", "").replace("-", "").replace(" ", "") in norm_candidates:
            if v is not None and not (isinstance(v, float) and pd.isna(v)):
                val_str = str(v).strip()
                if val_str and val_str.lower() not in ("nan", "null", "none"):
                    return v
    return None

def parse_csv_stream(file_obj_or_path: Union[io.BytesIO, str, io.StringIO], chunk_size: int = 2000) -> Iterator[List[Dict[str, Any]]]:
    """
    Parses CSV in streaming chunks without loading the whole file into memory.
    Robust against arbitrary column naming, casing, and supports both transaction and wallet-class schemas.
    Optimized for high-throughput streaming (O(1) column resolution, vector-friendly dictionary extraction).
    """
    try:
        for chunk in pd.read_csv(file_obj_or_path, chunksize=chunk_size, dtype=object, keep_default_na=False):
            # Pre-compute normalized column mapping once per chunk
            col_lookup = {}
            for col in chunk.columns:
                norm = str(col).lower().replace("_", "").replace("-", "").replace(" ", "")
                col_lookup[norm] = col

            is_wallet_dataset = ("address" in col_lookup or "walletaddress" in col_lookup or "wallet" in col_lookup) and not any(t in col_lookup for t in ("txid", "txhash", "transactionid", "txid1"))
            is_tx_class_dataset = any(t in col_lookup for t in ("txid", "txhash", "transactionid")) and ("class" in col_lookup or "label" in col_lookup) and not any(a in col_lookup for a in ("inputaddresses", "inputs", "inputwallets", "outputaddresses", "outputs", "outputwallets"))

            # Helper for O(1) column retrieval
            def get_val(row_dict: dict, *candidates: str) -> Any:
                for c in candidates:
                    norm_c = c.lower().replace("_", "").replace("-", "").replace(" ", "")
                    orig = col_lookup.get(norm_c)
                    if orig is not None and orig in row_dict:
                        v = row_dict[orig]
                        if v is not None:
                            val_str = str(v).strip()
                            if val_str and val_str.lower() not in ("nan", "null", "none"):
                                return v
                return None

            records = []
            for row_dict in chunk.to_dict(orient="records"):
                if is_wallet_dataset:
                    mapped = {
                        "record_type": "WALLET",
                        "address": str(get_val(row_dict, "address", "wallet_address", "wallet") or "").strip(),
                        "class": str(get_val(row_dict, "class", "label", "category") or "3").strip(),
                    }
                    records.append(mapped)
                    continue

                if is_tx_class_dataset:
                    mapped = {
                        "record_type": "TX_CLASS",
                        "txid": str(get_val(row_dict, "txid", "tx_id", "txId", "tx_hash", "txhash", "transaction_id") or "").strip(),
                        "class": str(get_val(row_dict, "class", "label", "category") or "3").strip(),
                    }
                    records.append(mapped)
                    continue

                # Standard Transaction Record
                mapped = {
                    "record_type": "TRANSACTION",
                    "txid": get_val(row_dict, "txid", "tx_id", "txId", "tx_hash", "txhash", "transaction_id", "txId1"),
                    "timestamp": get_val(row_dict, "timestamp", "time", "block_time", "date", "datetime", "ts", "network_timestamp"),
                    "fee": get_val(row_dict, "fee", "fees", "tx_fee") or 0.0,
                    "script_type": get_val(row_dict, "script_type", "scripttype", "type", "script") or "P2PKH",
                    "input_addresses": parse_list_field(get_val(row_dict, "input_addresses", "inputaddresses", "inputs", "input_wallets", "inputwallets", "src_addresses", "sender")),
                    "output_addresses": parse_list_field(get_val(row_dict, "output_addresses", "outputaddresses", "outputs", "output_wallets", "outputwallets", "dst_addresses", "receiver")),
                    "input_amounts": parse_list_field(get_val(row_dict, "input_amounts", "inputamounts", "in_amounts", "inamounts", "input_val")),
                    "output_amounts": parse_list_field(get_val(row_dict, "output_amounts", "outputamounts", "out_amounts", "outamounts", "amounts", "output_val")),
                    "src_ip": get_val(row_dict, "src_ip", "srcip", "source_ip", "ip", "peer_ip", "relay_ip"),
                    "dst_ip": get_val(row_dict, "dst_ip", "dstip", "destination_ip"),
                    "src_port": get_val(row_dict, "src_port", "srcport"),
                    "dst_port": get_val(row_dict, "dst_port", "dstport"),
                    "geo_country": get_val(row_dict, "geo_country", "geocountry", "country", "location"),
                    "asn": get_val(row_dict, "asn", "as_number", "autonomous_system"),
                    "wallet_classes": get_val(row_dict, "wallet_classes", "walletclasses"),
                    "tx_class": get_val(row_dict, "tx_class", "txclass", "class", "label"),
                    "ml_anomaly_score": get_val(row_dict, "ml_anomaly_score", "mlanomalyscore", "anomaly_score")
                }
                records.append(mapped)
            yield records
    except Exception as e:
        raise InvalidFileFormatError(f"CSV Parsing Failed: {str(e)}")

def stream_json_objects(source: Union[str, bytes, io.BytesIO, io.StringIO]) -> Iterator[Dict[str, Any]]:
    """
    Memory-safe generator yielding JSON transaction dicts from file path, bytes, or stream.
    Supports:
    1. Standard JSON array: [ {...}, {...} ]
    2. JSON object with array property: {"transactions": [ {...} ]} or {"data": [...]}
    3. JSON Lines (NDJSON): one JSON object per line
    """
    if isinstance(source, (bytes, bytearray)):
        content_str = source.decode("utf-8", errors="replace")
        data = json.loads(content_str)
        if isinstance(data, dict):
            for k in ("transactions", "data", "records", "items"):
                if k in data and isinstance(data[k], list):
                    for item in data[k]:
                        if isinstance(item, dict):
                            yield item
                    return
            yield data
        elif isinstance(data, list):
            for item in data:
                if isinstance(item, dict):
                    yield item
        return

    f_to_close = None
    if isinstance(source, str):
        f = open(source, "r", encoding="utf-8", errors="replace")
        f_to_close = f
    elif hasattr(source, "read"):
        f = source
    else:
        return

    try:
        # Detect first non-whitespace character
        first_char = ""
        while True:
            ch = f.read(1)
            if not ch:
                break
            if not ch.isspace():
                first_char = ch
                break

        if not first_char:
            return

        if first_char == "[":
            decoder = json.JSONDecoder()
            buffer = ""
            while True:
                chunk = f.read(65536)
                if not chunk:
                    break
                buffer += chunk
                while buffer:
                    buffer = buffer.lstrip()
                    if not buffer:
                        break
                    if buffer[0] == ",":
                        buffer = buffer[1:].lstrip()
                    if not buffer:
                        break
                    if buffer[0] == "]":
                        return
                    try:
                        obj, idx = decoder.raw_decode(buffer)
                        if isinstance(obj, dict):
                            yield obj
                        buffer = buffer[idx:].lstrip()
                    except json.JSONDecodeError:
                        break

            # Flush remaining buffer
            buffer = buffer.lstrip()
            while buffer and buffer[0] != "]":
                if buffer[0] == ",":
                    buffer = buffer[1:].lstrip()
                if not buffer or buffer[0] == "]":
                    break
                try:
                    obj, idx = decoder.raw_decode(buffer)
                    if isinstance(obj, dict):
                        yield obj
                    buffer = buffer[idx:].lstrip()
                except json.JSONDecodeError:
                    break

        elif first_char == "{":
            rest_of_line = f.readline()
            first_line = first_char + rest_of_line
            is_ndjson = False
            try:
                first_obj = json.loads(first_line.strip())
                if isinstance(first_obj, dict) and not any(k in first_obj for k in ("transactions", "data", "records")):
                    is_ndjson = True
                    yield first_obj
            except Exception:
                is_ndjson = False

            if is_ndjson:
                for line in f:
                    line = line.strip()
                    if line:
                        try:
                            obj = json.loads(line)
                            if isinstance(obj, dict):
                                yield obj
                        except Exception:
                            pass
            else:
                if hasattr(f, "seek"):
                    f.seek(0)
                    data = json.load(f)
                else:
                    data = json.loads(first_line + f.read())
                if isinstance(data, dict):
                    for k in ("transactions", "data", "records", "items"):
                        if k in data and isinstance(data[k], list):
                            for item in data[k]:
                                if isinstance(item, dict):
                                    yield item
                            return
                    yield data
                elif isinstance(data, list):
                    for item in data:
                        if isinstance(item, dict):
                            yield item
    finally:
        if f_to_close:
            f_to_close.close()

def parse_json_stream(file_bytes_or_path: Union[bytes, str, io.BytesIO, io.StringIO], chunk_size: int = 1000) -> Iterator[List[Dict[str, Any]]]:
    """
    Parses JSON data in memory-safe chunks from file path or bytes.
    """
    try:
        current_chunk = []
        for item in stream_json_objects(file_bytes_or_path):
            mapped = {
                "txid": item.get("txid") or item.get("tx_hash"),
                "timestamp": item.get("timestamp") or item.get("time"),
                "fee": item.get("fee", 0.0),
                "script_type": item.get("script_type", "P2PKH"),
                "input_addresses": parse_list_field(item.get("input_addresses") or item.get("inputs")),
                "output_addresses": parse_list_field(item.get("output_addresses") or item.get("outputs")),
                "input_amounts": parse_list_field(item.get("input_amounts")),
                "output_amounts": parse_list_field(item.get("output_amounts") or item.get("amounts")),
                "src_ip": item.get("src_ip") or item.get("ip"),
                "dst_ip": item.get("dst_ip"),
                "src_port": item.get("src_port"),
                "dst_port": item.get("dst_port"),
                "geo_country": item.get("geo_country") or item.get("country"),
                "asn": item.get("asn")
            }
            current_chunk.append(mapped)
            if len(current_chunk) >= chunk_size:
                yield current_chunk
                current_chunk = []
        if current_chunk:
            yield current_chunk

    except Exception as e:
        raise InvalidFileFormatError(f"JSON Parsing Failed: {str(e)}")

def parse_xml_stream(file_bytes_or_path: Union[bytes, str, io.BytesIO], chunk_size: int = 1000) -> Iterator[List[Dict[str, Any]]]:
    """
    Streaming XML parser using ET.iterparse for transaction elements.
    Accepts a disk file path (memory-safe) or in-memory bytes.
    """
    try:
        if isinstance(file_bytes_or_path, str):
            source = file_bytes_or_path
        elif isinstance(file_bytes_or_path, (bytes, bytearray)):
            source = io.BytesIO(file_bytes_or_path)
        else:
            source = file_bytes_or_path

        context = ET.iterparse(source, events=("end",))
        current_chunk = []

        for event, elem in context:
            # Match top-level transaction container tags
            if elem.tag.lower() in ("transaction", "record", "tx"):
                mapped = {
                    "txid": elem.findtext("txid") or elem.findtext("tx_hash"),
                    "timestamp": elem.findtext("timestamp") or elem.findtext("time"),
                    "fee": elem.findtext("fee") or "0.0",
                    "script_type": elem.findtext("script_type") or "P2PKH",
                    "src_ip": elem.findtext("src_ip") or elem.findtext("ip"),
                    "dst_ip": elem.findtext("dst_ip"),
                    "src_port": elem.findtext("src_port"),
                    "dst_port": elem.findtext("dst_port"),
                    "geo_country": elem.findtext("geo_country") or elem.findtext("country"),
                    "asn": elem.findtext("asn"),
                }

                # Inputs
                in_addrs = []
                in_amts = []
                inputs_elem = elem.find("input_addresses")
                if inputs_elem is None:
                    inputs_elem = elem.find("inputs")

                if inputs_elem is not None and len(inputs_elem) > 0:
                    for child in inputs_elem:
                        if child.text:
                            in_addrs.append(child.text.strip())
                else:
                    raw_in = elem.findtext("input_addresses") or elem.findtext("inputs")
                    in_addrs = parse_list_field(raw_in)

                in_amts_elem = elem.find("input_amounts")
                if in_amts_elem is not None and len(in_amts_elem) > 0:
                    for child in in_amts_elem:
                        if child.text:
                            in_amts.append(child.text.strip())
                else:
                    raw_amts = elem.findtext("input_amounts")
                    in_amts = parse_list_field(raw_amts)

                # Outputs
                out_addrs = []
                out_amts = []
                outputs_elem = elem.find("output_addresses")
                if outputs_elem is None:
                    outputs_elem = elem.find("outputs")

                if outputs_elem is not None and len(outputs_elem) > 0:
                    for child in outputs_elem:
                        if child.text:
                            out_addrs.append(child.text.strip())
                else:
                    raw_out = elem.findtext("output_addresses") or elem.findtext("outputs")
                    out_addrs = parse_list_field(raw_out)

                out_amts_elem = elem.find("output_amounts")
                if out_amts_elem is None:
                    out_amts_elem = elem.find("amounts")

                if out_amts_elem is not None and len(out_amts_elem) > 0:
                    for child in out_amts_elem:
                        if child.text:
                            out_amts.append(child.text.strip())
                else:
                    raw_out_amts = elem.findtext("output_amounts") or elem.findtext("amounts")
                    out_amts = parse_list_field(raw_out_amts)

                mapped["input_addresses"] = in_addrs
                mapped["input_amounts"] = in_amts
                mapped["output_addresses"] = out_addrs
                mapped["output_amounts"] = out_amts

                current_chunk.append(mapped)
                elem.clear()

                if len(current_chunk) >= chunk_size:
                    yield current_chunk
                    current_chunk = []

        if current_chunk:
            yield current_chunk

    except Exception as e:
        raise InvalidFileFormatError(f"XML Parsing Failed: {str(e)}")
