# TraceX — AI-Powered Bitcoin Transaction Investigation & Risk Intelligence Platform

[![Smart India Hackathon 2026](https://img.shields.io/badge/SIH-2026%20Problem%20SIH26146-10B981?style=for-the-badge)](https://sih.gov.in)
[![Offline Ready](https://img.shields.io/badge/Mode-100%25%20Offline%20First-06B6D4?style=for-the-badge)](OFFLINE_SETUP.md)
[![ML Anomaly Detection](https://img.shields.io/badge/ML-Isolation%20Forest%20%2B%20LOF-8B5CF6?style=for-the-badge)](docs/ml.md)
[![Graph Intelligence](https://img.shields.io/badge/Graph-NetworkX%20%2B%20Cytoscape-F59E0B?style=for-the-badge)](docs/graph.md)
[![Tests Passing](https://img.shields.io/badge/Tests-16%2F16%20Passing-10B981?style=for-the-badge)](backend/tests/)

> **IMPORTANT FORENSIC & ETHICAL NOTICE**:  
> TraceX is an investigative analytics and anomaly-detection system. It identifies anomalous entities and generates prioritized investigative leads based on available Bitcoin network and blockchain metadata.  
> **TraceX does NOT claim to prove criminal guilt, establish definitive wallet ownership from network IP observations, or replace human investigator judgment.**

---

## 1. Executive Summary

TraceX addresses **Smart India Hackathon 2026 Problem Statement SIH26146**. It is an **offline Linux-compatible investigative intelligence platform** designed for cybersecurity analysts, forensic accountants, and law enforcement agencies.

### What TraceX Does:
1. **Bulk Ingestion**: Streams and parses bulk Bitcoin transaction and P2P network metadata in **CSV, JSON, and XML** formats.
2. **Offline GeoIP & ASN Resolution**: Local in-memory subnet classification mapping relay IPs to Countries and Autonomous System Numbers without external network calls.
3. **Multi-Layer Correlation**: Correlates blockchain-layer transactions (TXID, inputs, outputs, amounts, fees, scripts) with network-layer wire broadcast observations (IP, port, ASN, GeoIP) while preserving provenance.
4. **Heterogeneous Entity Graph**: Constructs an in-memory graph connecting `WALLET`, `TRANSACTION`, `IP`, `ASN`, and `COUNTRY` entities.
5. **Feature Engineering**: Extracts 20+ behavioral, topological, and network dispersion signals (transaction velocity, burst rate, counterparty diversity, fan-in/fan-out ratios, jurisdictional entropy).
6. **Genuine Machine Learning**: Trains and benchmarks `IsolationForest` against `LocalOutlierFactor` with automated ROC-AUC, PR-AUC, and F1 calculation against synthetic ground-truth benchmark scenarios.
7. **DBSCAN Entity Clustering**: Groups behaviorally correlated entities into structured cohorts.
8. **Deterministic Risk Prioritization**: Computes a transparent composite score (0–100) separating raw ML anomaly scores from domain-weighted investigation priority.
9. **Mathematical Explainability**: Explains why every entity was flagged using empirical $z$-score deviations against population medians.
10. **Interactive Visual Link Analysis**: Rich Cytoscape.js workspace supporting k-hop expansion, path tracing, and layout switching.
11. **Forensic Report Generator**: Generates print-ready forensic lead briefs with complete provenance and compliance disclaimers.
12. **1-Click Deterministic Demo**: Built-in demo harness executing the entire pipeline in < 10 seconds.

---

## 2. Technology Stack

- **Frontend**: React 18, TypeScript, Vite, Tailwind CSS, Cytoscape.js, Recharts, TanStack Query, Lucide Icons.
- **Backend**: Python 3.13, FastAPI (OpenAPI v3), Pydantic v2, SQLAlchemy 2.0 ORM.
- **Data & ML**: Pandas, NumPy, Scikit-learn (`IsolationForest`, `LocalOutlierFactor`, `DBSCAN`, `RobustScaler`), NetworkX, Joblib.
- **Persistence**: SQLite (Embedded zero-setup mode) / PostgreSQL (Docker mode).
- **Deployment**: Multi-stage Linux-compatible Docker & Docker Compose.

---

## 3. Quick Start Guide

### Prerequisites
- Python 3.10+
- Node.js 18+ (npm 9+)

### Step 1: Clone and Install Backend
```bash
# 1. Install Python dependencies
pip install -r backend/requirements.txt
```

### Step 2: Install Frontend
```bash
cd frontend
npm install
cd ..
```

### Step 3: Launch TraceX
```bash
# Windows
scripts\run_local.bat

# Linux / macOS
chmod +x scripts/run_local.sh
./scripts/run_local.sh
```

- Open **`http://localhost:5173`** in your browser.
- Backend API & Swagger documentation is available at **`http://127.0.0.1:8000/docs`**.

---

## 4. 1-Click SIH 2026 Demo Walkthrough

1. Open `http://localhost:5173`.
2. Click the glowing **"Run 1-Click SIH Demo"** button in the top navigation bar.
3. TraceX will:
   - Ingest the synthetic benchmark dataset.
   - Run the offline GeoIP correlator.
   - Build the heterogeneous entity graph.
   - Extract 20+ dimensional feature vectors.
   - Fit the Isolation Forest and LOF baseline models.
   - Run DBSCAN entity clustering.
   - Generate ranked, explainable investigative alerts.
4. Inspect the top anomalous entity (`bc1q_peel_chain_alpha_...`), view the feature deviation radar, trace the 2-hop transaction flow in Cytoscape, and click **"Export Lead Report"**.

---

## 5. Docker Deployment

```bash
docker compose up --build -d
```
Access the application at `http://localhost:8000`.

---

## 6. Automated Test Suite

TraceX includes comprehensive unit and integration tests covering ingestion, parsing, correlation, feature extraction, ML models, graph queries, and REST APIs:

```bash
python -m pytest backend/tests -v
```

```
======================= 16 passed, 8 warnings in 2.88s ========================
```

---

## 7. Project Structure

```
SIH/
├── backend/
│   ├── app/
│   │   ├── api/v1/          # REST API endpoints (datasets, entities, graph, models, alerts, demo)
│   │   ├── core/            # Config, security, logging, errors
│   │   ├── db/              # SQLAlchemy Base & Session
│   │   ├── geoip/           # 100% Offline GeoIP & ASN lookup engine
│   │   ├── graph/           # NetworkX MultiDiGraph builder & k-hop queries
│   │   ├── ingestion/       # CSV, JSON, XML parsers, validators, normalizers, DQ analyzer
│   │   ├── ml/              # Isolation Forest, LOF, DBSCAN, Evaluation, Features
│   │   ├── models/          # SQLAlchemy ORM models
│   │   ├── risk/            # Deterministic 0-100 composite risk scorer
│   │   ├── explainability/  # Population baseline deviation explainer
│   │   ├── schemas/         # Pydantic validation schemas
│   │   ├── services/        # Service layer orchestrators
│   │   └── main.py          # FastAPI application entrypoint
│   ├── tests/               # 16 unit and integration test suites
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── components/      # CytoscapeGraph, RiskGauge, StatCard, ReasoningCard, Navbar, Sidebar
│   │   ├── pages/           # Dashboard, Datasets, Alerts, Search, Dossier, Graph, Clusters, Models, Reports
│   │   ├── services/        # Typed API client
│   │   ├── types/           # TypeScript domain interfaces
│   │   ├── App.tsx          # React Router & Query Provider
│   │   └── main.tsx
│   ├── package.json
│   ├── vite.config.ts
│   └── tailwind.config.js
├── data/sample/             # Benchmark synthetic datasets (CSV, JSON, XML)
├── docs/                    # Technical & architectural specifications
├── scripts/                 # Synthetic data generator & local runner scripts
├── docker-compose.yml       # Multi-container production compose
├── Dockerfile               # Linux-compatible multi-stage container
├── OFFLINE_SETUP.md         # Air-gapped deployment guide
└── README.md
```

---

## 8. Limitations & Ethical Considerations

1. **Synthetic vs Real-World Distribution**: This prototype uses synthetic benchmark datasets modeled on Bitcoin P2P and transaction structures. Real-world darknet or mixer patterns may require larger parameter tuning.
2. **Network Observation vs Ownership**: An IP address observed broadcasting a transaction may be a relay node, VPN, or Tor exit. TraceX records this as broadcast provenance, not proof of wallet ownership.
3. **Anomaly ≠ Crime**: An outlier score indicates statistical deviation from baseline traffic, serving as a prioritized lead for human investigator review.

---

## 9. License & Compliance
Built strictly for Smart India Hackathon 2026 (Problem Statement SIH26146). All code is modular, type-safe, open, and offline-compatible.
