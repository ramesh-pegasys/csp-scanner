"""Tests for schedule endpoints"""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import Mock


def test_create_schedule_success(client: TestClient, mock_scheduler):
    """Test successful schedule creation"""
    payload = {
        "name": "daily-extraction",
        "cron_expression": "0 0 * * *",
        "services": ["s3", "ec2"],
        "batch_size": 100
    }

    response = client.post("/api/v1/schedules/", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "created successfully" in data["message"]
    assert data["cron"] == "0 0 * * *"


def test_create_schedule_invalid_cron(client: TestClient, mock_scheduler):
    """Test schedule creation with invalid cron"""
    mock_scheduler.add_job.side_effect = Exception("Wrong number of fields; got 1, expected 5 or 6")

    payload = {
        "name": "invalid-schedule",
        "cron_expression": "invalid",
        "services": ["s3"]
    }

    response = client.post("/api/v1/schedules/", json=payload)
    assert response.status_code == 400
    assert "Wrong number of fields" in response.json()["detail"]


def test_list_schedules(client: TestClient, mock_scheduler):
    """Test listing schedules"""
    mock_job = Mock()
    mock_job.id = "schedule1"
    mock_job.name = "Daily Backup"
    mock_job.next_run_time = None
    mock_scheduler.get_jobs.return_value = [mock_job]

    response = client.get("/api/v1/schedules/")
    assert response.status_code == 200
    data = response.json()
    assert len(data["schedules"]) == 1
    assert data["schedules"][0]["id"] == "schedule1"
    assert data["schedules"][0]["name"] == "Daily Backup"


def test_delete_schedule_success(client: TestClient, mock_scheduler):
    """Test successful schedule deletion"""
    response = client.delete("/api/v1/schedules/daily-extraction")
    assert response.status_code == 200
    data = response.json()
    assert "deleted successfully" in data["message"]


def test_delete_schedule_not_found(client: TestClient, mock_scheduler):
    """Test deleting non-existent schedule"""
    mock_scheduler.remove_job.side_effect = Exception("Job not found")

    response = client.delete("/api/v1/schedules/non-existent")
    assert response.status_code == 404
    assert "Schedule not found" in response.json()["detail"]


def test_pause_schedule_success(client: TestClient, mock_scheduler):
    """Test successful schedule pause"""
    response = client.put("/api/v1/schedules/daily-extraction/pause")
    assert response.status_code == 200
    data = response.json()
    assert "paused successfully" in data["message"]


def test_pause_schedule_not_found(client: TestClient, mock_scheduler):
    mock_scheduler.pause_job.side_effect = Exception("missing")

    response = client.put("/api/v1/schedules/unknown/pause")
    assert response.status_code == 404
    assert "missing" in response.json()["detail"]


def test_resume_schedule_success(client: TestClient, mock_scheduler):
    """Test successful schedule resume"""
    response = client.put("/api/v1/schedules/daily-extraction/resume")
    assert response.status_code == 200
    data = response.json()
    assert "resumed successfully" in data["message"]


def test_resume_schedule_not_found(client: TestClient, mock_scheduler):
    mock_scheduler.resume_job.side_effect = Exception("missing")

    response = client.put("/api/v1/schedules/unknown/resume")
    assert response.status_code == 404
    assert "missing" in response.json()["detail"]
