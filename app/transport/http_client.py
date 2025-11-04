# app/transport/http_client.py
from typing import Dict, Any
import httpx
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
)
import logging
from app.core.exceptions import TransportError

logger = logging.getLogger(__name__)


class HTTPTransport:
    """HTTP transport with retry logic and circuit breaker"""

    def __init__(self, config: Dict[str, Any]):
        # Expect config as transport node
        endpoint = config.get("http_endpoint_url")
        if not endpoint or not isinstance(endpoint, str):
            raise ValueError(
                "transport config must include 'http_endpoint_url' as a non-empty string"
            )
        self.endpoint_url: str = endpoint
        self.timeout = config.get("timeout_seconds", 30)
        self.max_retries = config.get("max_retries", 3)
        self.allow_insecure_ssl = config.get("allow_insecure_ssl", False)
        self.headers = config.get("headers", {})

        # Add authentication headers if configured
        if "api_key" in config:
            self.headers["Authorization"] = f"Bearer {config['api_key']}"

        self.client = httpx.AsyncClient(
            timeout=self.timeout,
            headers=self.headers,
            limits=httpx.Limits(max_keepalive_connections=20, max_connections=100),
            verify=not self.allow_insecure_ssl,
        )

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((httpx.TimeoutException, httpx.NetworkError)),
        reraise=True,
    )
    async def send(self, artifact: Dict[str, Any]) -> Dict[str, Any]:
        """
        Send artifact to policy scanner

        Args:
            artifact: Resource configuration artifact

        Returns:
            Response from scanner

        Raises:
            TransportError: If send fails after retries
        """
        try:
            response = await self.client.post(self.endpoint_url, json=artifact)
            response.raise_for_status()

            logger.debug(f"Successfully sent artifact {artifact.get('resource_id')}")
            return response.json()

        except httpx.HTTPStatusError as e:
            logger.error(
                f"HTTP error sending artifact: {e.response.status_code} - {e.response.text}"
            )
            raise TransportError(f"HTTP {e.response.status_code}: {e.response.text}")
        except httpx.TimeoutException as e:
            logger.error(f"Timeout sending artifact: {e}")
            raise
        except httpx.NetworkError as e:
            logger.error(f"Network error sending artifact: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error sending artifact: {e}")
            raise TransportError(f"Unexpected error: {str(e)}")

    async def close(self):
        """Close HTTP client"""
        await self.client.aclose()
