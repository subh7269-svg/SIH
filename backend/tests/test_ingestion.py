import io
import json
import pytest
from backend.app.ingestion.parsers import parse_csv_stream, parse_json_stream, parse_xml_stream
from backend.app.ingestion.validation import validate_record
from backend.app.ingestion.normalizer import normalize_record
from backend.app.ingestion.pipeline import process_dataset_stream
from backend.app.services.dataset_service import create_dataset_record

def test_validate_record_valid():
    rec = {
        "txid": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        "timestamp": "2026-08-20T10:00:00Z",
        "input_addresses": ["bc1qxy2kgdygjrsqtzq2n0yrf2493p83kkfjhx0wlh"],
        "input_amounts": [1.5],
        "output_addresses": ["bc1qw508d6qejxtdg4y5r3zarvary0c5xw7kv8f3t4"],
        "output_amounts": [1.499],
        "fee": 0.001,
        "src_ip": "1.1.1.1"
    }
    is_valid, reason = validate_record(rec)
    assert is_valid is True
    assert reason is None

def test_validate_record_malformed_input():
    rec = {
        "txid": "invalid_short_txid",
        "timestamp": "2026-08-20T10:00:00Z",
        "input_addresses": [],
        "output_addresses": ["bc1qw508d6qejxtdg4y5r3zarvary0c5xw7kv8f3t4"]
    }
    is_valid, reason = validate_record(rec)
    assert is_valid is False
    assert "TXID" in reason or "input address" in reason

def test_csv_parser_and_streaming():
    csv_content = (
        "txid,timestamp,fee,script_type,input_addresses,input_amounts,output_addresses,output_amounts,src_ip\n"
        "TX001,2026-08-20T10:00:00Z,0.001,P2PKH,bc1qa;bc1qb,1.0;2.0,bc1qc,2.999,8.8.8.8\n"
        "TX002,2026-08-20T11:00:00Z,0.001,P2WPKH,bc1qc,2.999,bc1qd,2.998,1.1.1.1\n"
    )
    stream = list(parse_csv_stream(io.StringIO(csv_content), chunk_size=1))
    assert len(stream) == 2
    assert stream[0][0]["txid"] == "TX001"
    assert stream[0][0]["input_addresses"] == ["bc1qa", "bc1qb"]
    assert stream[0][0]["input_amounts"] == ["1.0", "2.0"]

def test_json_parser():
    json_data = json.dumps([
        {
            "txid": "TX_JSON_01",
            "timestamp": "2026-08-20T12:00:00Z",
            "fee": 0.0005,
            "input_addresses": ["bc1q_sender_1"],
            "input_amounts": [0.5],
            "output_addresses": ["bc1q_receiver_1"],
            "output_amounts": [0.4995],
            "src_ip": "45.33.32.156"
        }
    ]).encode("utf-8")
    chunks = list(parse_json_stream(json_data))
    assert len(chunks) == 1
    assert chunks[0][0]["txid"] == "TX_JSON_01"

def test_xml_parser():
    xml_data = (
        b"<transactions>"
        b"  <transaction>"
        b"    <txid>TX_XML_01</txid>"
        b"    <timestamp>2026-08-20T14:00:00Z</timestamp>"
        b"    <fee>0.001</fee>"
        b"    <script_type>P2PKH</script_type>"
        b"    <input_addresses><item>bc1q_xml_in</item></input_addresses>"
        b"    <input_amounts><item>2.0</item></input_amounts>"
        b"    <output_addresses><item>bc1q_xml_out</item></output_addresses>"
        b"    <output_amounts><item>1.999</item></output_amounts>"
        b"    <src_ip>185.220.101.5</src_ip>"
        b"  </transaction>"
        b"</transactions>"
    )
    chunks = list(parse_xml_stream(xml_data))
    assert len(chunks) == 1
    assert chunks[0][0]["txid"] == "TX_XML_01"
    assert chunks[0][0]["input_addresses"] == ["bc1q_xml_in"]

def test_full_pipeline_ingestion_and_dq_metrics(db):
    csv_content = (
        "txid,timestamp,fee,script_type,input_addresses,input_amounts,output_addresses,output_amounts,src_ip\n"
        "TX_INGEST_1,2026-08-20T10:00:00Z,0.001,P2PKH,bc1q_alpha,1.0,bc1q_beta,0.999,8.8.8.8\n"
        "TX_INGEST_2,2026-08-20T10:05:00Z,0.001,P2PKH,bc1q_beta,0.999,bc1q_gamma,0.998,185.220.101.5\n"
        "TX_INGEST_DUP,2026-08-20T10:10:00Z,0.001,P2PKH,bc1q_gamma,0.5,bc1q_delta,0.499,1.1.1.1\n"
        "TX_INGEST_DUP,2026-08-20T10:10:00Z,0.001,P2PKH,bc1q_gamma,0.5,bc1q_delta,0.499,1.1.1.1\n"
    ).encode("utf-8")

    ds = create_dataset_record(db, "test.csv", "csv", len(csv_content))
    dq_report = process_dataset_stream(db, ds.id, csv_content, "csv")

    assert dq_report["total_records"] == 4
    assert dq_report["valid_records"] == 3
    assert dq_report["duplicate_records"] == 1
    assert dq_report["unique_txids"] == 3
    assert dq_report["unique_wallets"] == 4
