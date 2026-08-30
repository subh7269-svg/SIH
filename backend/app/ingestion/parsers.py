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

def parse_csv_stream(file_obj_or_path: Union[io.BytesIO, str, io.StringIO], chunk_size: int = 1000) -> Iterator[List[Dict[str, Any]]]:
    """
    Parses CSV in streaming chunks without loading the whole file into memory.
    """
    try:
        for chunk in pd.read_csv(file_obj_or_path, chunksize=chunk_size, dtype=object, keep_default_na=False):
            records = []
            for _, row in chunk.iterrows():
                row_dict = row.to_dict()
                
                # Standardize column naming
                mapped = {
                    "txid": row_dict.get("txid") or row_dict.get("TXID") or row_dict.get("tx_hash"),
                    "timestamp": row_dict.get("timestamp") or row_dict.get("time") or row_dict.get("block_time"),
                    "fee": row_dict.get("fee", 0.0),
                    "script_type": row_dict.get("script_type") or row_dict.get("type", "P2PKH"),
                    "input_addresses": parse_list_field(row_dict.get("input_addresses") or row_dict.get("inputs") or row_dict.get("src_addresses")),
                    "output_addresses": parse_list_field(row_dict.get("output_addresses") or row_dict.get("outputs") or row_dict.get("dst_addresses")),
                    "input_amounts": parse_list_field(row_dict.get("input_amounts") or row_dict.get("in_amounts")),
                    "output_amounts": parse_list_field(row_dict.get("output_amounts") or row_dict.get("out_amounts") or row_dict.get("amounts")),
                    "src_ip": row_dict.get("src_ip") or row_dict.get("ip") or row_dict.get("peer_ip"),
                    "dst_ip": row_dict.get("dst_ip"),
                    "src_port": row_dict.get("src_port"),
                    "dst_port": row_dict.get("dst_port"),
                    "geo_country": row_dict.get("geo_country") or row_dict.get("country"),
                    "asn": row_dict.get("asn")
                }
                records.append(mapped)
            yield records
    except Exception as e:
        raise InvalidFileFormatError(f"CSV Parsing Failed: {str(e)}")

def parse_json_stream(file_bytes: bytes, chunk_size: int = 1000) -> Iterator[List[Dict[str, Any]]]:
    """
    Parses JSON data in memory-safe chunks.
    """
    try:
        content_str = file_bytes.decode("utf-8", errors="replace")
        data = json.loads(content_str)
        if isinstance(data, dict):
            if "transactions" in data and isinstance(data["transactions"], list):
                raw_list = data["transactions"]
            elif "data" in data and isinstance(data["data"], list):
                raw_list = data["data"]
            elif "records" in data and isinstance(data["records"], list):
                raw_list = data["records"]
            else:
                raw_list = [data]
        elif isinstance(data, list):
            raw_list = data
        else:
            raise InvalidFileFormatError("JSON root must be a list or object with transaction array.")

        current_chunk = []
        for item in raw_list:
            if not isinstance(item, dict):
                continue
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

def parse_xml_stream(file_bytes: bytes, chunk_size: int = 1000) -> Iterator[List[Dict[str, Any]]]:
    """
    Streaming XML parser using ET.iterparse for transaction elements.
    """
    try:
        bio = io.BytesIO(file_bytes)
        context = ET.iterparse(bio, events=("end",))
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
