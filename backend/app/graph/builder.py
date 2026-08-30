import networkx as nx
from typing import Dict, Any, Optional, List
from sqlalchemy.orm import Session
from backend.app.models.transaction import Transaction, TransactionInput, TransactionOutput, IPObservation
from backend.app.models.entity import Wallet

def build_networkx_graph_from_db(db: Session, dataset_id: Optional[str] = None) -> nx.MultiDiGraph:
    """
    Constructs a NetworkX MultiDiGraph representing entity interactions.
    Nodes: WALLET, TRANSACTION, IP, ASN, COUNTRY
    Edges: INPUT_OF, OUTPUT_TO, OBSERVED_IN, BELONGS_TO_ASN, LOCATED_IN
    """
    G = nx.MultiDiGraph()

    # Query Transactions
    tx_query = db.query(Transaction)
    if dataset_id:
        tx_query = tx_query.filter(Transaction.dataset_id == dataset_id)
    transactions = tx_query.all()
    tx_ids = [t.id for t in transactions]

    if not tx_ids:
        return G

    # Add Transaction nodes
    for tx in transactions:
        G.add_node(
            tx.txid,
            type="TRANSACTION",
            id=tx.txid,
            label=f"TX: {tx.txid[:8]}...",
            timestamp=tx.timestamp.isoformat() if tx.timestamp else None,
            fee=tx.fee,
            script_type=tx.script_type,
            input_total=tx.input_total,
            output_total=tx.output_total,
            risk_score=0,
            anomaly_score=0.0
        )

    # Inputs: (WALLET) -> (TRANSACTION)
    inputs = db.query(TransactionInput).filter(TransactionInput.transaction_id.in_(tx_ids)).all()
    for inp in inputs:
        wallet_node_id = inp.wallet_address
        if not G.has_node(wallet_node_id):
            G.add_node(
                wallet_node_id,
                type="WALLET",
                id=wallet_node_id,
                label=f"{wallet_node_id[:6]}...{wallet_node_id[-4:]}" if len(wallet_node_id) > 12 else wallet_node_id,
                address=wallet_node_id,
                risk_score=0,
                anomaly_score=0.0
            )
        G.add_edge(
            wallet_node_id,
            inp.txid,
            type="INPUT_OF",
            label=f"{inp.amount:.4f} BTC",
            amount=inp.amount
        )

    # Outputs: (TRANSACTION) -> (WALLET)
    outputs = db.query(TransactionOutput).filter(TransactionOutput.transaction_id.in_(tx_ids)).all()
    for out in outputs:
        wallet_node_id = out.wallet_address
        if not G.has_node(wallet_node_id):
            G.add_node(
                wallet_node_id,
                type="WALLET",
                id=wallet_node_id,
                label=f"{wallet_node_id[:6]}...{wallet_node_id[-4:]}" if len(wallet_node_id) > 12 else wallet_node_id,
                address=wallet_node_id,
                risk_score=0,
                anomaly_score=0.0
            )
        G.add_edge(
            out.txid,
            wallet_node_id,
            type="OUTPUT_TO",
            label=f"{out.amount:.4f} BTC",
            amount=out.amount
        )

    # IP Observations: (IP) -> (TRANSACTION), (IP) -> (ASN), (IP) -> (COUNTRY)
    ip_obs_query = db.query(IPObservation)
    if dataset_id:
        ip_obs_query = ip_obs_query.filter(IPObservation.dataset_id == dataset_id)
    ip_observations = ip_obs_query.all()

    for ip_obs in ip_observations:
        ip_node_id = ip_obs.src_ip
        if not G.has_node(ip_node_id):
            G.add_node(
                ip_node_id,
                type="IP",
                id=ip_node_id,
                label=f"IP: {ip_node_id}",
                ip=ip_node_id,
                country=ip_obs.country,
                asn=ip_obs.asn,
                risk_score=0,
                anomaly_score=0.0
            )

        # Network observation edge (provenance, NOT ownership)
        if G.has_node(ip_obs.txid):
            G.add_edge(
                ip_node_id,
                ip_obs.txid,
                type="OBSERVED_IN",
                label="Relayed TX",
                port=ip_obs.src_port,
                timestamp=ip_obs.timestamp.isoformat() if ip_obs.timestamp else None
            )

        # ASN node
        if ip_obs.asn and ip_obs.asn != "UNKNOWN":
            asn_node_id = ip_obs.asn
            if not G.has_node(asn_node_id):
                G.add_node(
                    asn_node_id,
                    type="ASN",
                    id=asn_node_id,
                    label=asn_node_id,
                    asn=asn_node_id,
                    risk_score=0,
                    anomaly_score=0.0
                )
            G.add_edge(
                ip_node_id,
                asn_node_id,
                type="BELONGS_TO_ASN",
                label="Routing"
            )

        # Country node
        if ip_obs.country and ip_obs.country != "UNKNOWN":
            country_node_id = f"GEO_{ip_obs.country}"
            if not G.has_node(country_node_id):
                G.add_node(
                    country_node_id,
                    type="COUNTRY",
                    id=country_node_id,
                    label=f"Country: {ip_obs.country}",
                    country=ip_obs.country,
                    risk_score=0,
                    anomaly_score=0.0
                )
            G.add_edge(
                ip_node_id,
                country_node_id,
                type="LOCATED_IN",
                label="Geo Location"
            )

    # Enrich wallets with risk/anomaly scores if available
    wallet_addrs = [n for n, d in G.nodes(data=True) if d.get("type") == "WALLET"]
    if wallet_addrs:
        wallets = db.query(Wallet).filter(Wallet.address.in_(wallet_addrs)).all()
        for w in wallets:
            if G.has_node(w.address):
                G.nodes[w.address]["risk_score"] = w.risk_score
                G.nodes[w.address]["anomaly_score"] = w.anomaly_score

    return G
