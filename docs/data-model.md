# TraceX Relational & Graph Data Models

---

## 1. Relational Entities (SQLAlchemy 2.0)

### `Dataset`
Represents an ingested batch of metadata.
- `id` (UUID, Primary Key)
- `filename` (String)
- `format` (String: `csv`, `json`, `xml`)
- `size_bytes` (Integer)
- `status` (String: `PENDING`, `PROCESSING`, `COMPLETED`, `FAILED`)
- `total_records`, `processed_records`, `rejected_records` (Integer)
- `data_quality_metrics` (JSON)
- `uploaded_at`, `completed_at` (DateTime UTC)

### `Transaction`
Represents a recorded Bitcoin blockchain transaction.
- `id` (UUID, Primary Key)
- `dataset_id` (ForeignKey -> `Dataset.id`)
- `txid` (String 64, Indexed)
- `timestamp` (DateTime UTC, Indexed)
- `fee` (Float)
- `script_type` (String: `P2PKH`, `P2SH`, `P2WPKH`, `P2WSH`, `TAPROOT`)
- `input_total`, `output_total` (Float)

### `TransactionInput` & `TransactionOutput`
- `transaction_id` (ForeignKey -> `Transaction.id`)
- `txid` (String 64, Indexed)
- `wallet_address` (String 128, Indexed)
- `amount` (Float)

### `IPObservation` (Network Layer Provenance)
- `dataset_id` (ForeignKey -> `Dataset.id`)
- `transaction_id` (ForeignKey -> `Transaction.id`, Nullable)
- `txid` (String 64, Indexed)
- `timestamp` (DateTime UTC, Indexed)
- `src_ip`, `dst_ip` (String 45, Indexed)
- `src_port`, `dst_port` (Integer)
- `country`, `asn` (String 100, Indexed)

### `Wallet`
- `id` (UUID, Primary Key)
- `address` (String 128, Unique, Indexed)
- `first_seen`, `last_seen` (DateTime UTC)
- `total_received`, `total_sent` (Float)
- `tx_count` (Integer)
- `risk_score` (Integer 0-100)
- `anomaly_score` (Float 0.0-1.0)

### `Alert`
- `id` (UUID, Primary Key)
- `dataset_id` (ForeignKey -> `Dataset.id`)
- `entity_id` (String 128, Indexed)
- `entity_type` (String: `WALLET`, `IP`, `TRANSACTION`)
- `anomaly_score` (Float 0.0-1.0)
- `priority_score` (Integer 0-100)
- `severity` (String: `LOW`, `MEDIUM`, `HIGH`, `CRITICAL`)
- `status` (String: `NEW`, `REVIEWING`, `DISMISSED`, `ESCALATED`, `RESOLVED`)
- `reasons` (JSON List of strings)
- `explanation_details` (JSON Dictionary of feature $z$-scores)
- `evidence_summary` (JSON Provenance records)

---

## 2. Graph Semantic Model

```
(WALLET) ──[:INPUT_OF {amount}]──> (TRANSACTION)
(TRANSACTION) ──[:OUTPUT_TO {amount}]──> (WALLET)
(IP) ──[:OBSERVED_IN {timestamp, port}]──> (TRANSACTION)
(IP) ──[:BELONGS_TO_ASN]──> (ASN)
(IP) ──[:LOCATED_IN]──> (COUNTRY)
```
