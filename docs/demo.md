# LeadForge SIH 2026 5-Minute Demonstration Script

This script outlines the exact 5-minute judge walkthrough sequence for Problem Statement SIH26146:

---

## Step 1: Platform Overview & Forensic Principle (30 Seconds)
- Open `http://localhost:5173`.
- Explain: *"LeadForge is an offline-capable investigative platform that correlates network-layer P2P broadcast observations with blockchain-layer transactions to generate prioritized, mathematically explainable investigative leads. It does NOT assert definitive wallet ownership from IP observations."*

---

## Step 2: Trigger 1-Click SIH Demo (20 Seconds)
- Click the glowing **"Run 1-Click SIH Demo"** button in the top navigation bar.
- LeadForge will reset, generate the synthetic benchmark scenario, stream ingest CSV, parse network observations, build the entity graph, extract 20+ features, train Isolation Forest vs LOF, run DBSCAN clustering, and rank alerts in under 10 seconds.

---

## Step 3: Inspect Ingestion & Data Quality Hub (30 Seconds)
- Navigate to **"Datasets & Ingestion"**.
- Show the Data Quality report: total rows, 100% valid rows, duplicate TXID detection, unique wallets, unique relay IPs, ASNs, and countries.

---

## Step 4: Review Ranked Alerts & Mathematical Explainability (45 Seconds)
- Navigate to **"Investigative Alerts"**.
- Highlight the Critical/High priority alerts ranked by composite risk score (0-100).
- Click on the highest-priority anomalous entity (`bc1q_peel_chain_alpha_...`).

---

## Step 5: Entity Dossier & Graph Link Analysis (60 Seconds)
- In the Entity Dossier, demonstrate:
  - **Reasoning Card**: Point out the empirical deviation reasons (e.g. *"Transaction velocity 12.4 tx/hr is 5.8x higher than median"*).
  - **Feature Deviation Chart**: Review the $z$-score bar chart.
  - **Ego Graph (2-Hop)**: Show the directed value flow arrows, connected peers, and observed relay IPs with ASNs.
  - Switch layouts (Force-Directed COSE $\to$ Breadthfirst hierarchy).

---

## Step 6: Generate Forensic Lead Brief (30 Seconds)
- Click **"Export Lead Report"**.
- Show the compiled intelligence brief containing the mandatory compliance disclaimer, executive summary, feature breakdown, and transaction/network provenance.
