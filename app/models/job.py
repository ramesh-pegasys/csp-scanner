# app/models/job.py
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
from enum import Enum


class JobStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class Job(BaseModel):
    id: str
    status: JobStatus
    started_at: datetime
    completed_at: Optional[datetime] = None
    services: List[str]
    total_artifacts: int = 0
    successful_artifacts: int = 0
    failed_artifacts: int = 0
    errors: List[str] = []

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}
        schema_extra = {
            "example": {
                "id": "job-123",
                "status": "completed",
                "started_at": "2025-11-02T10:00:00Z",
                "completed_at": "2025-11-02T10:05:00Z",
                "services": ["EC2", "S3"],
                "total_artifacts": 10,
                "successful_artifacts": 9,
                "failed_artifacts": 1,
                "errors": ["Timeout on S3"],
            }
        }
