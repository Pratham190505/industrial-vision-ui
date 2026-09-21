from unittest.mock import AsyncMock, patch
from fastapi.testclient import TestClient


def test_root_endpoint(client: TestClient):
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "WarehouseVision AI"
    assert data["status"] == "online"
    assert "health_check" in data


def test_api_health_endpoint(client: TestClient):
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["version"] == "1.0.0"
    assert "WarehouseVision AI" in data["service"]


def test_database_health_connected(client: TestClient):
    with patch("app.api.routes.health.check_database_health", new_callable=AsyncMock) as mock_ping:
        mock_ping.return_value = True
        response = client.get("/api/v1/health/database")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["database"] == "connected"


def test_database_health_disconnected(client: TestClient):
    with patch("app.api.routes.health.check_database_health", new_callable=AsyncMock) as mock_ping:
        mock_ping.return_value = False
        response = client.get("/api/v1/health/database")
        assert response.status_code == 503
        data = response.json()
        assert data["status"] == "degraded"
        assert data["database"] == "disconnected"
