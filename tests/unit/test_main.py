"""
Unit tests for main FastAPI application.
Tests application initialization and basic endpoints.
"""

import pytest
from fastapi.testclient import TestClient
from app.main import app


@pytest.fixture
def client():
    """Create a test client for the FastAPI application."""
    return TestClient(app)


def test_app_initialization():
    """Test that the FastAPI app initializes correctly."""
    assert app.title == "Cognitive AI Learning Platform"
    assert app.version == "1.0.0"


def test_health_check_endpoint(client):
    """Test the health check endpoint."""
    response = client.get("/health")
    
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["service"] == "Cognitive AI Learning Platform"
    assert data["version"] == "1.0.0"


def test_root_endpoint(client):
    """Test the root endpoint."""
    response = client.get("/")
    
    assert response.status_code == 200
    data = response.json()
    assert "message" in data
    assert "Cognitive AI Learning Platform" in data["message"]
    assert data["docs"] == "/docs"
    assert data["redoc"] == "/redoc"


def test_docs_endpoint_accessible(client):
    """Test that the OpenAPI docs endpoint is accessible."""
    response = client.get("/docs")
    assert response.status_code == 200


def test_openapi_schema_accessible(client):
    """Test that the OpenAPI schema is accessible."""
    response = client.get("/openapi.json")
    assert response.status_code == 200
    schema = response.json()
    assert schema["info"]["title"] == "Cognitive AI Learning Platform"
