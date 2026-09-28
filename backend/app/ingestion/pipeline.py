import io
import uuid
from datetime import datetime, timezone
from typing import Dict, Any, Optional, Set
from sqlalchemy.orm import Session
from sqlalchemy import select

from backend.app.models.dataset import Dataset
from backend.app.models.transaction import Transaction, TransactionInput, TransactionOutput, IPObservation
from backend.app.models.entity import Wallet
from backend.app.ingestion.validation import validate_record
from backend.app.ingestion.normalizer import normalize_record, to_utc
from backend.app.ingestion.parsers import parse_csv_stream, parse_json_stream, parse_xml_stream
from backend.app.ingestion.quality import DataQualityAnalyzer
from backend.app.core.errors import DatasetProcessingError, InvalidFileFormatError
from backend.app.core.logging import logger

from sqlalchemy import text

def upsert_wallet_batch(db: Session, chunk_wallet_map: Dict[str, Dict[str, Any]], batch_size: int = 1000) -> None:
    """Safe high-performance batch upsert for wallets using native SQLite ON CONFLICT with ORM fallback."""
    if not chunk_wallet_map:
        return

    is_sqlite = True
    try:
        bind_url = str(db.bind.url) if db.bind else ""
        is_sqlite = bind_url.startswith("sqlite")
    except Exception:
        pass

    if is_sqlite:
        now_dt = datetime.now(timezone.utc)
        params = []
        for addr, meta in chunk_wallet_map.items():
            params.append({
                "id": str(uuid.uuid4()),
                "address": addr,
                "first_seen": meta.get("first_seen") or now_dt,
                "last_seen": meta.get("last_seen") or now_dt,
                "total_received": round(meta.get("received", 0.0), 8),
                "total_sent": round(meta.get("sent", 0.0), 8),
                "tx_count": meta.get("tx_count", 1),
                "risk_score": meta.get("risk_score", 0),
                "anomaly_score": meta.get("anomaly_score", 0.0),
                "created_at": now_dt
            })

        upsert_stmt = text("""
            INSERT INTO wallets (id, address, first_seen, last_seen, total_received, total_sent, tx_count, risk_score, anomaly_score, created_at)
            VALUES (:id, :address, :first_seen, :last_seen, :total_received, :total_sent, :tx_count, :risk_score, :anomaly_score, :created_at)
            ON CONFLICT(address) DO UPDATE SET
                first_seen = MIN(wallets.first_seen, excluded.first_seen),
                last_seen = MAX(wallets.last_seen, excluded.last_seen),
                total_received = ROUND(wallets.total_received + excluded.total_received, 8),
                total_sent = ROUND(wallets.total_sent + excluded.total_sent, 8),
                tx_count = wallets.tx_count + excluded.tx_count,
                risk_score = CASE WHEN excluded.risk_score > 0 THEN excluded.risk_score ELSE wallets.risk_score END,
                anomaly_score = CASE WHEN excluded.anomaly_score > 0.0 THEN excluded.anomaly_score ELSE wallets.anomaly_score END
        """)
        for i in range(0, len(params), batch_size):
            db.execute(upsert_stmt, params[i:i + batch_size])
        logger.debug(f"[PIPELINE] Upserted {len(params)} wallets via native SQLite ON CONFLICT")
        return

    # Fallback for non-SQLite databases
    addrs = list(chunk_wallet_map.keys())
    logger.debug(f"[PIPELINE] Upserting {len(addrs)} wallets in batches of {batch_size}")
    for i in range(0, len(addrs), batch_size):
        sub_addrs = addrs[i:i + batch_size]
        existing = {w.address: w for w in db.query(Wallet).filter(Wallet.address.in_(sub_addrs)).all()}
        new_wallets = []
        for addr in sub_addrs:
            meta = chunk_wallet_map[addr]
            if addr in existing:
                w = existing[addr]
                w_first = to_utc(w.first_seen)
                m_first = to_utc(meta.get("first_seen"))
                if w_first and m_first:
                    w.first_seen = min(w_first, m_first)
                elif m_first:
                    w.first_seen = m_first

                w_last = to_utc(w.last_seen)
                m_last = to_utc(meta.get("last_seen"))
                if w_last and m_last:
                    w.last_seen = max(w_last, m_last)
                elif m_last:
                    w.last_seen = m_last

                w.total_sent = round(w.total_sent + meta.get("sent", 0.0), 8)
                w.total_received = round(w.total_received + meta.get("received", 0.0), 8)
                w.tx_count += meta.get("tx_count", 0)
                if "risk_score" in meta:
                    w.risk_score = meta["risk_score"]
                if "anomaly_score" in meta:
                    w.anomaly_score = meta["anomaly_score"]
            else:
                new_w = Wallet(
                    id=str(uuid.uuid4()),
                    address=addr,
                    first_seen=meta.get("first_seen") or datetime.now(timezone.utc),
                    last_seen=meta.get("last_seen") or datetime.now(timezone.utc),
                    total_sent=round(meta.get("sent", 0.0), 8),
                    total_received=round(meta.get("received", 0.0), 8),
                    tx_count=meta.get("tx_count", 1),
                    risk_score=meta.get("risk_score", 0),
                    anomaly_score=meta.get("anomaly_score", 0.0)
                )
                new_wallets.append(new_w)

        if new_wallets:
            db.bulk_save_objects(new_wallets)
            logger.debug(f"[PIPELINE] Created {len(new_wallets)} new wallets, updated {len(sub_addrs) - len(new_wallets)} existing")

def process_dataset_stream(
    db: Session,
    dataset_id: str,
    file_bytes: Optional[bytes] = None,
    file_format: str = "csv",
    file_path: Optional[str] = None
) -> Dict[str, Any]:
    """
    Ingests and processes raw dataset content in chunks with validation, normalization, and relational persistence.
    Supports streaming directly from disk without memory accumulation or SQL variable limit crashes.
    """
    logger.info(f"[PIPELINE] ▶ Starting ingestion: dataset={dataset_id}, format={file_format}, source={'file' if file_path else 'bytes'}")

    dataset = db.query(Dataset).filter(Dataset.id == dataset_id).first()
    if not dataset:
        logger.error(f"[PIPELINE] ✗ Dataset {dataset_id} does not exist in DB!")
        raise DatasetProcessingError(f"Dataset {dataset_id} does not exist.")

    dataset.status = "PROCESSING"
    db.commit()
    logger.info(f"[PIPELINE] Dataset {dataset_id} status → PROCESSING")

    dq_analyzer = DataQualityAnalyzer()
    seen_txids: Set[str] = set()

    format_lower = file_format.lower().strip()
    chunk_number = 0
    try:
        source = file_path if file_path else (io.BytesIO(file_bytes) if format_lower == "csv" else file_bytes)
        if format_lower == "csv":
            logger.debug(f"[PIPELINE] Using CSV parser (chunk_size=1000)")
            stream = parse_csv_stream(source, chunk_size=1000)
        elif format_lower == "json":
            logger.debug(f"[PIPELINE] Using JSON parser (chunk_size=1000)")
            stream = parse_json_stream(source, chunk_size=1000)
        elif format_lower == "xml":
            logger.debug(f"[PIPELINE] Using XML parser (chunk_size=1000)")
            stream = parse_xml_stream(source, chunk_size=1000)
        else:
            logger.error(f"[PIPELINE] ✗ Invalid file format: {format_lower}")
            raise InvalidFileFormatError(format_lower)

        for chunk in stream:
            chunk_number += 1
            tx_batch = []
            inputs_batch = []
            outputs_batch = []
            ip_obs_batch = []
            chunk_wallet_map: Dict[str, Dict[str, Any]] = {}
            chunk_valid = 0
            chunk_rejected = 0

            for raw in chunk:
                is_valid, reason = validate_record(raw)
                if not is_valid:
                    dq_analyzer.record_rejected(reason)
                    chunk_rejected += 1
                    continue

                norm = normalize_record(raw)

                # Schema A: Wallet Classification Record (e.g. wallets_classes.csv)
                if norm.get("record_type") == "WALLET":
                    addr = norm["address"]
                    dq_analyzer.record_valid(norm)
                    chunk_valid += 1
                    chunk_wallet_map[addr] = {
                        "first_seen": norm.get("timestamp") or datetime.now(timezone.utc),
                        "last_seen": norm.get("timestamp") or datetime.now(timezone.utc),
                        "risk_score": norm.get("risk_score", 0),
                        "anomaly_score": norm.get("anomaly_score", 0.0),
                        "sent": 0.0,
                        "received": 0.0,
                        "tx_count": 0
                    }
                    continue

                # Schema B: Standard Transaction Record
                txid = norm.get("txid")
                if txid in seen_txids:
                    dq_analyzer.record_duplicate(txid)
                    continue

                seen_txids.add(txid)
                dq_analyzer.record_valid(norm)
                chunk_valid += 1

                # Create transaction model
                tx_id = str(uuid.uuid4())
                tx_obj = Transaction(
                    id=tx_id,
                    dataset_id=dataset_id,
                    txid=txid,
                    timestamp=norm["timestamp"],
                    fee=norm["fee"],
                    script_type=norm["script_type"],
                    input_total=norm["input_total"],
                    output_total=norm["output_total"]
                )
                tx_batch.append(tx_obj)

                # Create Inputs
                for addr, amt in zip(norm["input_addresses"], norm["input_amounts"]):
                    in_obj = TransactionInput(
                        id=str(uuid.uuid4()),
                        transaction_id=tx_id,
                        txid=txid,
                        wallet_address=addr,
                        amount=amt
                    )
                    inputs_batch.append(in_obj)

                    if addr not in chunk_wallet_map:
                        chunk_wallet_map[addr] = {
                            "first_seen": norm["timestamp"],
                            "last_seen": norm["timestamp"],
                            "received": 0.0,
                            "sent": amt,
                            "tx_count": 1
                        }
                    else:
                        w = chunk_wallet_map[addr]
                        w["first_seen"] = min(w["first_seen"], norm["timestamp"])
                        w["last_seen"] = max(w["last_seen"], norm["timestamp"])
                        w["sent"] += amt
                        w["tx_count"] += 1

                # Create Outputs
                for addr, amt in zip(norm["output_addresses"], norm["output_amounts"]):
                    out_obj = TransactionOutput(
                        id=str(uuid.uuid4()),
                        transaction_id=tx_id,
                        txid=txid,
                        wallet_address=addr,
                        amount=amt
                    )
                    outputs_batch.append(out_obj)

                    if addr not in chunk_wallet_map:
                        chunk_wallet_map[addr] = {
                            "first_seen": norm["timestamp"],
                            "last_seen": norm["timestamp"],
                            "received": amt,
                            "sent": 0.0,
                            "tx_count": 1
                        }
                    else:
                        w = chunk_wallet_map[addr]
                        w["first_seen"] = min(w["first_seen"], norm["timestamp"])
                        w["last_seen"] = max(w["last_seen"], norm["timestamp"])
                        w["received"] += amt
                        w["tx_count"] += 1

                # Create IP Observation if present
                if norm.get("src_ip"):
                    ip_obj = IPObservation(
                        id=str(uuid.uuid4()),
                        dataset_id=dataset_id,
                        transaction_id=tx_id,
                        txid=txid,
                        timestamp=norm["timestamp"],
                        src_ip=norm["src_ip"],
                        dst_ip=norm.get("dst_ip"),
                        src_port=norm.get("src_port"),
                        dst_port=norm.get("dst_port"),
                        country=norm.get("geo_country"),
                        asn=norm.get("asn")
                    )
                    ip_obs_batch.append(ip_obj)

            # Persist transactions and relationships in safe batches of 500
            for i in range(0, len(tx_batch), 500):
                db.bulk_save_objects(tx_batch[i:i + 500])
            for i in range(0, len(inputs_batch), 500):
                db.bulk_save_objects(inputs_batch[i:i + 500])
            for i in range(0, len(outputs_batch), 500):
                db.bulk_save_objects(outputs_batch[i:i + 500])
            for i in range(0, len(ip_obs_batch), 500):
                db.bulk_save_objects(ip_obs_batch[i:i + 500])

            # Upsert wallets in safe slices of 500
            upsert_wallet_batch(db, chunk_wallet_map, batch_size=500)

            # Commit chunk transaction and release memory
            db.commit()
            logger.info(
                f"[PIPELINE] Chunk #{chunk_number} committed: "
                f"txns={len(tx_batch)}, inputs={len(inputs_batch)}, outputs={len(outputs_batch)}, "
                f"ips={len(ip_obs_batch)}, wallets={len(chunk_wallet_map)}, "
                f"valid={chunk_valid}, rejected={chunk_rejected}"
            )

        # Generate Data Quality report and update Dataset
        dq_report = dq_analyzer.generate_report()
        dataset.status = "COMPLETED"
        dataset.total_records = dq_report["total_records"]
        dataset.processed_records = dq_report["valid_records"]
        dataset.rejected_records = dq_report["rejected_records"]
        dataset.data_quality_metrics = dq_report
        dataset.completed_at = datetime.now(timezone.utc)
        dataset.error_summary = None
        db.commit()

        logger.info(
            f"[PIPELINE] ✓ Dataset {dataset_id} COMPLETED — "
            f"chunks={chunk_number}, total={dq_report['total_records']}, "
            f"valid={dq_report['valid_records']}, rejected={dq_report['rejected_records']}, "
            f"duplicates={dq_report.get('duplicate_records', 0)}"
        )
        return dq_report

    except Exception as e:
        logger.error(f"[PIPELINE] ✗ FATAL ERROR in dataset {dataset_id} at chunk #{chunk_number}: {e}", exc_info=True)
        db.rollback()
        try:
            ds = db.query(Dataset).filter(Dataset.id == dataset_id).first()
            if ds:
                ds.status = "FAILED"
                ds.error_summary = f"Ingestion failed: {str(e)}"
                ds.completed_at = datetime.now(timezone.utc)
                if dq_analyzer.total_records > 0:
                    ds.data_quality_metrics = dq_analyzer.generate_report()
                    ds.total_records = dq_analyzer.total_records
                    ds.processed_records = dq_analyzer.valid_records
                    ds.rejected_records = dq_analyzer.rejected_records
                db.commit()
                logger.info(f"[PIPELINE] Dataset {dataset_id} marked as FAILED in DB")
        except Exception as status_err:
            logger.error(f"[PIPELINE] ✗ Could not mark dataset {dataset_id} as FAILED: {status_err}", exc_info=True)
        raise DatasetProcessingError(f"Dataset processing failed: {str(e)}")
