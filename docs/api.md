# LeadForge REST API Documentation (OpenAPI v3)

All endpoints are versioned under `/api/v1` and accessible via Swagger UI at `/docs`.

---

## 1. Datasets API
- `POST /api/v1/datasets`: Upload CSV, JSON, or XML dataset.
- `GET /api/v1/datasets`: List all datasets and processing status.
- `GET /api/v1/datasets/{id}`: Detailed dataset statistics and Data Quality report.
- `POST /api/v1/datasets/{id}/process`: Re-trigger ingestion & ML pipeline.
- `DELETE /api/v1/datasets/{id}`: Cascade delete dataset.

## 2. Entities & Search API
- `GET /api/v1/entities/search?q={query}`: Multi-type search (Wallet, TXID, IP, ASN).
- `GET /api/v1/entities/{id}`: Full investigative dossier with feature breakdown, ledger, and network provenance.

## 3. Graph API
- `GET /api/v1/graph/overview`: High-level graph topology snapshot.
- `GET /api/v1/graph/entity/{id}?k={hops}`: k-Hop ego network around focal entity.
- `POST /api/v1/graph/path`: Shortest path subgraph connecting two entities.

## 4. Machine Learning & Clustering API
- `POST /api/v1/models/train`: Train Isolation Forest or LOF model.
- `GET /api/v1/models`: List trained model artifacts and benchmark evaluation metrics.
- `GET /api/v1/clusters`: List DBSCAN behavioral entity clusters.

## 5. Alerts & Triage API
- `GET /api/v1/alerts`: List ranked investigative leads with severity and status filters.
- `GET /api/v1/alerts/{id}`: Alert details with mathematical reason breakdown.
- `PATCH /api/v1/alerts/{id}/status`: Update triage status (`NEW`, `REVIEWING`, `ESCALATED`, `DISMISSED`, `RESOLVED`) with investigator notes.

## 6. Reports API
- `POST /api/v1/reports/generate`: Generate formal forensic intelligence report brief.

## 7. Demo API
- `POST /api/v1/demo/run?seed={seed}`: 1-Click end-to-end SIH 2026 demonstration execution.
- `POST /api/v1/demo/reset`: Clear all data for clean slate test.
