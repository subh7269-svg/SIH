import ipaddress
import json
from pathlib import Path
from typing import Dict, Any, Optional
from backend.app.core.config import settings

class OfflineGeoIP:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(OfflineGeoIP, cls).__new__(cls)
            cls._instance._init_db()
        return cls._instance

    def _init_db(self):
        self.subnets = []
        db_path = settings.GEOIP_DATA_PATH
        if db_path.exists():
            try:
                with open(db_path, "r", encoding="utf-8") as f:
                    entries = json.load(f)
                    for e in entries:
                        try:
                            net = ipaddress.ip_network(e["cidr"], strict=False)
                            self.subnets.append((net, e))
                        except Exception:
                            continue
            except Exception:
                pass

        # Country code to full name mapping
        self.country_names = {
            "US": "United States",
            "DE": "Germany",
            "NL": "Netherlands",
            "RU": "Russia",
            "IN": "India",
            "CH": "Switzerland",
            "SG": "Singapore",
            "PA": "Panama",
            "AU": "Australia",
            "GB": "United Kingdom",
            "CA": "Canada",
            "CN": "China",
            "HK": "Hong Kong",
            "SC": "Seychelles",
            "VG": "British Virgin Islands",
            "UNKNOWN": "Unknown Jurisdiction"
        }

    def lookup(self, ip_str: str) -> Dict[str, Any]:
        """
        Completely offline lookup. Resolves IP to Country, Country Name, ASN, and Organization.
        If IP matches known offline subnets, uses exact match.
        Otherwise, uses deterministic heuristic mapping based on IPv4 octets.
        """
        if not ip_str or ip_str in ("127.0.0.1", "localhost", "::1"):
            return {
                "ip": ip_str or "127.0.0.1",
                "country": "US",
                "country_name": "Localhost / Internal",
                "asn": "AS0",
                "org": "Internal Loopback"
            }

        try:
            ip_obj = ipaddress.ip_address(ip_str)
            # Check exact CIDR matches
            for net, meta in self.subnets:
                if ip_obj in net:
                    return {
                        "ip": ip_str,
                        "country": meta["country"],
                        "country_name": meta.get("country_name", self.country_names.get(meta["country"], "Unknown")),
                        "asn": meta["asn"],
                        "org": meta.get("org", "Offline ASN")
                    }

            # Deterministic fallback mapping for unlisted IP ranges based on first/second octet
            if isinstance(ip_obj, ipaddress.IPv4Address):
                octets = ip_obj.exploded.split(".")
                first = int(octets[0])
                second = int(octets[1])
                hash_val = (first * 31 + second) % 10

                fallback_map = [
                    {"country": "US", "asn": "AS16509", "org": "Amazon Web Services"},
                    {"country": "DE", "asn": "AS24940", "org": "Hetzner Online"},
                    {"country": "NL", "asn": "AS49981", "org": "WorldStream B.V."},
                    {"country": "CH", "asn": "AS12345", "org": "Swiss Privacy Relays"},
                    {"country": "SG", "asn": "AS55555", "org": "SingTel Relays"},
                    {"country": "IN", "asn": "AS13335", "org": "Cloudflare India"},
                    {"country": "RU", "asn": "AS48282", "org": "Hostkey B.V."},
                    {"country": "PA", "asn": "AS99999", "org": "Offshore Privacy Services"},
                    {"country": "GB", "asn": "AS2856", "org": "BT Public Internet"},
                    {"country": "SC", "asn": "AS88888", "org": "Seychelles Hosting Ltd"}
                ]
                chosen = fallback_map[hash_val]
                return {
                    "ip": ip_str,
                    "country": chosen["country"],
                    "country_name": self.country_names.get(chosen["country"], "Unknown"),
                    "asn": chosen["asn"],
                    "org": chosen["org"]
                }
        except ValueError:
            pass

        return {
            "ip": ip_str,
            "country": "UNKNOWN",
            "country_name": "Unknown Jurisdiction",
            "asn": "AS_UNKNOWN",
            "org": "Unknown Organization"
        }

offline_geoip = OfflineGeoIP()
