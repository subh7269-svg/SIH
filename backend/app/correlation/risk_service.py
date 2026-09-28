"""
Explainable Investigation Lead Prioritization Service.
IMPORTANT FORENSIC ETHICS NOTICE:
This system produces an 'Investigation Lead Prioritization Score' (0 - 100).
It does NOT establish criminal guilt or replace human investigator analysis.
Every flagged score includes transparent, human-readable evidence justification.
"""
from typing import Dict, Any, List, Tuple
from backend.app.correlation.config import correlation_settings

class RiskService:
    """
    Calculates explainable risk scores and human-auditable evidence justifications.
    """
    def __init__(self, settings=correlation_settings):
        self.cfg = settings

    def calculate_investigation_lead(
        self,
        txid: str,
        features: Dict[str, Any],
        tx_class: str,
        network_info: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Evaluates risk score (0-100), priority tier, and structured evidence list.
        """
        score = 0
        evidence: List[str] = []

        fan_in = features.get("fan_in", 0)
        fan_out = features.get("fan_out", 0)
        amount = features.get("transaction_amount", 0.0)
        fee = features.get("fee", 0.0)
        wallet_count = features.get("wallet_count", 0)
        net_conf = features.get("network_confidence", 0.0)
        time_diff = network_info.get("time_difference_seconds")
        method = network_info.get("correlation_method", "none")

        # 1. High fan-in (+15)
        if fan_in >= self.cfg.HIGH_FAN_IN_THRESHOLD:
            pts = self.cfg.WEIGHT_HIGH_FAN_IN
            score += pts
            evidence.append(f"+{pts} High fan-in: Aggregated from {fan_in} input sources (threshold >= {self.cfg.HIGH_FAN_IN_THRESHOLD})")

        # 2. High fan-out (+15)
        if fan_out >= self.cfg.HIGH_FAN_OUT_THRESHOLD:
            pts = self.cfg.WEIGHT_HIGH_FAN_OUT
            score += pts
            evidence.append(f"+{pts} High fan-out: Peeling/splitting across {fan_out} output addresses (threshold >= {self.cfg.HIGH_FAN_OUT_THRESHOLD})")

        # 3. Large transaction amount (+15)
        if amount >= self.cfg.VERY_LARGE_TRANSACTION_THRESHOLD:
            pts = self.cfg.WEIGHT_LARGE_TRANSACTION + 5
            score += pts
            evidence.append(f"+{pts} Very large transaction: {amount:.2f} BTC moved (exceeds {self.cfg.VERY_LARGE_TRANSACTION_THRESHOLD} BTC)")
        elif amount >= self.cfg.LARGE_TRANSACTION_THRESHOLD:
            pts = self.cfg.WEIGHT_LARGE_TRANSACTION
            score += pts
            evidence.append(f"+{pts} Large transaction: {amount:.2f} BTC moved (threshold >= {self.cfg.LARGE_TRANSACTION_THRESHOLD} BTC)")

        # 4. Strong network correlation (+25)
        if net_conf >= self.cfg.NETWORK_CONFIDENCE_THRESHOLD:
            pts = self.cfg.WEIGHT_STRONG_NETWORK
            score += pts
            diff_str = f"{time_diff:.1f}s" if time_diff is not None else "exact"
            evidence.append(
                f"+{pts} Strong network correlation: Confidence {net_conf:.2f} via {method} (time difference: {diff_str})"
            )
        elif method == "timestamp_window" and net_conf > 0.0:
            pts = 10
            score += pts
            evidence.append(f"+{pts} Moderate temporal network correlation: Confidence {net_conf:.2f}")

        # 5. Multiple connected wallets (+10)
        if wallet_count >= self.cfg.CONNECTED_WALLETS_THRESHOLD:
            pts = self.cfg.WEIGHT_MULTIPLE_WALLETS
            score += pts
            evidence.append(f"+{pts} Highly connected entity: {wallet_count} associated counterparties")

        # 6. Benchmark Class / High Fee Anomaly (+20)
        if str(tx_class).lower() in ("1", "illicit"):
            pts = self.cfg.WEIGHT_KNOWN_ILLICIT_CLASS
            score += pts
            evidence.append(f"+{pts} Known illicit category label in benchmark forensic dataset")
        elif fee >= self.cfg.HIGH_FEE_THRESHOLD:
            pts = 10
            score += pts
            evidence.append(f"+{pts} Anomalous high transaction fee: {fee:.6f} BTC")

        # Normalize score 0 - 100
        score = min(100, max(0, score))

        # Assign Priority
        if score >= 70:
            priority = "HIGH"
        elif score >= 40:
            priority = "MEDIUM"
        else:
            priority = "LOW"

        if not evidence:
            evidence.append("Standard transaction profile within normal baseline operating bounds")

        return {
            "txid": txid,
            "risk_score": score,
            "priority": priority,
            "evidence": evidence,
            "evidence_text": " | ".join(evidence)
        }
