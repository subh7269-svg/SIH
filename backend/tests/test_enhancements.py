import os
import io
import json
import pytest
from fastapi.testclient import TestClient

CSV_SAMPLE = """timestamp,src_ip,dst_ip,src_port,dst_port,txid,input_addresses,output_addresses,input_amounts,output_amounts,geo_country,asn,fee,script_type
2026-09-27T10:00:00Z,192.168.1.100,10.0.0.1,8333,8333,tx_alpha_1,addr_src_1,addr_dst_1,1.5,1.499,US,AS15169,0.001,P2WPKH
2026-09-27T10:05:00Z,192.168.1.101,10.0.0.2,8333,8333,tx_alpha_2,addr_src_2,addr_dst_2,2.0,1.998,DE,AS3320,0.002,P2WPKH
"""

JSON_SAMPLE = json.dumps([
    {
        "timestamp": "2026-09-27T10:00:00Z",
        "src_ip": "198.51.100.1",
        "dst_ip": "10.0.0.1",
        "src_port": 8333,
        "dst_port": 8333,
        "txid": "tx_json_1",
        "input_addresses": ["addr_j_src_1"],
        "output_addresses": ["addr_j_dst_1"],
        "input_amounts": [3.0],
        "output_amounts": [2.999],
        "geo_country": "SG",
        "asn": "AS4657",
        "fee": 0.001,
        "script_type": "P2SH"
    }
])

XML_SAMPLE = """<transactions>
  <transaction>
    <timestamp>2026-09-27T10:00:00Z</timestamp>
    <src_ip>203.0.113.5</src_ip>
    <dst_ip>10.0.0.1</dst_ip>
    <src_port>8333</src_port>
    <dst_port>8333</dst_port>
    <txid>tx_xml_1</txid>
    <input_addresses><address>addr_xml_src_1</address></input_addresses>
    <output_addresses><address>addr_xml_dst_1</address></output_addresses>
    <input_amounts><amount>5.0</amount></input_amounts>
    <output_amounts><amount>4.995</amount></output_amounts>
    <geo_country>CH</geo_country>
    <asn>AS559</asn>
    <fee>0.005</fee>
    <script_type>P2WPKH</script_type>
  </transaction>
</transactions>"""

def test_1_upload_small_csv(client: TestClient):
    """TEST 1: Upload a small CSV. Expected: COMPLETED and valid records."""
    files = {"file": ("test_small.csv", io.BytesIO(CSV_SAMPLE.encode("utf-8")), "text/csv")}
    resp = client.post("/api/v1/datasets", files=files, data={"run_ml": False})
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["status"] == "COMPLETED"
    assert data["format"] == "csv"
    assert data["processed_records"] == 2
    assert data["total_records"] == 2

def test_2_upload_small_json(client: TestClient):
    """TEST 2: Upload a small JSON. Expected: COMPLETED and valid records."""
    files = {"file": ("test_small.json", io.BytesIO(JSON_SAMPLE.encode("utf-8")), "application/json")}
    resp = client.post("/api/v1/datasets", files=files, data={"run_ml": False})
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["status"] == "COMPLETED"
    assert data["format"] == "json"
    assert data["processed_records"] == 1

def test_3_upload_small_xml(client: TestClient):
    """TEST 3: Upload a small XML. Expected: COMPLETED and valid records."""
    files = {"file": ("test_small.xml", io.BytesIO(XML_SAMPLE.encode("utf-8")), "application/xml")}
    resp = client.post("/api/v1/datasets", files=files, data={"run_ml": False})
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["status"] == "COMPLETED"
    assert data["format"] == "xml"
    assert data["processed_records"] == 1

def test_4_multi_file_batch_upload(client: TestClient):
    """TEST 4: Select multiple files at once (A.csv, B.json, C.xml).
       Expected: All three appear independently in INGESTED DATASETS.
    """
    files = [
        ("files", ("A.csv", io.BytesIO(CSV_SAMPLE.encode("utf-8")), "text/csv")),
        ("files", ("B.json", io.BytesIO(JSON_SAMPLE.encode("utf-8")), "application/json")),
        ("files", ("C.xml", io.BytesIO(XML_SAMPLE.encode("utf-8")), "application/xml")),
    ]
    resp = client.post("/api/v1/datasets/batch", files=files, data={"run_ml": False})
    assert resp.status_code == 200, resp.text
    batch_data = resp.json()
    assert batch_data["total_files"] == 3
    assert batch_data["successful_count"] == 3
    assert batch_data["failed_count"] == 0
    assert len(batch_data["datasets"]) == 3

    # Check each file appeared with its own identity in datasets list
    ds_list_resp = client.get("/api/v1/datasets")
    assert ds_list_resp.status_code == 200
    all_datasets = ds_list_resp.json()["datasets"]
    filenames = [d["filename"] for d in all_datasets]
    assert "A.csv" in filenames
    assert "B.json" in filenames
    assert "C.xml" in filenames

def test_5_upload_large_csv_exceeding_100mb(client: TestClient, tmp_path):
    """TEST 5: Upload a large CSV significantly larger than 100 MB.
       Expected: Accepted and processed using streaming/chunking without 100 MB validation error.
    """
    # Create a 105 MB CSV file on disk using 10KB rows for fast database ingestion
    large_csv_path = tmp_path / "large_dataset_105mb.csv"
    padding = "A" * 10240  # 10 KB of script metadata
    row = f"2026-09-27T10:00:00Z,192.168.1.100,10.0.0.1,8333,8333,tx_large_chunk,addr_src,addr_dst,1.0,0.999,US,AS15169,0.001,{padding}\n"
    target_bytes = 105 * 1024 * 1024 # 105 MB

    with open(large_csv_path, "w", encoding="utf-8") as f:
        f.write("timestamp,src_ip,dst_ip,src_port,dst_port,txid,input_addresses,output_addresses,input_amounts,output_amounts,geo_country,asn,fee,script_type\n")
        bytes_written = 140
        while bytes_written < target_bytes:
            f.write(row)
            bytes_written += len(row)

    file_size = os.path.getsize(large_csv_path)
    assert file_size >= 105 * 1024 * 1024, f"File size {file_size} is under 105 MB"

    # Upload using stream to ensure no 100 MB limit stops it
    with open(large_csv_path, "rb") as f:
        files = {"file": ("large_dataset_105mb.csv", f, "text/csv")}
        resp = client.post("/api/v1/datasets", files=files, data={"run_ml": False})
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert data["status"] == "COMPLETED"
        assert data["size_bytes"] >= 105 * 1024 * 1024
        assert data["processed_records"] > 0

def test_6_multi_file_fault_isolation(client: TestClient):
    """TEST 7: One valid file + one intentionally invalid file.
       Expected: Valid file completes, invalid file shows FAILED/error, and valid file is NOT rolled back.
    """
    valid_csv = CSV_SAMPLE.encode("utf-8")
    invalid_xml = b"<transactions><unclosed_tag>"

    files = [
        ("files", ("valid_part.csv", io.BytesIO(valid_csv), "text/csv")),
        ("files", ("malformed_part.xml", io.BytesIO(invalid_xml), "application/xml")),
    ]
    resp = client.post("/api/v1/datasets/batch", files=files, data={"run_ml": False})
    assert resp.status_code == 200
    batch_res = resp.json()
    assert batch_res["total_files"] == 2
    assert batch_res["successful_count"] == 1
    assert batch_res["failed_count"] == 1

    # Verify both records exist in datasets table and valid file is NOT rolled back
    ds_list = client.get("/api/v1/datasets").json()["datasets"]
    valid_ds = next((d for d in ds_list if d["filename"] == "valid_part.csv"), None)
    invalid_ds = next((d for d in ds_list if d["filename"] == "malformed_part.xml"), None)

    assert valid_ds is not None
    assert valid_ds["status"] == "COMPLETED"
    assert valid_ds["processed_records"] == 2

    assert invalid_ds is not None
    assert invalid_ds["status"] == "FAILED"

def test_8_forensic_report_data_completeness(client: TestClient):
    """TEST 8-12: Generate forensic report with many transaction records.
       Expected: The report retains all transactions without artificial truncation (not sliced to 10),
       and contains all required sections: disclaimer, explainability, risk scores, network evidence.
    """
    # Ingest a dataset with 25 distinct transactions
    rows = ["timestamp,src_ip,dst_ip,src_port,dst_port,txid,input_addresses,output_addresses,input_amounts,output_amounts,geo_country,asn,fee,script_type"]
    for i in range(25):
        rows.append(f"2026-09-27T10:{i:02d}:00Z,198.51.100.{i+1},10.0.0.1,8333,8333,tx_report_test_{i:04d},addr_target_investigation,addr_dest_{i},2.0,1.999,US,AS15169,0.001,P2WPKH")

    multi_tx_csv = "\n".join(rows)
    files = {"file": ("report_multi_tx.csv", io.BytesIO(multi_tx_csv.encode("utf-8")), "text/csv")}
    upload_res = client.post("/api/v1/datasets", files=files, data={"run_ml": True})
    assert upload_res.status_code == 200

    # Generate Report for addr_target_investigation
    rep_resp = client.post("/api/v1/reports/generate", json={
        "title": "Forensic Lead Intelligence Brief: Comprehensive Audit",
        "entity_id": "addr_target_investigation",
        "include_evidence": True,
        "analyst_notes": "Priority lead under investigation. Multiple peel chains observed."
    })
    assert rep_resp.status_code == 200
    report = rep_resp.json()

    # Verify all sections are present
    assert report["title"] == "Forensic Lead Intelligence Brief: Comprehensive Audit"
    assert report["entity_id"] == "addr_target_investigation"
    assert report["disclaimer"] != ""
    assert "MANDATORY" in report["disclaimer"] or "DISCLAIMER" in report["disclaimer"]
    assert report["risk_score"] >= 0
    assert report["severity"] in ("LOW", "MEDIUM", "HIGH", "CRITICAL")
    assert report["anomaly_score"] >= 0.0

    # Verify transaction evidence contains all 25 records (NOT truncated to 10 or 5!)
    assert len(report["transaction_evidence"]) == 25
    assert len(report["network_observations"]) >= 25

    # Verify markdown content also includes all 25 transactions
    md = report["markdown_content"]
    assert "tx_report_test_0000" in md
    assert "tx_report_test_0024" in md
    assert "MANDATORY" in md or "DISCLAIMER" in md
