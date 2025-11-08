# app/models/artifact.py
from pydantic import BaseModel
from typing import Dict, Any, Optional
from datetime import datetime


class CloudArtifact(BaseModel):
    """Standardized cloud artifact model"""

    resource_id: str
    resource_type: str
    service: str
    region: Optional[str] = None
    account_id: Optional[str] = None
    configuration: Dict[str, Any]
    raw: Dict[str, Any]
    extracted_at: Optional[datetime] = None

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}
        json_schema_extra = {
            "example": {
                "resource_id": "i-1234567890abcdef0",
                "resource_type": "ec2",
                "service": "EC2",
                "region": "us-west-2",
                "account_id": "123456789012",
                "configuration": {"instanceType": "t2.micro"},
                "raw": {"rawData": "..."},
                "extracted_at": "2025-11-02T12:00:00Z",
            }
        }
