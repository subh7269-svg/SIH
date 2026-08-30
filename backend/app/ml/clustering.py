import numpy as np
import pandas as pd
from typing import Dict, Any, List
from sklearn.cluster import DBSCAN
from sklearn.preprocessing import StandardScaler

class EntityClusterer:
    def __init__(self, eps: float = 0.5, min_samples: int = 3):
        self.eps = eps
        self.min_samples = min_samples
        self.scaler = StandardScaler()
        self.model = None

    def fit_predict(self, X: pd.DataFrame) -> List[Dict[str, Any]]:
        """
        Executes DBSCAN clustering over normalized behavioral feature matrix.
        Returns a list of cluster metadata objects (cluster_label, name, member_ids, characteristics).
        """
        if len(X) < 2:
            return []

        X_clean = X.replace([np.inf, -np.inf], np.nan).fillna(0.0)
        X_scaled = self.scaler.fit_transform(X_clean)

        self.model = DBSCAN(eps=self.eps, min_samples=self.min_samples)
        labels = self.model.fit_predict(X_scaled)

        entity_ids = list(X.index)
        unique_labels = set(labels)

        clusters = []
        for lbl in unique_labels:
            mask = (labels == lbl)
            member_ids = [entity_ids[i] for i in range(len(entity_ids)) if mask[i]]
            sub_df = X.iloc[mask]

            if lbl == -1:
                name = "Noise / Outlier Group"
                desc = "Entities with isolated or non-conforming behavioral patterns."
            else:
                # Characterize cluster based on dominant features
                mean_velocity = float(sub_df["tx_velocity_per_hour"].mean()) if "tx_velocity_per_hour" in sub_df else 0.0
                mean_counterparties = float(sub_df["unique_counterparties"].mean()) if "unique_counterparties" in sub_df else 0.0
                mean_ips = float(sub_df["unique_observed_ips"].mean()) if "unique_observed_ips" in sub_df else 0.0

                if mean_velocity > 5.0 and mean_counterparties > 10:
                    name = f"Cluster {lbl}: High-Velocity Fan-Out Entities"
                elif mean_ips > 3:
                    name = f"Cluster {lbl}: Multi-IP Network Dispersal Cohort"
                elif mean_counterparties < 2:
                    name = f"Cluster {lbl}: Isolated Peer Transfer Chain"
                else:
                    name = f"Cluster {lbl}: Behaviorally Correlated Group"
                desc = f"Group of {len(member_ids)} entities exhibiting similar transaction velocity ({mean_velocity:.2f} tx/hr) and peer connectivity ({mean_counterparties:.1f} counterparties)."

            mean_characteristics = {
                col: round(float(sub_df[col].mean()), 4)
                for col in sub_df.columns
            }

            clusters.append({
                "cluster_label": int(lbl),
                "cluster_name": name,
                "description": desc,
                "member_count": len(member_ids),
                "member_ids": member_ids,
                "characteristics": mean_characteristics
            })

        return clusters
