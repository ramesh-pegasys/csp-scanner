# app/transport/filesystem.py
"""
Filesystem transport for writing artifacts to local JSON files.
Each artifact is written as a separate JSON file with a unique filename.
"""

import os
import json
import uuid
from typing import Dict, Any, List
from datetime import datetime, timezone
import logging

from app.transport.base import BaseTransport, TransportResult, TransportStatus
from app.core.exceptions import TransportError

logger = logging.getLogger(__name__)


class FilesystemTransport(BaseTransport):
    """
    Transport that writes artifacts to local filesystem as JSON files.

    Each artifact gets a unique filename based on service, resource type,
    resource ID, and timestamp. Files are organized in a directory structure.
    """

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize filesystem transport using transport config node.

        Args:
            config: Transport configuration node (expects 'type', 'base_dir', 'create_dir')
        """
        super().__init__(config)

        # Get base directory from config, default to ./file_collector relative to cwd
        self.base_dir = config.get("base_dir", "./file_collector")

        # Convert to absolute path if relative
        if not os.path.isabs(self.base_dir):
            self.base_dir = os.path.join(os.getcwd(), self.base_dir)

        self.create_dir = config.get("create_dir", True)

        # Ensure base directory exists
        self._ensure_base_dir()

        logger.info(
            f"Filesystem transport initialized with base directory: {self.base_dir}"
        )

    def _ensure_base_dir(self) -> None:
        """Ensure the base directory exists"""
        if self.create_dir and not os.path.exists(self.base_dir):
            try:
                os.makedirs(self.base_dir, exist_ok=True)
                logger.info(f"Created base directory: {self.base_dir}")
            except OSError as e:
                raise TransportError(
                    f"Failed to create base directory {self.base_dir}: {e}"
                )

    def _generate_filename(self, artifact: Dict[str, Any]) -> str:
        """
        Generate a unique filename for the artifact.

        Format: {service}_{resource_type}_{resource_id}_{timestamp}_{uuid}.json

        Args:
            artifact: The artifact to generate filename for

        Returns:
            Unique filename
        """
        # Extract service from metadata if available, otherwise from top level
        service = "unknown"
        if "metadata" in artifact and isinstance(artifact["metadata"], dict):
            service = artifact["metadata"].get("service", "unknown")
        if service == "unknown":
            service = artifact.get("service", "unknown")

        resource_type = artifact.get("resource_type", "unknown")

        # Extract resource_id from metadata if available, otherwise from top level
        resource_id = "unknown"
        if "metadata" in artifact and isinstance(artifact["metadata"], dict):
            resource_id = artifact["metadata"].get("resource_id", "unknown")
        if resource_id == "unknown":
            resource_id = artifact.get("resource_id", "unknown")

        # Clean resource_id to be filesystem-safe and extract a meaningful name
        if resource_id != "unknown":
            # For Azure resources, extract the resource name from the resource ID
            # Azure resource IDs have format:
            # /subscriptions/.../resourceGroups/.../providers/.../resourceType/resourceName
            if "/" in str(resource_id):
                parts = str(resource_id).split("/")
                if len(parts) > 0:
                    # Get the last part which is usually the resource name
                    resource_name = parts[-1]
                    if resource_name:
                        resource_id_clean = resource_name.replace("/", "_").replace(
                            "\\", "_"
                        )[:50]
                    else:
                        resource_id_clean = (
                            str(resource_id).replace("/", "_").replace("\\", "_")[:50]
                        )
                else:
                    resource_id_clean = (
                        str(resource_id).replace("/", "_").replace("\\", "_")[:50]
                    )
            else:
                resource_id_clean = (
                    str(resource_id).replace("/", "_").replace("\\", "_")[:50]
                )
        else:
            resource_id_clean = "unknown"

        # Clean resource_type to be filesystem-safe (replace colons with underscores)
        resource_type_clean = (
            str(resource_type)
            .replace(":", "_")
            .replace("/", "_")
            .replace("\\", "_")[:50]
        )

        # Generate timestamp
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S_%f")

        # Generate unique ID
        unique_id = str(uuid.uuid4())[:8]

        filename = f"{service}_{resource_type_clean}_{resource_id_clean}_{timestamp}_{unique_id}.json"

        return filename

    def _get_file_path(self, filename: str) -> str:
        """
        Get the full file path for a filename.

        Args:
            filename: The filename

        Returns:
            Full path to the file
        """
        return os.path.join(self.base_dir, filename)

    async def connect(self) -> bool:
        """
        Establish connection (ensure directory exists).

        Returns:
            True if connection successful
        """
        try:
            self._ensure_base_dir()
            self._is_connected = True
            logger.info("Filesystem transport connected")
            return True
        except Exception as e:
            logger.error(f"Failed to connect filesystem transport: {e}")
            self._is_connected = False
            return False

    async def disconnect(self) -> None:
        """Close connection (no-op for filesystem)"""
        self._is_connected = False
        logger.info("Filesystem transport disconnected")

    async def send(self, artifact: Dict[str, Any]) -> TransportResult:
        """
        Write a single artifact to a JSON file.

        Args:
            artifact: The cloud artifact to write

        Returns:
            TransportResult indicating success/failure
        """
        start_time = datetime.now(timezone.utc)

        # Extract artifact_id from metadata if available, otherwise from top level
        artifact_id = "unknown"
        if "metadata" in artifact and isinstance(artifact["metadata"], dict):
            artifact_id = artifact["metadata"].get("resource_id", "unknown")
        if artifact_id == "unknown":
            artifact_id = artifact.get("resource_id", "unknown")

        try:
            # Generate unique filename
            filename = self._generate_filename(artifact)
            file_path = self._get_file_path(filename)

            # Write artifact to JSON file
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(artifact, f, indent=2, ensure_ascii=False, default=str)

            duration_ms = (
                datetime.now(timezone.utc) - start_time
            ).total_seconds() * 1000

            logger.debug(f"Successfully wrote artifact {artifact_id} to {file_path}")

            result = TransportResult(
                status=TransportStatus.SUCCESS,
                artifact_id=artifact_id,
                timestamp=datetime.now(timezone.utc),
                response_data={"file_path": file_path, "filename": filename},
                duration_ms=duration_ms,
            )

            await self._update_metrics_success(result)
            return result

        except Exception as e:
            duration_ms = (
                datetime.now(timezone.utc) - start_time
            ).total_seconds() * 1000
            error_msg = f"Failed to write artifact {artifact_id}: {str(e)}"

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
        Write multiple artifacts as individual JSON files.

        Args:
            artifacts: List of cloud artifacts to write

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
        Check if the filesystem is writable.

        Returns:
            True if filesystem is writable
        """
        try:
            # Try to write a test file
            test_file = os.path.join(self.base_dir, ".health_check")
            with open(test_file, "w") as f:
                f.write("health_check")

            # Clean up test file
            os.remove(test_file)

            return True
        except Exception as e:
            logger.error(f"Filesystem health check failed: {e}")
            return False

    def get_base_dir(self) -> str:
        """
        Get the base directory path.

        Returns:
            Base directory path
        """
        return self.base_dir

    def list_files(self) -> List[str]:
        """
        List all JSON files in the base directory.

        Returns:
            List of filenames
        """
        try:
            return [
                f
                for f in os.listdir(self.base_dir)
                if f.endswith(".json")
                and os.path.isfile(os.path.join(self.base_dir, f))
            ]
        except Exception as e:
            logger.error(f"Failed to list files: {e}")
            return []


# Register this transport
from app.transport.base import TransportFactory  # noqa: E402

TransportFactory.register("filesystem", FilesystemTransport)
