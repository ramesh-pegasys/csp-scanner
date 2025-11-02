# app/cloud/__init__.py
"""
Cloud session abstraction layer for multi-cloud support.
Provides unified interface for AWS, Azure, and GCP sessions.
"""

from app.cloud.base import CloudProvider, CloudSession
from app.cloud.aws_session import AWSSession
from app.cloud.azure_session import AzureSession
from app.cloud.gcp_session import GCPSession

__all__ = [
    "CloudProvider",
    "CloudSession",
    "AWSSession",
    "AzureSession",
    "GCPSession",
]
