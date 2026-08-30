from typing import Dict, Any, Tuple

def compute_deterministic_risk_score(
    anomaly_score: float,
    features: Dict[str, Any]
) -> Tuple[int, str, Dict[str, float]]:
    """
    Computes a deterministic, transparent composite investigation priority score (0-100)
    combining ML outlier score with behavioral, network, and graph domain signals.

    Returns:
      (priority_score: int [0-100], severity: str, subscores: dict)
    """
    # 1. ML Component (0-100)
    s_ml = min(100.0, max(0.0, float(anomaly_score) * 100.0))

    # 2. Velocity Component
    vel = float(features.get("tx_velocity_per_hour", 0.0))
    s_vel = min(100.0, (vel / 8.0) * 100.0)

    # 3. Counterparty Concentration/Fan-out Component
    counterparties = float(features.get("unique_counterparties", 0.0))
    s_counterparties = min(100.0, (counterparties / 20.0) * 100.0)

    # 4. Network & Geo Dispersal Component
    ips = float(features.get("unique_observed_ips", 0.0))
    asns = float(features.get("unique_asns", 0.0))
    countries = float(features.get("unique_countries", 0.0))
    s_network = min(100.0, (ips * 15.0) + (asns * 15.0) + (countries * 10.0))

    # 5. Graph Connectivity Component
    degree = float(features.get("graph_degree", 0.0))
    s_graph = min(100.0, (degree / 25.0) * 100.0)

    # Weighted Composite
    raw_composite = (
        0.40 * s_ml +
        0.20 * s_vel +
        0.15 * s_counterparties +
        0.15 * s_network +
        0.10 * s_graph
    )
    final_score = int(min(100, max(0, round(raw_composite))))

    # Determine severity
    if final_score >= 80:
        severity = "CRITICAL"
    elif final_score >= 60:
        severity = "HIGH"
    elif final_score >= 35:
        severity = "MEDIUM"
    else:
        severity = "LOW"

    subscores = {
        "ml_score": round(s_ml, 1),
        "velocity_score": round(s_vel, 1),
        "counterparty_score": round(s_counterparties, 1),
        "network_score": round(s_network, 1),
        "graph_score": round(s_graph, 1)
    }

    return final_score, severity, subscores
