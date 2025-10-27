"""Tests for extraction endpoints"""

from fastapi.testclient import TestClient
import uuid


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
    mock_registry.list_services.return_value = ["s3", "ec2", "lambda", "rds"]

    response = client.get("/api/v1/extraction/services")
    assert response.status_code == 200
    data = response.json()
    assert data["services"] == ["s3", "ec2", "lambda", "rds"]
