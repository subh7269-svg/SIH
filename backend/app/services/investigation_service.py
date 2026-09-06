from typing import List, Dict, Any, Optional
from datetime import timezone
from sqlalchemy.orm import Session
from sqlalchemy import or_

from backend.app.models.entity import Wallet
from backend.app.models.transaction import Transaction, TransactionInput, TransactionOutput, IPObservation
from backend.app.models.alert import Alert
from backend.app.models.feature import EntityFeature
from backend.app.models.ml import EntityCluster
from backend.app.schemas.entity import EntitySearchResult, EntityDossierSchema
from backend.app.core.errors import EntityNotFoundError

def search_entities(db: Session, query_str: str, limit: int = 30) -> List[EntitySearchResult]:
    q = query_str.strip()
    if not q:
        return []

    results: List[EntitySearchResult] = []

    # 1. Search Wallets
    wallets = db.query(Wallet).filter(Wallet.address.ilike(f"%{q}%")).limit(limit).all()
    for w in wallets:
        results.append(EntitySearchResult(
            entity_id=w.address,
            entity_type="WALLET",
            label=f"Wallet {w.address[:8]}...{w.address[-6:]}" if len(w.address) > 16 else w.address,
            subtext=f"Txs: {w.tx_count} | Sent: {w.total_sent:.2f} BTC | Recv: {w.total_received:.2f} BTC",
            risk_score=w.risk_score,
            anomaly_score=w.anomaly_score,
            metadata={"address": w.address, "tx_count": w.tx_count}
        ))

    # 2. Search Transactions
    txs = db.query(Transaction).filter(Transaction.txid.ilike(f"%{q}%")).limit(limit).all()
    for tx in txs:
        results.append(EntitySearchResult(
            entity_id=tx.txid,
            entity_type="TRANSACTION",
            label=f"TX: {tx.txid[:10]}...",
            subtext=f"Total: {tx.input_total:.2f} BTC | Fee: {tx.fee:.4f} BTC | {tx.timestamp.strftime('%Y-%m-%d %H:%M')}",
            risk_score=0,
            anomaly_score=0.0,
            metadata={"txid": tx.txid, "fee": tx.fee, "timestamp": tx.timestamp.isoformat()}
        ))

    # 3. Search IP Observations
    ips = db.query(IPObservation).filter(or_(IPObservation.src_ip.ilike(f"%{q}%"), IPObservation.dst_ip.ilike(f"%{q}%"))).limit(limit).all()
    seen_ips = set()
    for ipo in ips:
        if ipo.src_ip not in seen_ips:
            seen_ips.add(ipo.src_ip)
            results.append(EntitySearchResult(
                entity_id=ipo.src_ip,
                entity_type="IP",
                label=f"IP: {ipo.src_ip}",
                subtext=f"Country: {ipo.country} | ASN: {ipo.asn}",
                risk_score=0,
                anomaly_score=0.0,
                metadata={"ip": ipo.src_ip, "country": ipo.country, "asn": ipo.asn}
            ))

    return results[:limit]

def get_entity_dossier(db: Session, entity_id: str) -> EntityDossierSchema:
    # 1. Check if Wallet
    wallet = db.query(Wallet).filter(Wallet.address == entity_id).first()
    if wallet:
        # Fetch features
        feat_record = db.query(EntityFeature).filter(EntityFeature.entity_id == entity_id).first()
        features = feat_record.features if feat_record else {}

        # Fetch Alert
        alert = db.query(Alert).filter(Alert.entity_id == entity_id).order_by(Alert.priority_score.desc()).first()
        reasons = alert.reasons if alert else []
        deviations = alert.explanation_details if alert else {}
        severity = alert.severity if alert else ("CRITICAL" if wallet.risk_score >= 80 else "HIGH" if wallet.risk_score >= 60 else "MEDIUM" if wallet.risk_score >= 35 else "LOW")

        # Fetch transactions
        inputs = db.query(TransactionInput).filter(TransactionInput.wallet_address == entity_id).limit(20).all()
        outputs = db.query(TransactionOutput).filter(TransactionOutput.wallet_address == entity_id).limit(20).all()
        txids = list(set([i.txid for i in inputs] + [o.txid for o in outputs]))

        tx_records = db.query(Transaction).filter(Transaction.txid.in_(txids)).order_by(Transaction.timestamp.desc()).limit(15).all()
        recent_txs = [{
            "txid": t.txid,
            "timestamp": t.timestamp.isoformat(),
            "input_total": t.input_total,
            "output_total": t.output_total,
            "fee": t.fee,
            "script_type": t.script_type
        } for t in tx_records]

        # Fetch IP observations linked to these transactions
        ip_obs = db.query(IPObservation).filter(IPObservation.txid.in_(txids)).all()
        obs_ips = [{
            "ip": ipo.src_ip,
            "country": ipo.country,
            "asn": ipo.asn,
            "timestamp": ipo.timestamp.isoformat()
        } for ipo in ip_obs]

        obs_countries = list(set([ipo.country for ipo in ip_obs if ipo.country and ipo.country != "UNKNOWN"]))
        obs_asns = list(set([ipo.asn for ipo in ip_obs if ipo.asn and ipo.asn != "UNKNOWN"]))

        # Check clusters
        cluster_info = None
        clusters = db.query(EntityCluster).all()
        for cl in clusters:
            if entity_id in (cl.member_ids or []):
                cluster_info = {
                    "cluster_label": cl.cluster_label,
                    "cluster_name": cl.cluster_name,
                    "algorithm": cl.algorithm,
                    "member_count": cl.member_count
                }
                break

        return EntityDossierSchema(
            entity_id=wallet.address,
            entity_type="WALLET",
            risk_score=wallet.risk_score,
            anomaly_score=wallet.anomaly_score,
            severity=severity,
            first_seen=wallet.first_seen,
            last_seen=wallet.last_seen,
            total_volume_btc=round(wallet.total_received + wallet.total_sent, 4),
            transaction_count=wallet.tx_count,
            unique_counterparties=int(features.get("unique_counterparties", 0)),
            observed_ips=obs_ips,
            observed_countries=obs_countries,
            observed_asns=obs_asns,
            features=features,
            explanation_reasons=reasons,
            feature_deviations=deviations,
            recent_transactions=recent_txs,
            related_alerts=[{
                "id": alert.id,
                "severity": alert.severity,
                "priority_score": alert.priority_score,
                "status": alert.status,
                "created_at": alert.created_at.isoformat()
            }] if alert else [],
            cluster_info=cluster_info
        )

    # 2. Check if Transaction
    tx = db.query(Transaction).filter(Transaction.txid == entity_id).first()
    if tx:
        inputs = db.query(TransactionInput).filter(TransactionInput.txid == entity_id).all()
        outputs = db.query(TransactionOutput).filter(TransactionOutput.txid == entity_id).all()
        ip_obs = db.query(IPObservation).filter(IPObservation.txid == entity_id).all()

        obs_ips = [{"ip": ipo.src_ip, "country": ipo.country, "asn": ipo.asn, "timestamp": ipo.timestamp.isoformat()} for ipo in ip_obs]

        return EntityDossierSchema(
            entity_id=tx.txid,
            entity_type="TRANSACTION",
            risk_score=0,
            anomaly_score=0.0,
            severity="LOW",
            first_seen=tx.timestamp,
            last_seen=tx.timestamp,
            total_volume_btc=round(tx.input_total + tx.output_total, 4),
            transaction_count=1,
            unique_counterparties=len(inputs) + len(outputs),
            observed_ips=obs_ips,
            observed_countries=list(set([ipo.country for ipo in ip_obs if ipo.country])),
            observed_asns=list(set([ipo.asn for ipo in ip_obs if ipo.asn])),
            features={"fee": tx.fee, "input_count": len(inputs), "output_count": len(outputs)},
            explanation_reasons=["Observed blockchain transaction record."],
            feature_deviations={},
            recent_transactions=[{"txid": tx.txid, "timestamp": tx.timestamp.isoformat(), "fee": tx.fee, "script_type": tx.script_type}],
            related_alerts=[]
        )

    # 3. Check if IP
    ip_obs_list = db.query(IPObservation).filter(IPObservation.src_ip == entity_id).all()
    if ip_obs_list:
        related_txids = list(set([ipo.txid for ipo in ip_obs_list]))
        sample = ip_obs_list[0]
        return EntityDossierSchema(
            entity_id=entity_id,
            entity_type="IP",
            risk_score=0,
            anomaly_score=0.0,
            severity="LOW",
            first_seen=min([ipo.timestamp.replace(tzinfo=timezone.utc) if ipo.timestamp.tzinfo is None else ipo.timestamp for ipo in ip_obs_list]) if ip_obs_list else None,
            last_seen=max([ipo.timestamp.replace(tzinfo=timezone.utc) if ipo.timestamp.tzinfo is None else ipo.timestamp for ipo in ip_obs_list]) if ip_obs_list else None,
            total_volume_btc=0.0,
            transaction_count=len(related_txids),
            unique_counterparties=0,
            observed_ips=[{"ip": entity_id, "country": sample.country, "asn": sample.asn}],
            observed_countries=[sample.country] if sample.country else [],
            observed_asns=[sample.asn] if sample.asn else [],
            features={"relayed_tx_count": len(related_txids)},
            explanation_reasons=[f"Network peer IP observed relaying {len(related_txids)} transactions."],
            feature_deviations={},
            recent_transactions=[{"txid": t} for t in related_txids[:10]],
            related_alerts=[]
        )

    raise EntityNotFoundError("Entity", entity_id)
