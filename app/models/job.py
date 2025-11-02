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
