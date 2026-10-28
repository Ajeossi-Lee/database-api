import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.settings.config import settings


@pytest.fixture(scope="session")
def client():
    """Create a test client for the application."""
    return TestClient(app)


def test_health_endpoint(client):
    """Test that health endpoints are working."""
    response = client.get("/healthz")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"


def test_readiness_endpoint(client):
    """Test that readiness endpoint is working."""
    response = client.get("/readyz")
    assert response.status_code == 200
    assert response.json()["status"] == "ready"


def test_request_id_header(client):
    """Test that request ID is properly set in response."""
    response = client.get("/healthz")
    assert response.status_code == 200
    assert "X-Request-ID" in response.headers


def test_config_loaded():
    """Test that settings are properly loaded."""
    assert settings.PROJECT_NAME == "Database API"
    assert settings.APP_ENV == "test"
    assert settings.DEBUG is False