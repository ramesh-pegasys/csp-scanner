import logging
from typing import Dict, Any, List
from datetime import datetime, timezone

from app.transport.base import (
    BaseTransport,
    TransportResult,
    TransportStatus,
    TransportFactory,
)

logger = logging.getLogger(__name__)


class ConsoleTransport(BaseTransport):
    """
    Transport that writes artifact body to the console (stdout).
    """

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)

    async def connect(self) -> bool:
        self._is_connected = True
        logger.info("Console transport connected")
        return True

    async def disconnect(self) -> None:
        self._is_connected = False
        logger.info("Console transport disconnected")

    async def send(self, artifact: Dict[str, Any]) -> TransportResult:
        start_time = datetime.now(timezone.utc)
        artifact_id = artifact.get("resource_id", "unknown")
        body = artifact.get(
            "body", artifact
        )  # Use 'body' key if present, else whole artifact

        print("=== Artifact Body ===")
        print(body)
        print("=====================")

        duration_ms = (datetime.now(timezone.utc) - start_time).total_seconds() * 1000

        result = TransportResult(
            status=TransportStatus.SUCCESS,
            artifact_id=artifact_id,
            timestamp=datetime.now(timezone.utc),
            response_data={"output": "console"},
            duration_ms=duration_ms,
        )
        await self._update_metrics_success(result)
        return result

    async def send_batch(
        self, artifacts: List[Dict[str, Any]]
    ) -> List[TransportResult]:
        results = []
        for artifact in artifacts:
            result = await self.send(artifact)
            results.append(result)
        return results

    async def health_check(self) -> bool:
        return True


# Register this transport
TransportFactory.register("console", ConsoleTransport)
