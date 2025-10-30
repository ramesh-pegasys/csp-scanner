"""Tests for extraction endpoints"""

from fastapi.testclient import TestClient
from types import SimpleNamespace
import uuid


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


def test_trigger_extraction_success(client: TestClient, mock_orchestrator):
    """Test successful extraction trigger"""
    job_id = str(uuid.uuid4())
    mock_orchestrator.run_extraction.return_value = job_id

    payload = {"services": ["s3", "ec2"], "regions": ["us-east-1"], "batch_size": 50}

    response = client.post("/api/v1/extraction/trigger", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["job_id"] == job_id
    assert "started successfully" in data["message"]


def test_trigger_extraction_failure(client: TestClient, mock_orchestrator):
    """Test extraction trigger failure"""
    mock_orchestrator.run_extraction.side_effect = Exception("AWS Error")

    payload = {"services": ["s3"]}

    response = client.post("/api/v1/extraction/trigger", json=payload)
    assert response.status_code == 500
    assert "AWS Error" in response.json()["detail"]


def test_get_job_status_found(client: TestClient, mock_orchestrator):
    """Test getting existing job status"""
    response = client.get("/api/v1/extraction/jobs/test-job")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == "test-job"
    assert data["status"] == "completed"


def test_get_job_status_not_found(client: TestClient, mock_orchestrator):
    """Test getting non-existent job status"""
    mock_orchestrator.get_job_status.return_value = None

    response = client.get("/api/v1/extraction/jobs/non-existent")
    assert response.status_code == 404
    assert "Job not found" in response.json()["detail"]


def test_list_jobs(client: TestClient, mock_orchestrator):
    """Test listing jobs"""
    response = client.get("/api/v1/extraction/jobs")
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

    response = client.get("/api/v1/extraction/services")
    assert response.status_code == 200
    data = response.json()
    assert data["total_services"] == 2
    assert "aws" in data["services_by_provider"]
    service_names = [item["service"] for item in data["services_by_provider"]["aws"]]
    assert service_names == ["s3", "ec2"]


def test_trigger_extraction_invalid_provider(client: TestClient):
    response = client.post("/api/v1/extraction/trigger", json={"provider": "digitalocean"})
    assert response.status_code == 400
    assert "Invalid provider" in response.json()["detail"]


def test_trigger_extraction_provider_validates_services(
    client: TestClient, mock_registry
):
    mock_registry.get_extractors.return_value = [_make_extractor("s3")]

    payload = {"provider": "aws", "services": ["ec2"]}
    response = client.post("/api/v1/extraction/trigger", json=payload)
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

    response = client.post("/api/v1/extraction/trigger", json={"provider": "aws"})
    assert response.status_code == 200
    args = mock_orchestrator.run_extraction.await_args.kwargs
    assert args["services"] == ["s3", "ec2"]


def test_list_services_invalid_provider(client: TestClient):
    response = client.get("/api/v1/extraction/services", params={"provider": "digitalocean"})
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

    response = client.get("/api/v1/extraction/services", params={"provider": "azure"})
    assert response.status_code == 200
    data = response.json()
    assert data["total_services"] == 1
    assert list(data["services_by_provider"].keys()) == ["azure"]
    assert data["services_by_provider"]["azure"][0]["service"] == "compute"


def test_list_providers(client: TestClient, mock_registry):
    mock_registry.get_extractors.return_value = [
        _make_extractor("s3", "aws"),
        _make_extractor("compute", "azure"),
    ]

    response = client.get("/api/v1/extraction/providers")
    assert response.status_code == 200
    providers = set(response.json()["providers"])
    assert providers == {"aws", "azure"}
