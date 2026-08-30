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
from backend.app.ingestion.normalizer import normalize_record
from backend.app.ingestion.parsers import parse_csv_stream, parse_json_stream, parse_xml_stream
from backend.app.ingestion.quality import DataQualityAnalyzer
from backend.app.core.errors import DatasetProcessingError, InvalidFileFormatError
from backend.app.core.logging import logger

def process_dataset_stream(
    db: Session,
    dataset_id: str,
    file_bytes: bytes,
    file_format: str
) -> Dict[str, Any]:
    """
    Ingests and processes raw dataset content in chunks with validation, normalization, and relational persistence.
    """
    dataset = db.query(Dataset).filter(Dataset.id == dataset_id).first()
    if not dataset:
        raise DatasetProcessingError(f"Dataset {dataset_id} does not exist.")

    dataset.status = "PROCESSING"
    db.commit()

    dq_analyzer = DataQualityAnalyzer()
    seen_txids: Set[str] = set()

    # Track wallets in memory for batch upsert
    wallet_map: Dict[str, Dict[str, Any]] = {}

    format_lower = file_format.lower().strip()
    try:
        if format_lower == "csv":
            stream = parse_csv_stream(io.BytesIO(file_bytes), chunk_size=1000)
        elif format_lower == "json":
            stream = parse_json_stream(file_bytes, chunk_size=1000)
        elif format_lower == "xml":
            stream = parse_xml_stream(file_bytes, chunk_size=1000)
        else:
            raise InvalidFileFormatError(format_lower)

        for chunk in stream:
            tx_batch = []
            inputs_batch = []
            outputs_batch = []
            ip_obs_batch = []

            for raw in chunk:
                is_valid, reason = validate_record(raw)
                if not is_valid:
                    dq_analyzer.record_rejected(reason)
                    continue

                norm = normalize_record(raw)
                txid = norm["txid"]

                if txid in seen_txids:
                    dq_analyzer.record_duplicate(txid)
                    continue

                seen_txids.add(txid)
                dq_analyzer.record_valid(norm)

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

                    # Update wallet tracker
                    if addr not in wallet_map:
                        wallet_map[addr] = {
                            "first_seen": norm["timestamp"],
                            "last_seen": norm["timestamp"],
                            "received": 0.0,
                            "sent": amt,
                            "tx_count": 1
                        }
                    else:
                        w = wallet_map[addr]
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

                    # Update wallet tracker
                    if addr not in wallet_map:
                        wallet_map[addr] = {
                            "first_seen": norm["timestamp"],
                            "last_seen": norm["timestamp"],
                            "received": amt,
                            "sent": 0.0,
                            "tx_count": 1
                        }
                    else:
                        w = wallet_map[addr]
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
                        dst_ip=norm["dst_ip"],
                        src_port=norm["src_port"],
                        dst_port=norm["dst_port"],
                        country=norm["geo_country"],
                        asn=norm["asn"]
                    )
                    ip_obs_batch.append(ip_obj)

            # Persist batch
            if tx_batch:
                db.bulk_save_objects(tx_batch)
            if inputs_batch:
                db.bulk_save_objects(inputs_batch)
            if outputs_batch:
                db.bulk_save_objects(outputs_batch)
            if ip_obs_batch:
                db.bulk_save_objects(ip_obs_batch)
            db.commit()

        # Batch upsert Wallets
        existing_wallets = {w.address: w for w in db.query(Wallet).filter(Wallet.address.in_(list(wallet_map.keys()))).all()}
        new_wallets = []
        for addr, meta in wallet_map.items():
            if addr in existing_wallets:
                w = existing_wallets[addr]
                w.first_seen = min(w.first_seen, meta["first_seen"])
                w.last_seen = max(w.last_seen, meta["last_seen"])
                w.total_sent += meta["sent"]
                w.total_received += meta["received"]
                w.tx_count += meta["tx_count"]
            else:
                new_w = Wallet(
                    id=str(uuid.uuid4()),
                    address=addr,
                    first_seen=meta["first_seen"],
                    last_seen=meta["last_seen"],
                    total_sent=meta["sent"],
                    total_received=meta["received"],
                    tx_count=meta["tx_count"]
                )
                new_wallets.append(new_w)

        if new_wallets:
            db.bulk_save_objects(new_wallets)
        db.commit()

        # Generate Data Quality report and update Dataset
        dq_report = dq_analyzer.generate_report()
        dataset.status = "COMPLETED"
        dataset.total_records = dq_report["total_records"]
        dataset.processed_records = dq_report["valid_records"]
        dataset.rejected_records = dq_report["rejected_records"]
        dataset.data_quality_metrics = dq_report
        dataset.completed_at = datetime.now(timezone.utc)
        db.commit()

        logger.info(f"Dataset {dataset_id} processed successfully: {dq_report['valid_records']} valid records.")
        return dq_report

    except Exception as e:
        db.rollback()
        dataset.status = "FAILED"
        dataset.error_summary = str(e)
        dataset.completed_at = datetime.now(timezone.utc)
        db.commit()
        logger.error(f"Failed processing dataset {dataset_id}: {str(e)}")
        raise DatasetProcessingError(f"Dataset processing failed: {str(e)}")
