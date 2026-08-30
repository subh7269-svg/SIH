import pytest
import pandas as pd
from backend.app.ml.features import extract_wallet_features_from_db
from backend.app.services.dataset_service import create_dataset_record
from backend.app.ingestion.pipeline import process_dataset_stream

def test_feature_engineering_extraction(db):
    csv_data = (
        "txid,timestamp,fee,script_type,input_addresses,input_amounts,output_addresses,output_amounts,src_ip,geo_country,asn\n"
        "TX1,2026-08-20T10:00:00Z,0.001,P2PKH,bc1q_w1,5.0,bc1q_w2;bc1q_w3,2.5;2.499,8.8.8.8,US,AS15169\n"
        "TX2,2026-08-20T10:05:00Z,0.001,P2PKH,bc1q_w2,2.5,bc1q_w4,2.499,1.1.1.1,AU,AS13335\n"
    ).encode("utf-8")

    ds = create_dataset_record(db, "feat_test.csv", "csv", len(csv_data))
    process_dataset_stream(db, ds.id, csv_data, "csv")

    df_feats, feature_names = extract_wallet_features_from_db(db, dataset_id=ds.id)

    assert not df_feats.empty
    assert "bc1q_w1" in df_feats.index
    assert "tx_velocity_per_hour" in feature_names
    assert "unique_counterparties" in feature_names
    assert "unique_observed_ips" in feature_names
    assert "foreign_geo_entropy" in feature_names

    w1_row = df_feats.loc["bc1q_w1"]
    assert w1_row["tx_outgoing_count"] == 1
    assert w1_row["total_outgoing_btc"] == 5.0
    assert w1_row["unique_counterparties"] == 2  # w2 and w3
