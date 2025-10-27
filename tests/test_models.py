"""Tests for models"""
import pytest
from datetime import datetime
from app.models.job import Job, JobStatus
from app.models.artifact import CloudArtifact


def test_job_model():
    """Test Job model creation and validation"""
    job = Job(
        id="test-job-123",
        status=JobStatus.RUNNING,
        started_at=datetime(2023, 1, 1, 12, 0, 0),
        services=["s3", "ec2"],
        total_artifacts=10,
        successful_artifacts=8,
        failed_artifacts=2,
        errors=["Error 1", "Error 2"]
    )

    assert job.id == "test-job-123"
    assert job.status == JobStatus.RUNNING
    assert job.started_at == datetime(2023, 1, 1, 12, 0, 0)
    assert job.services == ["s3", "ec2"]
    assert job.total_artifacts == 10
    assert job.successful_artifacts == 8
    assert job.failed_artifacts == 2
    assert job.errors == ["Error 1", "Error 2"]
    assert job.completed_at is None


def test_job_model_defaults():
    """Test Job model with default values"""
    job = Job(
        id="test-job-456",
        status=JobStatus.PENDING,
        started_at=datetime(2023, 1, 1, 12, 0, 0),
        services=["s3"]
    )

    assert job.total_artifacts == 0
    assert job.successful_artifacts == 0
    assert job.failed_artifacts == 0
    assert job.errors == []


def test_job_status_enum():
    """Test JobStatus enum values"""
    assert JobStatus.PENDING == "pending"
    assert JobStatus.RUNNING == "running"
    assert JobStatus.COMPLETED == "completed"
    assert JobStatus.FAILED == "failed"


def test_cloud_artifact_model():
    """Test CloudArtifact model"""
    artifact = CloudArtifact(
        resource_id="my-bucket",
        resource_type="bucket",
        service="s3",
        region="us-east-1",
        account_id="123456789012",
        configuration={"name": "my-bucket", "created": "2023-01-01"},
        raw={"raw_data": "value"},
        extracted_at=datetime(2023, 1, 1, 12, 0, 0)
    )

    assert artifact.resource_id == "my-bucket"
    assert artifact.resource_type == "bucket"
    assert artifact.service == "s3"
    assert artifact.region == "us-east-1"
    assert artifact.account_id == "123456789012"
    assert artifact.configuration == {"name": "my-bucket", "created": "2023-01-01"}
    assert artifact.raw == {"raw_data": "value"}
    assert artifact.extracted_at == datetime(2023, 1, 1, 12, 0, 0)