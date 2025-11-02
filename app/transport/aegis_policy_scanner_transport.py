from typing import Dict, Any, Optional
import httpx
import os
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
)
from app.core.exceptions import TransportError
import logging

logger = logging.getLogger(__name__)


class AegisPolicyScannerTransport:
    """
    Transport for invoking Aegis Policy Scanning API endpoint.
    """

    def __init__(self, transport_config: dict, aegis_token_env: str = "AEGIS_TOKEN"):
        # Expect config as transport node
        self.aegis_host = transport_config.get("aegis_host")
        self.policy_name = transport_config.get("policy_name")
        self.max_concurrent_requests = transport_config.get(
            "max_concurrent_requests", 5
        )
        self.max_retries = transport_config.get("max_retries", 3)
        # Static labels from config
        static_labels = transport_config.get("labels", {})
        # Dynamic labels for cloud resources

        self.labels = self._generate_cloud_labels(transport_config, static_labels)

        self.aegis_token = os.getenv(aegis_token_env)
        if not self.aegis_token:
            raise ValueError(
                f"Aegis token not found in environment variable: {aegis_token_env}"
            )
        self.endpoint_url = (
            f"https://{self.aegis_host}/api/eval/policies/{self.policy_name}"
        )
        self.headers = {
            "Content-Type": "application/x-yaml",
            "Authorization": f"Bearer {self.aegis_token}",
        }
        # Proxy support for AsyncClient
        proxy_url = os.getenv("HTTPS_PROXY") or os.getenv("HTTP_PROXY")
        if proxy_url:
            self.client = httpx.AsyncClient(proxy=proxy_url)
        else:
            self.client = httpx.AsyncClient()
        # NO_PROXY is handled by httpx via environment variable

        # Throttling
        self._semaphore = None
        if self.max_concurrent_requests > 0:
            import asyncio

            self._semaphore = asyncio.Semaphore(self.max_concurrent_requests)

    def _generate_cloud_labels(self, config: dict, static_labels: dict) -> dict:
        labels = dict(static_labels)
        # AWS
        aws_accounts = config.get("aws_accounts", [])
        for account in aws_accounts:
            account_id = account.get("account_id")
            for region in account.get("regions", []):
                region_name = region["name"] if isinstance(region, dict) else region
                policy_name = (
                    region.get("policy_name") if isinstance(region, dict) else None
                )
                labels_key = f"aws_{account_id}_{region_name}"
                labels_value = f"account:{account_id},region:{region_name}"
                if policy_name:
                    labels_value += f",policy:{policy_name}"
                labels[labels_key] = labels_value
        # GCP
        gcp_projects = config.get("gcp_projects", [])
        for project in gcp_projects:
            project_id = project.get("project_id")
            for region in project.get("regions", []):
                region_name = region["name"] if isinstance(region, dict) else region
                policy_name = (
                    region.get("policy_name") if isinstance(region, dict) else None
                )
                labels_key = f"gcp_{project_id}_{region_name}"
                labels_value = f"project:{project_id},region:{region_name}"
                if policy_name:
                    labels_value += f",policy:{policy_name}"
                labels[labels_key] = labels_value
        # Azure
        azure_subs = config.get("azure_subscriptions", [])
        for sub in azure_subs:
            sub_id = sub.get("subscription_id")
            for location in sub.get("locations", []):
                location_name = (
                    location["name"] if isinstance(location, dict) else location
                )
                policy_name = (
                    location.get("policy_name") if isinstance(location, dict) else None
                )
                labels_key = f"azure_{sub_id}_{location_name}"
                labels_value = f"subscription:{sub_id},location:{location_name}"
                if policy_name:
                    labels_value += f",policy:{policy_name}"
                labels[labels_key] = labels_value
            return labels
        return labels
        self.headers = {
            "Content-Type": "application/x-yaml",
            "Authorization": f"Bearer {self.aegis_token}",
        }
        # Proxy support for AsyncClient
        proxy_url = os.getenv("HTTPS_PROXY") or os.getenv("HTTP_PROXY")
        if proxy_url:
            self.client = httpx.AsyncClient(proxy=proxy_url)
        else:
            self.client = httpx.AsyncClient()
        # NO_PROXY is handled by httpx via environment variable

        # Throttling
        self._semaphore = None
        if self.max_concurrent_requests > 0:
            import asyncio

            self._semaphore = asyncio.Semaphore(self.max_concurrent_requests)

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((httpx.TimeoutException, httpx.NetworkError)),
        reraise=True,
    )
    async def send(
        self, input_data: Dict[str, Any], labels: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Send extraction data to Aegis Policy Scanner API.
        Args:
            input_data: Extraction JSON data
            labels: Optional dictionary of labels (overrides config)
        Returns:
            Response from Aegis Policy Scanner
        Raises:
            TransportError: If send fails
        """
        use_labels = labels if labels is not None else self.labels
        yaml_body = self._build_yaml(use_labels, input_data)
        try:
            if self._semaphore:
                async with self._semaphore:
                    response = await self.client.post(
                        self.endpoint_url,
                        content=yaml_body,
                        headers=self.headers,
                    )
            else:
                response = await self.client.post(
                    self.endpoint_url,
                    content=yaml_body,
                    headers=self.headers,
                )
            response.raise_for_status()
            logger.debug(f"Aegis policy scan successful for policy {self.policy_name}")
            return response.json()
        except Exception as e:
            logger.error(f"Aegis policy scan failed: {e}")
            raise TransportError(f"Aegis policy scan failed: {str(e)}")

    def _build_yaml(self, labels: Dict[str, Any], input_data: Dict[str, Any]) -> str:
        import yaml

        # yaml_dict is not used
        # inputData must be a YAML block string
        # So we use yaml.dump for inputData, then insert as block
        labels_yaml = yaml.dump({"labels": labels}, default_flow_style=False)
        input_yaml = yaml.dump(input_data, default_flow_style=False)
        return f"labels:\n{labels_yaml.split('labels:')[1].strip()}\ninputData: |-\n{input_yaml}"

    async def close(self):
        if self.client is not None:
            await self.client.aclose()
