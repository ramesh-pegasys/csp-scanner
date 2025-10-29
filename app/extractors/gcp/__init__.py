# app/extractors/gcp/__init__.py
"""
GCP resource extractors.
"""

from app.extractors.gcp.compute import GCPComputeExtractor
from app.extractors.gcp.storage import GCPStorageExtractor
from app.extractors.gcp.networking import GCPNetworkingExtractor
from app.extractors.gcp.kubernetes import GCPKubernetesExtractor
from app.extractors.gcp.iam import GCPIAMExtractor

__all__ = [
    "GCPComputeExtractor",
    "GCPStorageExtractor",
    "GCPNetworkingExtractor",
    "GCPKubernetesExtractor",
    "GCPIAMExtractor",
]
