# LeadForge: Transaction?Wallet?Network Correlation Engine
### Smart India Hackathon 2026 ? Problem Statement SIH26146
#### Industry-Ready Offline Cryptocurrency Forensic Analysis Platform

> **IMPORTANT FORENSIC & ETHICAL NOTICE**:  
> LeadForge is an investigative analytics and anomaly-prioritization platform. It generates:  
> **"Potential anomaly / investigation lead requiring human verification"**  
> LeadForge does **NOT** claim that any wallet, transaction, or individual is criminal. Furthermore, network observations are reported as:  
> **"network observation temporally correlated with transaction"** rather than claiming *"IP belongs to wallet."*

---

## 1. Executive Summary & Engine Objective

The **LeadForge Correlation Engine** bridges the critical visibility gap between blockchain-layer transactions and network-layer wire observations. In modern cryptocurrency forensics, sophisticated entities obscure fund flows across peeling chains and mixers. By synthesizing:
1. **Blockchain Transactions** (`txs_features.csv`, `txs_classes.csv`),
2. **Entity & Wallet Graphs** (`wallets_features.csv`, `wallets_classes.csv`, `AddrTx_edgelist.csv`, `TxAddr_edgelist.csv`), and
3. **P2P Wire Broadcast Metadata** (`network_data.csv`),

LeadForge extracts multi-dimensional behavioral, graph, and network features, computes unsupervised Isolation Forest anomaly scores, and generates transparent, explainable investigation leads (0?100) with concrete evidence justifications for law enforcement and forensic investigators.

---

## 2. Dataset Structure

The platform is designed to ingest the **Elliptic++** dataset and related P2P capture datasets:

| File Name | Description | Size / Scale | Key Columns |
| :--- | :--- | :--- | :--- |
| `txs_features.csv` | Transaction features, amounts, fees, degrees | ~662.6 MB (184 cols) | `txId`, `Time step`, `fees`, `total_BTC`, `in_txs_degree`, `out_txs_degree` |
| `txs_classes.csv` | Ground-truth benchmark transaction labels | ~2.3 MB | `txId`, `class` (1: illicit, 2: licit, 3: unknown) |
| `AddrTx_edgelist.csv` | Input wallet address to transaction mapping | ~21.2 MB | `input_address`, `txId` |
| `TxAddr_edgelist.csv` | Transaction to output wallet address mapping | ~36.7 MB | `txId`, `output_address` |
| `wallets_classes.csv` | Known entity/wallet classifications | ~30.4 MB | `address`, `class` |
| `wallets_features.csv` | Aggregated wallet-level historical behaviors | ~578.4 MB | `address`, `total_txs`, degrees, transaction velocity |
| `network_data.csv` | P2P network broadcast observations | Configurable | `timestamp`, `src_ip`, `src_port`, `dst_ip`, `dst_port`, `txid` |

---

## 3. How Transaction Data Is Processed

### Chunked Streaming & Dynamic Column Detection
`txs_features.csv` is ~662.6 MB and cannot be loaded entirely into RAM on evaluation laptops. LeadForge implements streaming generators:
```python
pd.read_csv(file, chunksize=50000, low_memory=False)
```
- **Dynamic Column Aliases**: The engine automatically detects column variations:
  - `txid` / `tx_id` / `transaction_id` / `txId`
  - `timestamp` / `time` / `datetime` / `Time step`
  - `fee` / `fees` / `transaction_fee`
  - `input_addresses` / `inputs` (or resolved via edgelists)
  - `input_amounts` / `total_BTC` / `amount`
- **Safe Parsing & Degree Derivation**: Safely handles nulls, brackets (`"['addr1', 'addr2']"`), comma-separated strings, and numeric floats. Computes `fan_in`, `fan_out`, `total_input_amount`, and `amount_per_output = total_input_amount / max(1, output_count)`.

---

## 4. How Wallet Correlation Works

The `WalletCorrelator` builds fast in-memory hash indices from:
- `AddrTx_edgelist.csv`: Maps `input_address` $	o$ `txId`
- `TxAddr_edgelist.csv`: Maps `txId` $	o$ `output_address`
- `txs_classes.csv` & `wallets_classes.csv`: Maps identifiers to labels (`illicit`, `licit`, `unknown`)

For every transaction, LeadForge:
1. Gathers all input addresses and output addresses (merging inline CSV columns and edgelists).
2. Deduplicates all addresses to eliminate double counting.
3. Retrieves known entity classification tags.
4. Returns: `input_wallets`, `output_wallets`, `related_wallets`, `wallet_classes`, and `wallet_count`.

---

## 5. How Network Correlation Works

The `NetworkCorrelator` maps blockchain activity to physical network wire broadcasts (`network_data.csv`):
1. **Tier 1: Exact TXID Match**:
   - If `txid` is present in the network packet capture, LeadForge performs an $O(1)$ hash map lookup.
   - Exact match establishes `network_confidence = 1.0` and `correlation_method = "exact_txid"`.
2. **Tier 2: Temporal Proximity Window (When TXID Is Not in Packet)**:
   - When Bitcoin nodes relay unconfirmed transactions, intermediate routers or network sensors capture traffic without application-layer TXIDs.
   - LeadForge stores sorted network observation epochs and executes an $O(\log N)$ binary search (`bisect_left`/`bisect_right`) within $\pm 120$ seconds (`CORRELATION_TIME_WINDOW_SECONDS`).
   - Identifies the temporally closest observation.
3. **Forensic Integrity**: Never assumes IP ownership of a private key. Outputs:  
   `"network observation temporally correlated with transaction"`.

---

## 6. How Timestamp Matching Works

Timestamps in cryptocurrency datasets can be:
- ISO 8601 strings (`2026-08-20T10:18:00+00:00`),
- Unix epoch integers (`1787221080`), or
- Discrete time steps (e.g. Elliptic step $1 \dots 49$, where step 1 represents $10,800$ epoch seconds).

The engine parses all formats into normalized float epoch seconds, calculates the exact time difference:
$$\Delta t = |t_{	ext{tx}} - t_{	ext{net}}|$$

---

## 7. How Confidence Is Calculated

Confidence decays linearly with temporal distance within the observation window $W$ ($120$s default):
$$	ext{Confidence} = \max\left(0.0,\, 1.0 - rac{\Delta t}{W}
ight)$$

- At $\Delta t = 0	ext{s}$: $	ext{Confidence} = 1.0$ (Peak correlation)
- At $\Delta t = 30	ext{s}$: $	ext{Confidence} = 1.0 - rac{30}{120} = 0.75$
- At $\Delta t = 90	ext{s}$: $	ext{Confidence} = 1.0 - rac{90}{120} = 0.25$
- At $\Delta t \ge 120	ext{s}$: $	ext{Confidence} = 0.0$ (No correlation)

---

## 8. How Investigation Scores Work & Explainability

LeadForge implements an **Explainable Investigation Lead Prioritization Score** ($0$?$100$):
> The system **never** outputs only `Risk = 78`. It outputs explicit evidence justifications.

### Transparent Evidence Weights (Configurable in `config.py`):
| Factor | Condition / Threshold | Points |
| :--- | :--- | :---: |
| High Fan-In | $\ge 4$ inputs aggregated | **+15** |
| High Fan-Out | $\ge 4$ output peeling/splits | **+15** |
| Large Transaction | $\ge 10.0$ BTC (or $+20$ if $\ge 50$ BTC) | **+15** |
| Strong Network Correlation | Network confidence $\ge 0.50$ | **+25** |
| Multiple Connected Wallets | Connected counterparties $\ge 5$ | **+10** |
| Known Illicit Benchmark Tag | Benchmark class `1` / `illicit` | **+20** |
| High Fee Anomaly | Miner fee $\ge 0.01$ BTC | **+10** |

### Priority Classification:
- **LOW**: $0$ ? $39$
- **MEDIUM**: $40$ ? $69$
- **HIGH**: $70$ ? $100$

---

## 9. Heterogeneous Graph Generation

The `GraphService` generates multi-relational graphs exported to `graph_edges.csv`:
```
source,target,source_type,target_type,relationship
wallet_1,tx_999,wallet,transaction,input_to
tx_999,wallet_2,transaction,wallet,output_to
198.51.100.24,tx_999,ip,transaction,network_observation
```
The REST API provides interactive subgraphs compatible with **Cytoscape.js** and **D3.js** supporting $k$-hop expansion ($1, 2, 3$).

---

## 10. Machine Learning Anomaly Detection

- Model: Scikit-learn `IsolationForest(n_estimators=100, contamination=0.05)`
- Scaler: `RobustScaler` to handle heavy-tailed Bitcoin amounts and high degrees
- Artifacts: Saved to `models/isolation_forest.joblib` and `models/scaler.joblib`
- Features: `fan_in`, `fan_out`, `transaction_amount`, `fee`, `wallet_count`, `network_confidence`, `time_difference_seconds`, `degree`, `unique_counterparties`.
- Output: `ml_anomaly_score` ($0.0$ to $1.0$) and `ml_anomaly_label` ($-1$ for outlier, $1$ for inlier).

---

## 11. How to Add `network_data.csv`

Place your `network_data.csv` in any of the search locations:
1. `C:\Users\ASUS\Desktop\SIHH\network_data.csv`
2. `backend/../data/correlation/network_data.csv`

### Expected CSV Format:
```csv
timestamp,src_ip,src_port,dst_ip,dst_port,txid
2026-08-20T10:18:00Z,198.51.100.24,8333,104.244.42.1,8333,3321
2026-08-20T10:18:25Z,185.220.101.5,9050,192.0.2.78,8333,
```
*Note: If `txid` is blank, temporal proximity matching automatically engages.*

---

## 12. How to Run the System

### A. Run Automated Pytest Suite
```bash
$env:PYTHONPATH="."
python -m pytest backend/tests/test_correlation_engine.py -v
```

### B. Start FastAPI Backend
```bash
$env:PYTHONPATH="."
python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000 --reload
```
Swagger UI: `http://127.0.0.1:8000/docs`

### C. Start Frontend Dashboard
```bash
cd frontend
npm run dev
```
Open: `http://localhost:5173/correlation`

---

## 13. REST API Endpoints

| Method | Path | Description |
| :--- | :--- | :--- |
| `POST` | `/api/correlation/run` | Triggers background correlation pipeline |
| `GET` | `/api/correlation/status` | Live status, progress percentage, metrics |
| `GET` | `/api/correlation/status/{job_id}` | Status of a specific job |
| `GET` | `/api/correlation/validation-report` | Schema and integrity validation report |
| `GET` | `/api/investigations` | Filterable ranked leads (`priority`, `minimum_score`, etc.) |
| `GET` | `/api/investigations/{txid}` | Complete forensic brief with evidence list |
| `GET` | `/api/transactions/{txid}` | Raw blockchain transaction details |
| `GET` | `/api/transactions/{txid}/correlations` | Wallet & network correlation breakdown |
| `GET` | `/api/graph/{txid}?hops=1` | Cytoscape.js heterogeneous link graph |

---

## 14. Example API Responses

### `POST /api/correlation/run` Response
```json
{
  "job_id": "corr_20260917_230131_8f1a",
  "status": "started",
  "message": "Correlation processing started in background thread."
}
```

### `GET /api/investigations/89273` Response
```json
{
  "txid": "89273",
  "risk_score": 60,
  "priority": "MEDIUM",
  "evidence": [
    "+15 High fan-out: Peeling/splitting across 288 output addresses (threshold >= 4)",
    "+20 Very large transaction: 852.16 BTC moved (exceeds 50.0 BTC)",
    "+25 Strong network correlation: Confidence 1.00 via exact_txid (time difference: exact)"
  ],
  "transaction_information": {
    "timestamp": 1,
    "amount": 852.16467964,
    "fee": 0.0,
    "tx_class": "unknown",
    "fan_in": 1,
    "fan_out": 288,
    "script_type": "P2PKH"
  },
  "network_correlation": {
    "src_ip": "198.51.100.24",
    "src_port": 8333,
    "dst_ip": "104.244.42.1",
    "dst_port": 8333,
    "correlation_method": "exact_txid",
    "network_confidence": 1.0
  },
  "ml_anomaly_information": {
    "ml_anomaly_score": 0.6582,
    "ml_anomaly_label": -1,
    "model": "IsolationForest"
  }
}
```

---

## 15. Limitations & Future Roadmap

1. **Network Wire Directionality**: Relaying nodes observe transaction announcements via Bitcoin P2P `inv` messages. Proximity indicates broadcast propagation path, not sender identity.
2. **Tor / VPN Anonymity**: Transactions broadcast via Tor exit relays show Tor IP addresses. Future versions will integrate Tor exit node consensus lists.
3. **Graph Scaling**: Browser-based Cytoscape graphs render up to ~1,500 nodes smoothly; larger graphs use server-side degree pruning.
