# app/transport/http_transport.py
"""
HTTP transport implementation using BaseTransport.
Wraps the HTTPTransport client for use with the transport factory.
"""

from typing import Dict, Any, List
from datetime import datetime, timezone
import logging

from app.transport.base import BaseTransport, TransportResult, TransportStatus
from app.transport.http_client import HTTPTransport as HTTPClient
from app.core.exceptions import TransportError

logger = logging.getLogger(__name__)


class HTTPTransport(BaseTransport):
    """
    HTTP transport that sends artifacts to a remote policy scanner endpoint.

    Uses the HTTPClient internally for actual HTTP communication.
    """

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize HTTP transport using transport config node.

        Args:
            config: Transport configuration node (expects 'type', 'http_endpoint_url', etc)
        """
        super().__init__(config)
        self.client = HTTPClient(config)

    async def connect(self) -> bool:
        """
        Establish connection (no-op for HTTP, always ready).

        Returns:
            True indicating ready to send
        """
        self._is_connected = True
        logger.info("HTTP transport connected")
        return True

    async def disconnect(self) -> None:
        """Close HTTP client connections"""
        await self.client.close()
        self._is_connected = False
        logger.info("HTTP transport disconnected")

    async def send(self, artifact: Dict[str, Any]) -> TransportResult:
        """
        Send a single artifact to the HTTP endpoint.

        Args:
            artifact: The cloud artifact to send

        Returns:
            TransportResult indicating success/failure
        """
        start_time = datetime.now(timezone.utc)
        artifact_id = artifact.get("resource_id", "unknown")

        try:
            response = await self.client.send(artifact)
            duration_ms = (
                datetime.now(timezone.utc) - start_time
            ).total_seconds() * 1000

            logger.debug(f"Successfully sent artifact {artifact_id} via HTTP")

            result = TransportResult(
                status=TransportStatus.SUCCESS,
                artifact_id=artifact_id,
                timestamp=datetime.now(timezone.utc),
                response_data=response,
                duration_ms=duration_ms,
            )

            await self._update_metrics_success(result)
            return result

        except TransportError as e:
            duration_ms = (
                datetime.now(timezone.utc) - start_time
            ).total_seconds() * 1000
            error_msg = f"Failed to send artifact {artifact_id} via HTTP: {str(e)}"

            logger.error(error_msg)

            result = TransportResult(
                status=TransportStatus.FAILED,
                artifact_id=artifact_id,
                timestamp=datetime.now(timezone.utc),
                error_message=error_msg,
                duration_ms=duration_ms,
            )

            await self._update_metrics_failure(result)
            return result

        except Exception as e:
            duration_ms = (
                datetime.now(timezone.utc) - start_time
            ).total_seconds() * 1000
            error_msg = f"Unexpected error sending artifact {artifact_id}: {str(e)}"

            logger.error(error_msg)

            result = TransportResult(
                status=TransportStatus.FAILED,
                artifact_id=artifact_id,
                timestamp=datetime.now(timezone.utc),
                error_message=error_msg,
                duration_ms=duration_ms,
            )

            await self._update_metrics_failure(result)
            return result

    async def send_batch(
        self, artifacts: List[Dict[str, Any]]
    ) -> List[TransportResult]:
        """
        Send multiple artifacts as individual HTTP requests.

        Args:
            artifacts: List of cloud artifacts to send

        Returns:
            List of TransportResult for each artifact
        """
        results = []
        for artifact in artifacts:
            result = await self.send(artifact)
            results.append(result)

        return results

    async def health_check(self) -> bool:
        """
        Check if the HTTP endpoint is reachable.

        Returns:
            True if endpoint is reachable
        """
        try:
            # Could implement a HEAD request or use a health endpoint
            # For now, just check if client is ready
            return self._is_connected
        except Exception as e:
            logger.error(f"HTTP health check failed: {e}")
            return False

    async def close(self):
        """Close HTTP client (alias for disconnect)"""
        await self.disconnect()


# Register this transport
from app.transport.base import TransportFactory  # noqa: E402

TransportFactory.register("http", HTTPTransport)
