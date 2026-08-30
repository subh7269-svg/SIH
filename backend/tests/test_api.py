import pytest
from fastapi.testclient import TestClient

def test_api_health(client: TestClient):
    resp = client.get("/api/v1/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "healthy"

def test_api_ready(client: TestClient):
    resp = client.get("/api/v1/ready")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ready"

def test_api_1click_demo(client: TestClient):
    # Execute 1-click demo
    resp = client.post("/api/v1/demo/run?seed=42")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "SUCCESS"
    assert "dataset_id" in data
    assert data["ml_result"]["alerts_generated"] > 0

    # Test alerts list
    alerts_resp = client.get("/api/v1/alerts")
    assert alerts_resp.status_code == 200
    alerts_data = alerts_resp.json()
    assert alerts_data["total"] > 0
    top_alert = alerts_data["alerts"][0]

    # Test alert triage update
    alert_id = top_alert["id"]
    patch_resp = client.patch(f"/api/v1/alerts/{alert_id}/status", json={"status": "REVIEWING", "note": "Investigating peel chain anomaly"})
    assert patch_resp.status_code == 200
    assert patch_resp.json()["status"] == "REVIEWING"

    # Test entity search
    search_resp = client.get("/api/v1/entities/search?q=bc1q")
    assert search_resp.status_code == 200
    assert search_resp.json()["total_results"] > 0

    # Test entity dossier
    target_wallet = top_alert["entity_id"]
    dossier_resp = client.get(f"/api/v1/entities/{target_wallet}")
    assert dossier_resp.status_code == 200
    assert dossier_resp.json()["entity_id"] == target_wallet

    # Test graph endpoint
    graph_resp = client.get(f"/api/v1/graph/entity/{target_wallet}?k=2")
    assert graph_resp.status_code == 200
    assert graph_resp.json()["node_count"] > 0

    # Test report generation
    rep_resp = client.post("/api/v1/reports/generate", json={
        "title": "Forensic Lead Brief: Target Alpha",
        "entity_id": target_wallet,
        "include_evidence": True,
        "analyst_notes": "High priority anomaly detected during demo scenario."
    })
    assert rep_resp.status_code == 200
    rep_data = rep_resp.json()
    assert "report_id" in rep_data
    assert "DISCLAIMER" in rep_data["markdown_content"]
