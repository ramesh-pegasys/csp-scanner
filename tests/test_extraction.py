"""Tests for extraction endpoints"""

from datetime import datetime, timedelta
import os
import uuid
from types import SimpleNamespace

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from jose import jwt

from app.api.routes import extraction


def _make_extractor(service: str, provider: str = "aws") -> SimpleNamespace:
    return SimpleNamespace(
        cloud_provider=provider,
        metadata=SimpleNamespace(
            service_name=service,
            description=f"Extracts {service}",
            resource_types=[service],
            version="1.0.0",
        ),
    )


# Dynamically generate a valid JWT for tests
def generate_test_jwt():
    secret = os.getenv("JWT_SECRET_KEY", "your-secret-key")
    algorithm = os.getenv("JWT_ALGORITHM", "HS256")
    expire = datetime.utcnow() + timedelta(days=1)
    payload = {"api": "access", "exp": expire}
    return jwt.encode(payload, secret, algorithm=algorithm)


def auth_headers():
    token = generate_test_jwt()
    return {"Authorization": f"Bearer {token}"}


def test_custom_openapi_adds_security_and_servers():
    app = FastAPI()
    app.include_router(extraction.router, prefix="/api/v1/extraction")

    schema = extraction.custom_openapi(app)

    assert "BearerAuth" in schema["components"]["securitySchemes"]
    assert schema["servers"] == [
        {
            "url": "https://localhost:8443",
            "description": "Local HTTPS (self-signed certs)",
        }
    ]

    # Call again to ensure cached schema path is exercised
    assert extraction.custom_openapi(app) is schema


def test_verify_jwt_token_success(monkeypatch):
    monkeypatch.setattr(extraction, "SECRET_KEY", "unit-secret")
    monkeypatch.setattr(extraction, "ALGORITHM", "HS256")

    token = jwt.encode({"sub": "tester"}, "unit-secret", algorithm="HS256")

    payload = extraction.verify_jwt_token(token=token)

    assert payload["sub"] == "tester"


def test_verify_jwt_token_invalid(monkeypatch):
    monkeypatch.setattr(extraction, "SECRET_KEY", "unit-secret")
    monkeypatch.setattr(extraction, "ALGORITHM", "HS256")

    invalid_token = "not-a-valid-token"

    with pytest.raises(extraction.HTTPException) as exc:
        extraction.verify_jwt_token(token=invalid_token)

    assert exc.value.status_code == 401


def test_trigger_extraction_success(client: TestClient, mock_orchestrator):
    """Test successful extraction trigger"""
    job_id = str(uuid.uuid4())
    mock_orchestrator.run_extraction.return_value = job_id

    payload = {"services": ["s3", "ec2"], "regions": ["us-east-1"], "batch_size": 50}

    response = client.post(
        "/api/v1/extraction/trigger", json=payload, headers=auth_headers()
    )
    assert response.status_code == 200
    data = response.json()
    assert data["job_id"] == job_id
    assert "started successfully" in data["message"]


def test_trigger_extraction_failure(client: TestClient, mock_orchestrator):
    """Test extraction trigger failure"""
    mock_orchestrator.run_extraction.side_effect = Exception("AWS Error")

    payload = {"services": ["s3"]}

    response = client.post(
        "/api/v1/extraction/trigger", json=payload, headers=auth_headers()
    )
    assert response.status_code == 500
    assert "AWS Error" in response.json()["detail"]


def test_get_job_status_found(client: TestClient, mock_orchestrator):
    """Test getting existing job status"""
    response = client.get("/api/v1/extraction/jobs/test-job", headers=auth_headers())
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == "test-job"
    assert data["status"] == "completed"


def test_get_job_status_not_found(client: TestClient, mock_orchestrator):
    """Test getting non-existent job status"""
    mock_orchestrator.get_job_status.return_value = None

    response = client.get(
        "/api/v1/extraction/jobs/non-existent", headers=auth_headers()
    )
    assert response.status_code == 404
    assert "Job not found" in response.json()["detail"]


def test_list_jobs(client: TestClient, mock_orchestrator):
    """Test listing jobs"""
    response = client.get("/api/v1/extraction/jobs", headers=auth_headers())
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["id"] == "job1"
    assert data[0]["status"] == "completed"


def test_list_services(client: TestClient, mock_registry):
    """Test listing available services"""
    mock_registry.get_extractors.return_value = [
        _make_extractor("s3"),
        _make_extractor("ec2"),
    ]

    response = client.get("/api/v1/extraction/services", headers=auth_headers())
    assert response.status_code == 200
    data = response.json()
    assert data["total_services"] == 2
    assert "aws" in data["services_by_provider"]
    service_names = [item["service"] for item in data["services_by_provider"]["aws"]]
    assert service_names == ["s3", "ec2"]


def test_trigger_extraction_invalid_provider(client: TestClient):
    response = client.post(
        "/api/v1/extraction/trigger",
        json={"provider": "digitalocean"},
        headers=auth_headers(),
    )
    assert response.status_code == 400
    assert "Invalid provider" in response.json()["detail"]


def test_trigger_extraction_provider_validates_services(
    client: TestClient, mock_registry
):
    # Override the side_effect to return only s3 extractor
    def _get_extractors_override(services=None, provider=None):
        extractors = [_make_extractor("s3")]
        if provider:
            provider_key = getattr(provider, "value", provider)
            extractors = [e for e in extractors if e.cloud_provider == provider_key]
        if services:
            extractors = [
                e for e in extractors if e.metadata.service_name in set(services)
            ]
        return extractors

    mock_registry.get_extractors.side_effect = _get_extractors_override

    payload = {"provider": "aws", "services": ["ec2"]}
    response = client.post(
        "/api/v1/extraction/trigger", json=payload, headers=auth_headers()
    )
    assert response.status_code == 400
    body = response.json()
    assert "Invalid services" in body["detail"]


def test_trigger_extraction_provider_autofills_services(
    client: TestClient, mock_registry, mock_orchestrator
):
    mock_registry.get_extractors.return_value = [
        _make_extractor("s3"),
        _make_extractor("ec2"),
    ]

    response = client.post(
        "/api/v1/extraction/trigger", json={"provider": "aws"}, headers=auth_headers()
    )
    assert response.status_code == 200
    args = mock_orchestrator.run_extraction.await_args.kwargs
    assert args["services"] == ["s3", "ec2"]


def test_list_services_invalid_provider(client: TestClient):
    response = client.get(
        "/api/v1/extraction/services",
        params={"provider": "digitalocean"},
        headers=auth_headers(),
    )
    assert response.status_code == 400


def test_list_services_filtered_by_provider(client: TestClient, mock_registry):
    aws_extractor = _make_extractor("s3", provider="aws")
    azure_extractor = _make_extractor("compute", provider="azure")

    def _side_effect(services=None, provider=None):
        provider_value = getattr(provider, "value", provider)
        data = [aws_extractor, azure_extractor]
        if provider_value:
            data = [e for e in data if e.cloud_provider == provider_value]
        if services:
            svc = set(services)
            data = [e for e in data if e.metadata.service_name in svc]
        return data

    mock_registry.get_extractors.side_effect = _side_effect

    response = client.get(
        "/api/v1/extraction/services",
        params={"provider": "azure"},
        headers=auth_headers(),
    )
    assert response.status_code == 200
    data = response.json()
    assert data["total_services"] == 1
    assert list(data["services_by_provider"].keys()) == ["azure"]
    assert data["services_by_provider"]["azure"][0]["service"] == "compute"


def test_list_providers(client: TestClient, mock_registry):
    # Override the side_effect to return both aws and azure extractors
    def _get_extractors_override(services=None, provider=None):
        extractors = [
            _make_extractor("s3", "aws"),
            _make_extractor("compute", "azure"),
        ]
        if provider:
            provider_key = getattr(provider, "value", provider)
            extractors = [e for e in extractors if e.cloud_provider == provider_key]
        if services:
            extractors = [
                e for e in extractors if e.metadata.service_name in set(services)
            ]
        return extractors

    mock_registry.get_extractors.side_effect = _get_extractors_override

    response = client.get("/api/v1/extraction/providers", headers=auth_headers())
    assert response.status_code == 200
    providers = set(response.json()["providers"])
    assert providers == {"aws", "azure"}
