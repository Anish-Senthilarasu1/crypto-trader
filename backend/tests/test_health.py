"""
Tests for health check endpoint.
"""

from fastapi.testclient import TestClient

from backend.main import app

client = TestClient(app)


def test_health_check() -> None:
    """Test that health endpoint returns 200 and correct structure."""
    response = client.get("/health")

    assert response.status_code == 200

    data = response.json()
    assert data["status"] == "healthy"
    assert data["service"] == "aurora-trader-api"
    assert data["version"] == "0.1.0"
    assert "timestamp" in data


def test_health_check_structure() -> None:
    """Test health response has all required fields."""
    response = client.get("/health")
    data = response.json()

    required_fields = ["status", "timestamp", "service", "version"]
    for field in required_fields:
        assert field in data, f"Missing required field: {field}"
