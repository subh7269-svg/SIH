import numpy as np
import pandas as pd
from typing import Dict, Any, List, Tuple

class ExplainabilityEngine:
    def __init__(self):
        self.baseline_stats: Dict[str, Dict[str, float]] = {}

    def compute_population_baselines(self, feature_df: pd.DataFrame):
        """
        Computes mean, median, standard deviation, and 90th percentile baselines
        across all entities in the dataset.
        """
        self.baseline_stats = {}
        for col in feature_df.columns:
            series = pd.to_numeric(feature_df[col], errors="coerce").fillna(0.0)
            self.baseline_stats[col] = {
                "mean": float(series.mean()),
                "median": float(series.median()),
                "std": float(series.std()) if len(series) > 1 and series.std() > 0 else 1.0,
                "p90": float(series.quantile(0.90)),
                "min": float(series.min()),
                "max": float(series.max())
            }

    def explain_entity(
        self,
        entity_id: str,
        features: Dict[str, Any],
        anomaly_score: float,
        priority_score: int
    ) -> Tuple[List[str], Dict[str, Any]]:
        """
        Generates explainable mathematical reasoning for why an entity was flagged.
        Returns:
          (reasons: List[str], deviation_details: Dict[str, Any])
        """
        reasons: List[str] = []
        deviation_details: Dict[str, Any] = {}

        # If no baseline calculated yet, return standard heuristic reasons
        if not self.baseline_stats:
            vel = float(features.get("tx_velocity_per_hour", 0.0))
            if vel > 4.0:
                reasons.append(f"High transaction frequency ({vel:.1f} tx/hr)")
            peers = int(features.get("unique_counterparties", 0))
            if peers > 10:
                reasons.append(f"Large counterparty network ({peers} distinct peers)")
            ips = int(features.get("unique_observed_ips", 0))
            if ips > 3:
                reasons.append(f"Dispersed network relay observations ({ips} unique IPs)")
            if not reasons:
                reasons.append("Elevated multivariate statistical anomaly score.")
            return reasons, deviation_details

        ranked_deviations = []
        for feat_name, val in features.items():
            if feat_name not in self.baseline_stats:
                continue
            try:
                num_val = float(val)
            except Exception:
                continue

            base = self.baseline_stats[feat_name]
            std = base["std"] if base["std"] > 1e-6 else 1.0
            z_score = (num_val - base["mean"]) / std
            ratio_to_median = num_val / max(0.0001, base["median"])

            deviation_details[feat_name] = {
                "value": round(num_val, 4),
                "baseline_mean": round(base["mean"], 4),
                "baseline_median": round(base["median"], 4),
                "baseline_p90": round(base["p90"], 4),
                "z_score": round(z_score, 2),
                "ratio_to_median": round(ratio_to_median, 2)
            }

            if z_score > 1.2:
                ranked_deviations.append((feat_name, num_val, base, z_score, ratio_to_median))

        # Sort by highest z-score
        ranked_deviations.sort(key=lambda x: x[3], reverse=True)

        for feat_name, val, base, z_score, ratio in ranked_deviations[:4]:
            if feat_name == "tx_velocity_per_hour":
                reasons.append(f"Transaction velocity ({val:.1f} tx/hr) is {ratio:.1f}x higher than population median ({base['median']:.1f} tx/hr).")
            elif feat_name == "unique_counterparties":
                reasons.append(f"Connected to {int(val)} counterparties, significantly exceeding typical baseline ({int(base['median'])} peers).")
            elif feat_name == "unique_observed_ips":
                reasons.append(f"Observed broadcasting across {int(val)} distinct IP addresses (population normal: {int(base['median'])}).")
            elif feat_name == "unique_asns":
                reasons.append(f"Associated with transactions routed through {int(val)} autonomous systems (ASNs).")
            elif feat_name == "unique_countries":
                reasons.append(f"Transaction broadcast observed in {int(val)} geographic jurisdictions.")
            elif feat_name == "avg_time_between_txs_sec" and val < base["median"] * 0.2:
                reasons.append(f"Extremely rapid inter-transaction intervals ({val:.0f}s vs {base['median']:.0f}s baseline), characteristic of automated peeling chains.")
            elif feat_name == "graph_degree":
                reasons.append(f"Unusually high topological graph connectivity (Degree: {int(val)} vs {base['median']:.1f} average).")
            elif feat_name == "foreign_geo_entropy":
                reasons.append(f"High jurisdictional entropy ({val:.2f}) indicating intentional multi-country network dispersal.")
            else:
                reasons.append(f"Elevated {feat_name.replace('_', ' ')}: {val:.2f} (z-score: +{z_score:.1f}).")

        if not reasons:
            reasons.append(f"Multivariate Isolation Forest anomaly score: {anomaly_score:.2f} (investigation priority: {priority_score}/100).")

        return reasons, deviation_details

explainer_engine = ExplainabilityEngine()
