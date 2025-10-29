# app/extractors/gcp/__init__.py
"""
GCP resource extractors.
"""

from app.extractors.gcp.compute import GCPComputeExtractor
from app.extractors.gcp.storage import GCPStorageExtractor

__all__ = [
    "GCPComputeExtractor",
    "GCPStorageExtractor",
]
