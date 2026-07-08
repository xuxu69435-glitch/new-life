from fastapi.testclient import TestClient

from app.main import app


def test_health_endpoint_reports_repository_and_rules() -> None:
    client = TestClient(app)
    response = client.get("/health")
    assert response.status_code == 200
    payload = response.json()
    assert "status" in payload
    assert "environment" in payload
    assert "repository_type" in payload
    assert "rules_loaded" in payload
    assert "database_connected" in payload
    assert "password" not in payload
    assert "DATABASE_URL" not in str(payload)
