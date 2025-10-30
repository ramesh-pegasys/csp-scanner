# app/cloud/gcp_api_check.py
"""
Utility to check if a GCP API is enabled for a project.
"""
import requests
import logging
from typing import Optional, Any

logger = logging.getLogger(__name__)

API_SERVICE_MAP = {
    "compute": "compute.googleapis.com",
    "storage": "storage.googleapis.com",
    "kubernetes": "container.googleapis.com",
    "networking": "compute.googleapis.com",
    "iam": "iam.googleapis.com",
    "filestore": "file.googleapis.com",
    "iap": "iap.googleapis.com",
    "resourcemanager": "cloudresourcemanager.googleapis.com",
    "billing": "cloudbilling.googleapis.com",
    "bigquery": "bigquery.googleapis.com",
    "cloudbuild": "cloudbuild.googleapis.com",
    "run": "run.googleapis.com",
    "firestore": "firestore.googleapis.com",
    "bigtable": "bigtableadmin.googleapis.com",
    "pubsub": "pubsub.googleapis.com",
    "dataflow": "dataflow.googleapis.com",
    "dataproc": "dataproc.googleapis.com",
    "spanner": "spanner.googleapis.com",
    "memorystore": "redis.googleapis.com",
    "dns": "dns.googleapis.com",
    "logging": "logging.googleapis.com",
    "monitoring": "monitoring.googleapis.com",
    "tasks": "cloudtasks.googleapis.com",
    "scheduler": "cloudscheduler.googleapis.com",
    "functions": "cloudfunctions.googleapis.com",
    "armor": "compute.googleapis.com",
    "interconnect": "compute.googleapis.com",
    "loadbalancer": "compute.googleapis.com",
}


def get_gcp_access_token(credentials) -> Optional[str]:
    """
    Get an OAuth2 access token from google-auth credentials object.
    """
    try:
        # google-auth credentials have a 'refresh' method and 'token' property
        import google.auth.transport.requests

        request = google.auth.transport.requests.Request()
        credentials.refresh(request)
        return credentials.token
    except Exception as e:
        logger.error(f"Failed to get GCP access token: {e}")
        return None


def is_gcp_api_enabled(
    project_id: str, api_service: str, credentials: Optional[Any] = None
) -> bool:
    """
    Check if a GCP API is enabled for the given project using credentials.
    Args:
        project_id: GCP project ID
        api_service: Service name (e.g., 'compute.googleapis.com')
        credentials: google-auth credentials object
    Returns:
        True if enabled, False otherwise
    """
    url = f"https://serviceusage.googleapis.com/v1/projects/{project_id}/services/{api_service}"
    headers = {}
    access_token = None
    if credentials:
        access_token = get_gcp_access_token(credentials)
        if access_token:
            headers["Authorization"] = f"Bearer {access_token}"
    try:
        resp = requests.get(url, headers=headers, timeout=5)
        if resp.status_code == 200:
            data = resp.json()
            return data.get("state") == "ENABLED"
        else:
            logger.warning(
                f"Failed to check GCP API. Status: {resp.status_code}"
            )
            return False
    except Exception as e:
        logger.error(f"Error checking GCP API {api_service}: {e}")
        return False
