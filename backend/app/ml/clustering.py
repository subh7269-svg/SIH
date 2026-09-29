import gc
import logging
import numpy as np
import pandas as pd
from typing import Dict, Any, List
from sklearn.cluster import DBSCAN
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import pairwise_distances_argmin_min

logger = logging.getLogger(__name__)

# Maximum entities for full DBSCAN; larger datasets are subsampled to avoid O(n²) memory
MAX_DBSCAN_SAMPLES = 15_000


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

        For large datasets (> MAX_DBSCAN_SAMPLES), a representative subsample is clustered
        and remaining entities are assigned to the nearest cluster centroid to avoid
        excessive memory usage from pairwise distance computations.
        """
        if len(X) < 2:
            return []

        X_clean = X.replace([np.inf, -np.inf], np.nan).fillna(0.0)
        X_scaled = self.scaler.fit_transform(X_clean)

        entity_ids = list(X.index)
        n_total = len(X_scaled)
        sampled = False

        if n_total > MAX_DBSCAN_SAMPLES:
            logger.info(
                f"[CLUSTERING] Dataset has {n_total} entities — subsampling to "
                f"{MAX_DBSCAN_SAMPLES} for DBSCAN, then assigning rest via nearest centroid"
            )
            rng = np.random.RandomState(42)
            sample_idx = np.sort(rng.choice(n_total, MAX_DBSCAN_SAMPLES, replace=False))
            X_sample = X_scaled[sample_idx]
            sampled = True
        else:
            X_sample = X_scaled
            sample_idx = np.arange(n_total)

        self.model = DBSCAN(
            eps=self.eps,
            min_samples=self.min_samples,
            algorithm='ball_tree',
            leaf_size=50
        )
        sample_labels = self.model.fit_predict(X_sample)

        if sampled:
            # Start with all noise, then fill in sampled points
            labels = np.full(n_total, -1, dtype=int)
            labels[sample_idx] = sample_labels

            unique_cluster_labels = set(sample_labels)
            unique_cluster_labels.discard(-1)

            if unique_cluster_labels:
                # Compute centroids for each discovered cluster
                centroids = np.array([
                    X_sample[sample_labels == lbl].mean(axis=0)
                    for lbl in sorted(unique_cluster_labels)
                ])
                centroid_labels = np.array(sorted(unique_cluster_labels))

                # Identify unassigned entities
                remaining_mask = np.ones(n_total, dtype=bool)
                remaining_mask[sample_idx] = False
                remaining_idx = np.where(remaining_mask)[0]

                if len(remaining_idx) > 0:
                    X_remaining = X_scaled[remaining_idx]
                    # Process in chunks to keep memory bounded
                    chunk_size = 5000
                    for i in range(0, len(remaining_idx), chunk_size):
                        chunk = X_remaining[i:i + chunk_size]
                        nearest, dists = pairwise_distances_argmin_min(chunk, centroids)
                        for j, (nn_idx, dist) in enumerate(zip(nearest, dists)):
                            # Assign to cluster if within generous distance; else noise
                            if dist <= self.eps * 3:
                                labels[remaining_idx[i + j]] = centroid_labels[nn_idx]
                    del X_remaining
                del centroids
                gc.collect()

            logger.info(
                f"[CLUSTERING] Sampling complete: {int((labels != -1).sum())}/{n_total} assigned to clusters"
            )
        else:
            labels = sample_labels

        del X_sample, X_scaled
        gc.collect()

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
