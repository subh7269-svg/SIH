import pytest
from backend.app.models.transaction import Transaction, TransactionInput, TransactionOutput, IPObservation
from backend.app.models.entity import Wallet
from backend.app.services.dataset_service import create_dataset_record
from backend.app.ingestion.pipeline import process_dataset_stream

def test_correlation_network_observation_provenance(db):
    """
    Verifies that IP observations are correlated with transaction broadcasts without
    asserting direct wallet ownership.
    """
    csv_data = (
        "txid,timestamp,fee,script_type,input_addresses,input_amounts,output_addresses,output_amounts,src_ip,geo_country,asn\n"
        "TX_CORR_01,2026-08-20T10:00:00Z,0.001,P2PKH,bc1q_sender,2.0,bc1q_receiver,1.999,185.220.101.5,DE,AS200052\n"
    ).encode("utf-8")

    ds = create_dataset_record(db, "corr_test.csv", "csv", len(csv_data))
    process_dataset_stream(db, ds.id, csv_data, "csv")

    tx = db.query(Transaction).filter(Transaction.txid == "TX_CORR_01").first()
    assert tx is not None

    inputs = db.query(TransactionInput).filter(TransactionInput.txid == "TX_CORR_01").all()
    outputs = db.query(TransactionOutput).filter(TransactionOutput.txid == "TX_CORR_01").all()
    ip_obs = db.query(IPObservation).filter(IPObservation.txid == "TX_CORR_01").all()

    assert len(inputs) == 1
    assert inputs[0].wallet_address == "bc1q_sender"
    assert len(outputs) == 1
    assert outputs[0].wallet_address == "bc1q_receiver"

    # Provenance: IP is observed relaying TX_CORR_01, NOT owned by bc1q_sender directly
    assert len(ip_obs) == 1
    assert ip_obs[0].src_ip == "185.220.101.5"
    assert ip_obs[0].country == "DE"
    assert ip_obs[0].asn == "AS200052"
