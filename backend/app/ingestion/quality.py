from typing import Dict, Any, List, Set
from datetime import datetime, timezone

class DataQualityAnalyzer:
    def __init__(self):
        self.total_records = 0
        self.valid_records = 0
        self.rejected_records = 0
        self.duplicate_records = 0
        self.missing_fields_count = 0
        
        self.unique_wallets: Set[str] = set()
        self.unique_txids: Set[str] = set()
        self.unique_src_ips: Set[str] = set()
        self.unique_countries: Set[str] = set()
        self.unique_asns: Set[str] = set()
        
        self.time_min: datetime = None
        self.time_max: datetime = None
        self.total_btc_volume: float = 0.0
        self.total_fee: float = 0.0
        
        self.field_presence: Dict[str, int] = {
            "txid": 0,
            "timestamp": 0,
            "input_addresses": 0,
            "output_addresses": 0,
            "input_amounts": 0,
            "output_amounts": 0,
            "fee": 0,
            "src_ip": 0,
            "geo_country": 0,
            "asn": 0
        }
        self.rejected_reasons: Dict[str, int] = {}

    def record_rejected(self, reason: str):
        self.total_records += 1
        self.rejected_records += 1
        self.rejected_reasons[reason] = self.rejected_reasons.get(reason, 0) + 1

    def record_duplicate(self, txid: str):
        self.total_records += 1
        self.duplicate_records += 1
        reason = f"Duplicate TXID: {txid}"
        self.rejected_reasons[reason] = self.rejected_reasons.get(reason, 0) + 1

    def record_valid(self, normalized_record: Dict[str, Any]):
        self.total_records += 1
        self.valid_records += 1

        if normalized_record.get("record_type") == "WALLET":
            addr = normalized_record.get("address", "")
            if addr:
                self.unique_wallets.add(addr)
                self.field_presence["input_addresses"] += 1
            return

        txid = normalized_record.get("txid")
        if txid:
            self.unique_txids.add(txid)
            self.field_presence["txid"] += 1

        ts = normalized_record.get("timestamp")
        if isinstance(ts, datetime):
            ts = ts.replace(tzinfo=timezone.utc) if ts.tzinfo is None else ts.astimezone(timezone.utc)
            self.field_presence["timestamp"] += 1
            if self.time_min is None:
                self.time_min = ts
            else:
                cur_min = self.time_min.replace(tzinfo=timezone.utc) if self.time_min.tzinfo is None else self.time_min
                if ts < cur_min:
                    self.time_min = ts

            if self.time_max is None:
                self.time_max = ts
            else:
                cur_max = self.time_max.replace(tzinfo=timezone.utc) if self.time_max.tzinfo is None else self.time_max
                if ts > cur_max:
                    self.time_max = ts

        # Wallets
        for w in normalized_record.get("input_addresses", []):
            self.unique_wallets.add(w)
        if normalized_record.get("input_addresses"):
            self.field_presence["input_addresses"] += 1

        for w in normalized_record.get("output_addresses", []):
            self.unique_wallets.add(w)
        if normalized_record.get("output_addresses"):
            self.field_presence["output_addresses"] += 1

        # Amounts
        in_tot = normalized_record.get("input_total", 0.0)
        out_tot = normalized_record.get("output_total", 0.0)
        self.total_btc_volume += max(in_tot, out_tot)

        if normalized_record.get("input_amounts"):
            self.field_presence["input_amounts"] += 1
        if normalized_record.get("output_amounts"):
            self.field_presence["output_amounts"] += 1

        # Fee
        fee = normalized_record.get("fee", 0.0)
        self.total_fee += fee
        if fee > 0:
            self.field_presence["fee"] += 1

        # Network
        src_ip = normalized_record.get("src_ip")
        if src_ip:
            self.unique_src_ips.add(src_ip)
            self.field_presence["src_ip"] += 1

        country = normalized_record.get("geo_country")
        if country and country != "UNKNOWN":
            self.unique_countries.add(country)
            self.field_presence["geo_country"] += 1

        asn = normalized_record.get("asn")
        if asn and asn != "UNKNOWN":
            self.unique_asns.add(asn)
            self.field_presence["asn"] += 1

    def generate_report(self) -> Dict[str, Any]:
        completeness = {}
        denom = max(1, self.total_records)
        for k, v in self.field_presence.items():
            completeness[k] = round((v / denom) * 100.0, 1)

        avg_fee = round(self.total_fee / max(1, self.valid_records), 6)

        return {
            "total_records": self.total_records,
            "valid_records": self.valid_records,
            "rejected_records": self.rejected_records,
            "duplicate_records": self.duplicate_records,
            "missing_fields_count": self.missing_fields_count,
            "unique_wallets": len(self.unique_wallets),
            "unique_txids": len(self.unique_txids),
            "unique_src_ips": len(self.unique_src_ips),
            "unique_countries": len(self.unique_countries),
            "unique_asns": len(self.unique_asns),
            "time_min": self.time_min.isoformat() if self.time_min else None,
            "time_max": self.time_max.isoformat() if self.time_max else None,
            "total_btc_volume": round(self.total_btc_volume, 4),
            "avg_fee": avg_fee,
            "field_completeness": completeness,
            "rejected_reasons": self.rejected_reasons
        }
