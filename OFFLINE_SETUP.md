# LeadForge: Offline Environment Preparation & Air-Gapped Deployment Guide
## Smart India Hackathon 2026 (Problem Statement SIH26146)

LeadForge is engineered with a strict **100% Offline-First Architecture**. During operation, the platform requires **zero internet access, zero cloud LLM APIs, zero external GeoIP queries, and zero remote blockchain RPC connections**.

This guide outlines the standard procedures for packaging, verifying, and running LeadForge in air-gapped or offline Linux/Windows environments.

---

## 1. Offline Architectural Guarantees

1. **Embedded GeoIP & ASN Resolution**:
   - LeadForge includes an embedded local IP prefix routing database in `backend/app/geoip/data/offline_subnets.json` and a deterministic subnet classifier in `backend/app/geoip/offline_lookup.py`.
   - All IP-to-Country and Autonomous System Number mappings execute in-memory with microsecond latency.

2. **Self-Contained ML Pipelines**:
   - Machine learning algorithms (`IsolationForest`, `LocalOutlierFactor`, `DBSCAN`, `RobustScaler`) run locally via `scikit-learn` and `numpy`.
   - Trained model artifacts are serialized locally to `ml/artifacts/*.joblib`.

3. **Bundled Frontend Assets**:
   - All React, TypeScript, Tailwind CSS, Lucide icons, Recharts, and Cytoscape.js packages are compiled into static bundles in `frontend/dist/`.
   - No external CDNs or Google Fonts calls are required at runtime.

---

## 2. Preparing Offline Packages (Online Machine)

To export LeadForge for an air-gapped / offline testing machine:

### A. Pre-downloading Python Wheels
```bash
mkdir -p offline_packages/python
pip download -r backend/requirements.txt -d offline_packages/python
```

### B. Pre-bundling Node Modules & Frontend Build
```bash
cd frontend
npm install
npm run build
cd ..
```

### C. (Optional) Exporting Docker Images for Air-Gapped Systems
```bash
docker compose build
docker save -o tracex_offline_images.tar tracex-platform:latest postgres:16-alpine
```

---

## 3. Air-Gapped Machine Installation & Launch

### Option A: Direct Local Execution (Zero-Setup Python + Node)
1. **Install Python Wheels locally**:
   ```bash
   pip install --no-index --find-links=offline_packages/python -r backend/requirements.txt
   ```
2. **Launch Backend**:
   ```bash
   # Windows
   scripts\run_local.bat

   # Linux / macOS
   chmod +x scripts/run_local.sh
   ./scripts/run_local.sh
   ```
3. **Launch Frontend** (or serve `frontend/dist` via Python):
   ```bash
   cd frontend
   npm run dev
   ```

### Option B: Docker Container Deployment (Air-Gapped)
1. **Load pre-built container image**:
   ```bash
   docker load -i tracex_offline_images.tar
   ```
2. **Start Services**:
   ```bash
   docker compose up -d
   ```
3. Access UI at `http://localhost:8000` (or `http://localhost:5173` in dev mode).

---

## 4. Verifying Offline Compliance

To guarantee zero external leakage:
1. Disconnect network interfaces or enable Airplane Mode.
2. Open LeadForge in browser: `http://localhost:5173`.
3. Click **"Run 1-Click SIH Demo"** in the top navigation bar.
4. Verify:
   - Ingestion and validation completes in < 2 seconds.
   - Network IP observations map to Country / ASN via local database.
   - Isolation Forest trains and evaluates against synthetic benchmark scenarios.
   - Cytoscape graph visualizer renders interactive topological flows.
   - Forensic reports generate with complete provenance.
