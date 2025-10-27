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
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }