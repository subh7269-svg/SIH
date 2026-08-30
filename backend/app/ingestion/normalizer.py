import datetime
from datetime import timezone
from typing import Dict, Any, List
from dateutil import parser as dt_parser
from backend.app.geoip.offline_lookup import offline_geoip

def normalize_timestamp(val: Any) -> datetime.datetime:
    if isinstance(val, datetime.datetime):
        if val.tzinfo is None:
            return val.replace(tzinfo=timezone.utc)
        return val.astimezone(timezone.utc)
    if isinstance(val, (int, float)):
        # Epoch seconds or milliseconds
        if val > 1e11:
            val = val / 1000.0
        return datetime.datetime.fromtimestamp(val, tz=timezone.utc)
    if isinstance(val, str):
        try:
            dt = dt_parser.parse(val)
            if dt.tzinfo is None:
                return dt.replace(tzinfo=timezone.utc)
            return dt.astimezone(timezone.utc)
        except Exception:
            return datetime.datetime.now(timezone.utc)
    return datetime.datetime.now(timezone.utc)

def normalize_record(raw_record: Dict[str, Any]) -> Dict[str, Any]:
    """
    Normalizes a single validated transaction record:
    - Normalizes timestamp to UTC datetime
    - Cleans and formats IP strings
    - Computes or completes GeoIP/ASN fields using offline engine
    - Aligns input and output amounts with address lists
    - Standardizes script types and numerical amounts
    """
    txid = str(raw_record.get("txid", "")).strip()
    ts = normalize_timestamp(raw_record.get("timestamp"))

    # Inputs
    input_addrs = [str(a).strip() for a in raw_record.get("input_addresses", []) if str(a).strip()]
    raw_in_amts = raw_record.get("input_amounts", [])
    input_amts = []
    for i, _ in enumerate(input_addrs):
        if i < len(raw_in_amts):
            try:
                input_amts.append(max(0.0, float(raw_in_amts[i])))
            except Exception:
                input_amts.append(0.0)
        else:
            input_amts.append(0.0)

    # Outputs
    output_addrs = [str(a).strip() for a in raw_record.get("output_addresses", []) if str(a).strip()]
    raw_out_amts = raw_record.get("output_amounts", [])
    output_amts = []
    for i, _ in enumerate(output_addrs):
        if i < len(raw_out_amts):
            try:
                output_amts.append(max(0.0, float(raw_out_amts[i])))
            except Exception:
                output_amts.append(0.0)
        else:
            output_amts.append(0.0)

    fee = 0.0
    try:
        fee = max(0.0, float(raw_record.get("fee", 0.0)))
    except Exception:
        fee = 0.0

    script_type = str(raw_record.get("script_type", "P2PKH")).strip().upper()
    if script_type not in ("P2PKH", "P2SH", "P2WPKH", "P2WSH", "TAPROOT"):
        script_type = "P2PKH"

    # Network layer observations
    src_ip = str(raw_record.get("src_ip", "")).strip() if raw_record.get("src_ip") else None
    dst_ip = str(raw_record.get("dst_ip", "")).strip() if raw_record.get("dst_ip") else None
    
    src_port = None
    if raw_record.get("src_port") is not None:
        try:
            src_port = int(raw_record.get("src_port"))
        except Exception:
            src_port = 8333

    dst_port = None
    if raw_record.get("dst_port") is not None:
        try:
            dst_port = int(raw_record.get("dst_port"))
        except Exception:
            dst_port = 8333

    geo_country = raw_record.get("geo_country") or raw_record.get("country")
    asn = raw_record.get("asn")

    # Offline GeoIP enhancement if missing
    if src_ip and (not geo_country or geo_country == "UNKNOWN" or not asn or asn == "UNKNOWN"):
        geo_info = offline_geoip.lookup(src_ip)
        if not geo_country or geo_country == "UNKNOWN":
            geo_country = geo_info["country"]
        if not asn or asn == "UNKNOWN":
            asn = geo_info["asn"]

    return {
        "txid": txid,
        "timestamp": ts,
        "fee": fee,
        "script_type": script_type,
        "input_addresses": input_addrs,
        "input_amounts": input_amts,
        "output_addresses": output_addrs,
        "output_amounts": output_amts,
        "input_total": sum(input_amts),
        "output_total": sum(output_amts),
        "src_ip": src_ip,
        "dst_ip": dst_ip,
        "src_port": src_port,
        "dst_port": dst_port,
        "geo_country": geo_country or "UNKNOWN",
        "asn": asn or "UNKNOWN"
    }
