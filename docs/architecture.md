# LeadForge System Architecture & Engineering Design
## Smart India Hackathon 2026 (Problem Statement SIH26146)

LeadForge is built as a **modular monolith** optimized for high-throughput metadata ingestion, complex graph traversal, statistical anomaly detection, and offline forensic intelligence.

---

## 1. High-Level Architectural Flow

```
[ Raw Metadata Input (CSV / JSON / XML) ]
                   │
                   ▼
┌─────────────────────────────────────────────────────────────┐
│  Ingestion Engine (Streaming, Chunked, Schema Validation)   │
│  - Ingestion Validator (Base58, Bech32, Hex TXID regex)     │
│  - UTC Normalization & Missing Field Imputation             │
│  - Data Quality Analyzer (Completeness, Duplicate Tracker)  │
└──────────────────────────────┬──────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────┐
│  Persistence & Correlation Layer (SQLAlchemy 2.0 ORM)       │
│  - Transactions, Inputs, Outputs, Wallets                   │
│  - IPObservations (Network layer wire broadcast provenance) │
└──────────────────────────────┬──────────────────────────────┘
                               │
               ┌───────────────┴───────────────┐
               ▼                               ▼
┌──────────────────────────────┐ ┌─────────────────────────────┐
│ In-Memory Graph Engine       │ │ Feature Engineering Pipeline│
│ (NetworkX MultiDiGraph)      │ │ (20+ Behavioral Signals)    │
│ - k-Hop Neighbor Traversal   │ │ - Velocity & Burst Rates    │
│ - Shortest Path Tracing      │ │ - Counterparty Diversity    │
│ - Topological Metrics        │ │ - Jurisdictional Entropy    │
└──────────────┬───────────────┘ └──────────────┬──────────────┘
               │                                │
               └───────────────┬────────────────┘
                               ▼
┌─────────────────────────────────────────────────────────────┐
│  Machine Learning & Risk Intelligence Core                  │
│  - Isolation Forest (100 Trees Subspace Isolation)          │
│  - Local Outlier Factor (LOF Baseline Comparison)           │
│  - DBSCAN Behavioral Clustering                             │
│  - Population Baseline Deviation Explainability Engine      │
│  - Deterministic 0-100 Investigation Risk Prioritization    │
└──────────────────────────────┬──────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────┐
│  Investigative Intelligence Workspace & API (FastAPI)       │
│  - Interactive Cytoscape.js Link Visualizer                 │
│  - Ranked Alert Lifecycle Management (NEW -> RESOLVED)      │
│  - Forensic Lead Brief / Investigation Report Generator     │
└─────────────────────────────────────────────────────────────┘
```

---

## 2. Core Modules Description

1. **`backend/app/ingestion/`**: Handles streaming chunked parsing of CSV, JSON, and XML files. Implements syntactic validation (Bech32, Base58, TXID hashes), UTC conversion, and generates detailed Data Quality metrics.
2. **`backend/app/geoip/`**: 100% offline GeoIP subnet mapping engine resolving IP addresses to ISO country codes, country names, and Autonomous System Numbers (ASNs) with zero external calls.
3. **`backend/app/graph/`**: Builds and maintains an in-memory heterogeneous `networkx.MultiDiGraph` with typed nodes (`WALLET`, `TRANSACTION`, `IP`, `ASN`, `COUNTRY`) and edges (`INPUT_OF`, `OUTPUT_TO`, `OBSERVED_IN`, `BELONGS_TO_ASN`, `LOCATED_IN`).
4. **`backend/app/ml/`**: Genuine ML pipeline training `IsolationForest` and comparing against `LocalOutlierFactor` with automated ROC-AUC, PR-AUC, and F1 calculation against synthetic ground-truth benchmark scenarios.
5. **`backend/app/explainability/`**: Generates mathematically backed explanations by calculating feature $z$-scores and deviation multiples against population medians.
6. **`backend/app/risk/`**: Computes deterministic 0-100 composite investigation priority scores combining ML anomaly scores with domain heuristic multipliers.
7. **`frontend/src/`**: Modern React 18 + TypeScript + Vite + Tailwind CSS dashboard with Cytoscape.js canvas rendering, level-of-detail filtering, and responsive intelligence views.
