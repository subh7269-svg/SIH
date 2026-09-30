# Unit and Integration Test Suite for LeadForge Correlation Engine
import pytest
import os
import pandas as pd
from pathlib import Path

from backend.app.correlation.column_detector import detect_column, detect_schema, normalize_txid
from backend.app.correlation.transaction_ingestion import (
    safe_parse_list,
    safe_parse_amounts,
    stream_transactions
)
from backend.app.correlation.wallet_correlator import WalletCorrelator
from backend.app.correlation.network_correlator import NetworkCorrelator, parse_epoch_seconds
from backend.app.correlation.feature_service import extract_features
from backend.app.correlation.risk_service import RiskService
from backend.app.correlation.graph_service import GraphService
from backend.app.correlation.validator import validate_dataset


# 1. TXID Extraction and Alias Detection
def test_txid_extraction_and_aliases():
    cols1 = ["tx_id", "time", "fee"]
    cols2 = ["transaction_id", "timestamp", "fees"]
    cols3 = ["txId", "Time step", "fees"]

    assert detect_column(cols1, "txid") == "tx_id"
    assert detect_column(cols2, "txid") == "transaction_id"
    assert detect_column(cols3, "txid") == "txId"

    assert normalize_txid("100234.0") == "100234"
    assert normalize_txid("bc1qtxhash") == "bc1qtxhash"
    assert normalize_txid(5544.0) == "5544"


# 2. Timestamp Parsing and Scaling
def test_timestamp_parsing():
    iso_time = "2026-08-20T10:18:00+00:00"
    epoch = parse_epoch_seconds(iso_time)
    assert epoch is not None
    assert epoch > 1700000000

    assert parse_epoch_seconds(1) == 10800.0
    assert parse_epoch_seconds(2) == 21600.0
    assert parse_epoch_seconds("invalid_date") is None
    assert parse_epoch_seconds(None) is None


# 3. Amount and Fee Parsing
def test_amount_and_fee_parsing():
    assert safe_parse_amounts("0.5, 1.25, 3.0") == [0.5, 1.25, 3.0]
    assert safe_parse_amounts("[10.5, 20.0]") == [10.5, 20.0]
    assert safe_parse_amounts("invalid") == []
    assert safe_parse_amounts(None) == []

    assert safe_parse_list("addr1, addr2, addr3") == ["addr1", "addr2", "addr3"]
    assert safe_parse_list("['addrA', 'addrB']") == ["addrA", "addrB"]
    assert safe_parse_list("") == []


# 4. Wallet Correlation
def test_wallet_correlation(tmp_path):
    addr_tx = tmp_path / "AddrTx_edgelist.csv"
    tx_addr = tmp_path / "TxAddr_edgelist.csv"
    txs_classes = tmp_path / "txs_classes.csv"
    wallets_classes = tmp_path / "wallets_classes.csv"

    addr_tx.write_text("input_address,txId\nW_IN_1,TX999\nW_IN_2,TX999\n", encoding="utf-8")
    tx_addr.write_text("txId,output_address\nTX999,W_OUT_1\nTX999,W_OUT_2\n", encoding="utf-8")
    txs_classes.write_text("txId,class\nTX999,1\n", encoding="utf-8")
    wallets_classes.write_text("address,class\nW_IN_1,1\nW_OUT_1,2\n", encoding="utf-8")

    correlator = WalletCorrelator(dataset_dir=tmp_path)
    correlator.load_transaction_classes()
    correlator.load_wallet_classes()
    correlator.load_edgelists()

    res = correlator.correlate_transaction("TX999", inline_inputs=["W_IN_1"], inline_outputs=["W_OUT_3"])
    assert res["tx_class"] == "illicit"
    assert "W_IN_1" in res["input_wallets"]
    assert "W_IN_2" in res["input_wallets"]
    assert "W_OUT_1" in res["output_wallets"]
    assert "W_OUT_3" in res["output_wallets"]
    assert len(res["input_wallets"]) == len(set(res["input_wallets"]))
    assert res["wallet_count"] == 5


# 5. Exact TXID Network Correlation
def test_exact_txid_network_correlation(tmp_path):
    net_csv = tmp_path / "network_data.csv"
    net_csv.write_text(
        "timestamp,src_ip,src_port,dst_ip,dst_port,txid\n2026-08-20T10:18:00Z,198.51.100.1,8333,203.0.113.5,8333,TX_EXACT_1\n",
        encoding="utf-8"
    )

    correlator = NetworkCorrelator(dataset_dir=tmp_path, time_window_seconds=120.0)
    correlator.load_network_data()

    res = correlator.correlate(txid="TX_EXACT_1", tx_timestamp="2026-08-20T10:18:00Z")
    assert res["correlation_method"] == "exact_txid"
    assert res["network_confidence"] == 1.0
    assert res["src_ip"] == "198.51.100.1"
    assert res["src_port"] == 8333


# 6. Timestamp Network Correlation
def test_timestamp_network_correlation(tmp_path):
    net_csv = tmp_path / "network_data.csv"
    net_csv.write_text(
        "timestamp,src_ip,src_port,dst_ip,dst_port,txid\n2026-08-20T10:18:30Z,192.0.2.45,8333,198.51.100.99,8333,\n",
        encoding="utf-8"
    )

    correlator = NetworkCorrelator(dataset_dir=tmp_path, time_window_seconds=120.0)
    correlator.load_network_data()

    res = correlator.correlate(txid="TX_NO_EXACT", tx_timestamp="2026-08-20T10:18:00Z")
    assert res["correlation_method"] == "timestamp_window"
    assert res["time_difference_seconds"] == 30.0
    assert res["src_ip"] == "192.0.2.45"
    assert 0.74 < res["network_confidence"] < 0.76


# 7. Confidence Calculation Monotonic Decay
def test_confidence_decay():
    window = 100.0
    dt_values = [0.0, 20.0, 50.0, 80.0, 100.0, 150.0]
    expected_confs = [1.0, 0.8, 0.5, 0.2, 0.0, 0.0]

    for dt, exp in zip(dt_values, expected_confs):
        conf = max(0.0, 1.0 - (dt / window))
        assert abs(conf - exp) < 1e-4


# 8. Risk Scoring and Explainability Evidence
def test_risk_scoring_and_evidence():
    scorer = RiskService()

    high_risk_features = {
        "fan_in": 10,
        "fan_out": 8,
        "transaction_amount": 60.0,
        "fee": 0.005,
        "wallet_count": 8,
        "network_confidence": 0.95
    }
    net_info = {
        "correlation_method": "exact_txid",
        "network_confidence": 0.95,
        "time_difference_seconds": 2.5
    }

    lead = scorer.calculate_investigation_lead(
        txid="TX_ALERT_1",
        features=high_risk_features,
        tx_class="illicit",
        network_info=net_info
    )

    assert lead["risk_score"] >= 70
    assert lead["priority"] == "HIGH"
    assert len(lead["evidence"]) >= 4
    evidence_str = " ".join(lead["evidence"])
    assert "High fan-in" in evidence_str
    assert "High fan-out" in evidence_str
    assert "Large transaction" in evidence_str or "Very large" in evidence_str
    assert "Strong network correlation" in evidence_str


# 9. Graph Generation
def test_graph_generation(tmp_path):
    gs = GraphService()
    gs.add_transaction_edges(
        txid="TX_GRAPH_1",
        input_wallets=["W_A", "W_B"],
        output_wallets=["W_C"],
        src_ip="203.0.113.10"
    )

    out_csv = tmp_path / "graph_edges.csv"
    gs.export_edges_csv(out_csv)
    assert out_csv.exists()

    df = pd.read_csv(out_csv)
    assert len(df) == 4
    assert "network_observation" in df["relationship"].values
    assert "input_to" in df["relationship"].values

    cyto = gs.get_subgraph_cytoscape("TX_GRAPH_1", hops=1)
    assert len(cyto["nodes"]) == 5
    assert len(cyto["edges"]) == 4


# 10. Large-File Streaming Chunk Processing
def test_chunked_streaming_processing(tmp_path):
    tx_file = tmp_path / "txs_features.csv"
    rows = []
    for i in range(15):
        rows.append({
            "txid": f"TX_{i}",
            "timestamp": "2026-08-20T12:00:00Z",
            "fee": 0.0001,
            "script_type": "P2PKH",
            "input_addresses": f"in_{i}_a,in_{i}_b",
            "output_addresses": f"out_{i}_a",
            "input_amounts": "1.5, 2.5"
        })
    pd.DataFrame(rows).to_csv(tx_file, index=False)

    chunks_seen = 0
    total_txs = 0
    for chunk in stream_transactions(tx_file, chunk_size=5):
        chunks_seen += 1
        total_txs += len(chunk)
        assert "fan_in" in chunk.columns
        assert "fan_out" in chunk.columns
        assert "total_input_amount" in chunk.columns

    assert chunks_seen == 3
    assert total_txs == 15
