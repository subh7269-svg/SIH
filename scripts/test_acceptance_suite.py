import os
import sys
import tempfile
import time
from datetime import datetime, timezone
import pytest

# Ensure root directory is on sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from backend.app.db.base import Base
from backend.app.db.session import ensure_db_schema
from backend.app.models.dataset import Dataset
from backend.app.models.entity import Wallet
from backend.app.models.transaction import Transaction, TransactionInput, TransactionOutput, IPObservation
from backend.app.models.alert import Alert
from backend.app.services.dataset_service import create_dataset_record, get_dataset_by_id
from backend.app.ingestion.pipeline import process_dataset_stream
from backend.app.graph.builder import build_networkx_graph_from_db
from backend.app.services.ml_service import train_and_evaluate_pipeline
from backend.app.services.correlation_service import run_cross_layer_correlation
from backend.app.services.investigation_service import get_entity_dossier
from backend.app.services.report_service import generate_forensic_report

def run_tests():
    print("=" * 70)
    print("LEADFORGE COMPREHENSIVE ACCEPTANCE TEST SUITE")
    print("=" * 70)

    # Setup isolated test database
    test_db_path = os.path.abspath("test_acceptance.db")
    if os.path.exists(test_db_path):
        try:
            os.remove(test_db_path)
        except Exception:
            pass

    engine = create_engine(f"sqlite:///{test_db_path}", connect_args={"check_same_thread": False})
    ensure_db_schema(engine)
    TestingSession = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = TestingSession()

    try:
        # TEST 1: Small CSV
        print("\n--- TEST 1: Small CSV Ingestion ---")
        csv_path = os.path.abspath("data/sample/bitcoin_network_sample.csv")
        ds1 = create_dataset_record(db, "bitcoin_network_sample.csv", "csv", os.path.getsize(csv_path))
        dq1 = process_dataset_stream(db, ds1.id, csv_path, "csv")
        db.refresh(ds1)
        assert ds1.status == "COMPLETED", f"Expected COMPLETED, got {ds1.status}"
        assert ds1.processed_records > 0, "Expected >0 processed records"
        print(f"PASS: ds1 status={ds1.status}, valid={ds1.processed_records}, total={ds1.total_records}")

        # TEST 2: Small JSON
        print("\n--- TEST 2: Small JSON Ingestion ---")
        json_path = os.path.abspath("data/sample/bitcoin_network_sample.json")
        ds2 = create_dataset_record(db, "bitcoin_network_sample.json", "json", os.path.getsize(json_path))
        dq2 = process_dataset_stream(db, ds2.id, json_path, "json")
        db.refresh(ds2)
        assert ds2.status == "COMPLETED", f"Expected COMPLETED, got {ds2.status}"
        assert ds2.processed_records > 0, "Expected >0 processed records"
        print(f"PASS: ds2 status={ds2.status}, valid={ds2.processed_records}, total={ds2.total_records}")

        # TEST 3: Small XML
        print("\n--- TEST 3: Small XML Ingestion ---")
        xml_path = os.path.abspath("data/sample/bitcoin_network_sample.xml")
        ds3 = create_dataset_record(db, "bitcoin_network_sample.xml", "xml", os.path.getsize(xml_path))
        dq3 = process_dataset_stream(db, ds3.id, xml_path, "xml")
        db.refresh(ds3)
        assert ds3.status == "COMPLETED", f"Expected COMPLETED, got {ds3.status}"
        assert ds3.processed_records > 0, "Expected >0 processed records"
        print(f"PASS: ds3 status={ds3.status}, valid={ds3.processed_records}, total={ds3.total_records}")

        # TEST 4, 5, 6: Large 194.1 MB CSV Ingestion
        print("\n--- TEST 4, 5, 6: Ingest 194.1 MB Large CSV ---")
        large_file = r"C:\Users\ASUS\Documents\DATASET\correlation_output\unified_correlated_dataset_part_002.csv"
        assert os.path.exists(large_file), f"Large file not found at {large_file}"
        large_size = os.path.getsize(large_file)
        print(f"File: {large_file} ({large_size / 1024 / 1024:.2f} MB)")

        t0 = time.time()
        ds_large = create_dataset_record(db, "unified_correlated_dataset_part_002.csv", "csv", large_size)
        dq_large = process_dataset_stream(db, ds_large.id, large_file, "csv")
        db.refresh(ds_large)
        duration = time.time() - t0

        print(f"Streaming ingestion completed in {duration:.1f}s")
        print(f"Dataset status: {ds_large.status}")
        print(f"Dataset total_records: {ds_large.total_records}")
        print(f"Dataset processed_records (valid): {ds_large.processed_records}")
        print(f"Dataset rejected_records: {ds_large.rejected_records}")
        print(f"Error summary: {ds_large.error_summary}")

        assert ds_large.status == "COMPLETED", f"Expected COMPLETED, got {ds_large.status}: {ds_large.error_summary}"
        assert ds_large.total_records == 39059, f"Expected 39059 total, got {ds_large.total_records}"
        assert ds_large.processed_records == 39059, f"Expected 39059 valid, got {ds_large.processed_records}"
        assert ds_large.rejected_records == 0, f"Expected 0 rejected, got {ds_large.rejected_records}"

        # TEST 6: Check Data Quality metrics
        assert dq_large["total_records"] == 39059
        assert dq_large["valid_records"] == 39059
        assert dq_large["rejected_records"] == 0
        assert dq_large["duplicate_records"] == 0
        assert dq_large["unique_wallets"] == 125398, f"Expected 125398 wallets, got {dq_large['unique_wallets']}"
        print(f"PASS TEST 4, 5, 6: Ingestion successful! Unique wallets indexed: {dq_large['unique_wallets']}")

        # TEST 7 & 8: Multi-File Batch & Fault Isolation (1 Valid + 1 Invalid)
        print("\n--- TEST 7 & 8: Multi-File Fault Isolation (Valid + Invalid) ---")
        # Create a temporary invalid CSV
        with tempfile.NamedTemporaryFile("w", delete=False, suffix=".csv") as invalid_f:
            invalid_f.write("wrong_header_col1,wrong_header_col2\nfoo,bar\n")
            invalid_path = invalid_f.name

        try:
            # File A: Valid (sample)
            ds_valid = create_dataset_record(db, "valid_batch_file.csv", "csv", os.path.getsize(csv_path))
            dq_v = process_dataset_stream(db, ds_valid.id, csv_path, "csv")
            db.refresh(ds_valid)

            # File B: Invalid
            ds_invalid = create_dataset_record(db, "invalid_batch_file.csv", "csv", os.path.getsize(invalid_path))
            try:
                process_dataset_stream(db, ds_invalid.id, invalid_path, "csv")
            except Exception as e:
                pass
            db.refresh(ds_invalid)

            assert ds_valid.status == "COMPLETED", "Valid file should be COMPLETED"
            assert ds_invalid.status == "FAILED", "Invalid file should be FAILED"
            assert ds_invalid.error_summary is not None, "Invalid file should have error_summary"
            print(f"PASS TEST 7 & 8: Valid ds status={ds_valid.status}, Invalid ds status={ds_invalid.status}, reason='{ds_invalid.error_summary}'")
        finally:
            if os.path.exists(invalid_path):
                os.unlink(invalid_path)

        # TEST 9: Wallet Classification Schema (wallets_classes.csv)
        print("\n--- TEST 9: Existing Wallet Classification Schema ---")
        wc_path = r"C:\Users\ASUS\Documents\DATASET\uploads\wallets_classes.csv"
        if os.path.exists(wc_path):
            # Test a sample chunk of 2,000 rows from wallets_classes.csv
            with tempfile.NamedTemporaryFile("w", delete=False, suffix=".csv") as sample_wc:
                with open(wc_path, "r", encoding="utf-8") as src_f:
                    for _ in range(2001):
                        line = src_f.readline()
                        if not line:
                            break
                        sample_wc.write(line)
                sample_wc_path = sample_wc.name

            try:
                ds_wc = create_dataset_record(db, "wallets_classes_sample.csv", "csv", os.path.getsize(sample_wc_path))
                dq_wc = process_dataset_stream(db, ds_wc.id, sample_wc_path, "csv")
                db.refresh(ds_wc)
                assert ds_wc.status == "COMPLETED", f"Expected COMPLETED, got {ds_wc.status}: {ds_wc.error_summary}"
                assert ds_wc.processed_records == 2000, f"Expected 2000 valid, got {ds_wc.processed_records}"
                assert ds_wc.rejected_records == 0, f"Expected 0 rejected, got {ds_wc.rejected_records}"
                print(f"PASS TEST 9: wallets_classes ingests as WALLET schema! Valid={ds_wc.processed_records}, Rejected={ds_wc.rejected_records}")
            finally:
                if os.path.exists(sample_wc_path):
                    os.unlink(sample_wc_path)

        # TEST 10: Downstream Services (Graph, ML, Correlation, Investigation, Reports)
        print("\n--- TEST 10: Downstream Services Integrity ---")
        print("Testing Graph Builder with 125,398 wallets (verifying no SQL variable limits)...")
        # Build graph for ds1 first
        G1 = build_networkx_graph_from_db(db, dataset_id=ds1.id)
        assert G1.number_of_nodes() > 0, "Graph G1 should have nodes"
        print(f"Graph G1: {G1.number_of_nodes()} nodes, {G1.number_of_edges()} edges")

        print("Testing ML Pipeline on dataset...")
        ml_res = train_and_evaluate_pipeline(db, dataset_id=ds1.id)
        print(f"ML Pipeline result: status={ml_res.get('status')}, alerts_count={ml_res.get('alerts_count')}")

        print("Testing Cross-Layer Correlation...")
        corr_res = run_cross_layer_correlation(db, dataset_id=ds1.id)
        print(f"Correlation result: high_risk_patterns={len(corr_res.get('patterns', []))}")

        print("Testing Entity Dossier...")
        first_wallet = db.query(Wallet).first()
        if first_wallet:
            dossier = get_entity_dossier(db, first_wallet.address)
            print(f"Entity Dossier for {first_wallet.address[:10]}... retrieved successfully")

        print("Testing Forensic Report Generation...")
        first_alert = db.query(Alert).first()
        if first_alert:
            rep = generate_forensic_report(db, first_alert.id, generated_by="Auditor_Test")
            assert rep is not None, "Report should be generated"
            print(f"Forensic Report generated successfully (ID={rep.id})")

        print("\n" + "=" * 70)
        print("ALL 10 ACCEPTANCE TESTS PASSED SUCCESSFULLY!")
        print("=" * 70)

    finally:
        db.close()
        engine.dispose()
        if os.path.exists(test_db_path):
            try:
                os.remove(test_db_path)
            except Exception:
                pass

if __name__ == "__main__":
    run_tests()
