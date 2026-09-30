# LeadForge Machine Learning & Risk Prioritization Methodology

---

## 1. Machine Learning Anomaly Detection

### Problem Formulation
In offline forensic investigation, labeled historical ground truth for illegitimate activity is frequently incomplete or unavailable. Therefore, unsupervised and semi-supervised statistical outlier detection is the most scientifically sound methodology.

### Primary Algorithm: Isolation Forest
Isolation Forest isolates anomalies by randomly selecting a feature and randomly selecting a split value between the minimum and maximum values of the selected feature.
Because anomalous points require fewer recursive partitions to isolate in feature space compared to normal clusters, their average path length $h(x)$ across an ensemble of $t=100$ isolation trees is significantly shorter:

$$s(x, n) = 2^{-\frac{E(h(x))}{c(n)}}$$

Where $c(n)$ is the average path length of unsuccessful search in a Binary Search Tree (BST):
$$c(n) = 2\ln(n - 1) + 0.5772156649 - \frac{2(n - 1)}{n}$$

### Baseline Comparison: Local Outlier Factor (LOF)
To ensure rigorous validation without assuming model superiority, LeadForge benchmarks Isolation Forest against Local Outlier Factor (LOF). LOF measures the local density deviation of a given entity with respect to its $k=20$ nearest neighbors:

$$\text{LOF}_k(p) = \frac{\sum_{o \in N_k(p)} \frac{\text{lrd}_k(o)}{\text{lrd}_k(p)}}{|N_k(p)|}$$

---

## 2. Feature Engineering Space (20+ Dimensions)

| Dimension Category | Features | Description |
| :--- | :--- | :--- |
| **Temporal Dynamics** | `tx_velocity_per_hour`, `avg_time_between_txs_sec` | Burst frequency and inter-transaction hopping velocity. |
| **Volume Distribution** | `total_incoming_btc`, `total_outgoing_btc`, `avg_tx_amount`, `std_tx_amount`, `net_flow_btc` | Scale, variance, and net accumulation. |
| **Graph Topology** | `unique_counterparties`, `fan_in_ratio`, `fan_out_ratio`, `graph_degree`, `in_degree`, `out_degree` | Fan-out structuring and concentration patterns. |
| **Network Relaying** | `unique_observed_ips`, `unique_asns`, `unique_countries`, `foreign_geo_entropy` | Jurisdictional and autonomous system hopping. |

---

## 3. Deterministic Investigation Priority Score (0–100)

LeadForge strictly distinguishes the raw ML statistical anomaly score from the **Investigation Priority Score**:

$$\text{Priority Score} = \text{clamp}\Big( 0.40 \cdot S_{\text{ML}} + 0.20 \cdot S_{\text{Velocity}} + 0.15 \cdot S_{\text{Counterparties}} + 0.15 \cdot S_{\text{Network}} + 0.10 \cdot S_{\text{Graph}}, 0, 100 \Big)$$

---

## 4. Mathematical Explainability

For every generated alert, LeadForge computes the $z$-score deviation against population medians:

$$z_i = \frac{x_i - \mu_i}{\sigma_i}$$

Features with $z_i > 1.2$ are ranked and translated into human-readable evidence statements (e.g. *"Transaction velocity of 14.2 tx/hr is 6.2x higher than population median (2.3 tx/hr)"*).
