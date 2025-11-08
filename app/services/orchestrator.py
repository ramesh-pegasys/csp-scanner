# app/services/orchestrator.py
from typing import List, Dict, Any, Optional
import asyncio
from datetime import datetime, timezone
import uuid
import logging
from app.services.registry import ExtractorRegistry
from app.transport.base import TransportWithSend, TransportFactory
from app.models.job import Job, JobStatus
from app.models.database import get_db_manager

logger = logging.getLogger(__name__)


class ExtractionOrchestrator:
    """Orchestrates the extraction and transport of cloud artifacts"""

    def __init__(
        self,
        registry: ExtractorRegistry,
        transport: Optional[TransportWithSend],
        config: Dict[str, Any],
    ):
        self.registry = registry
        self._transport = transport
        self._transport_config: Optional[Dict[str, Any]] = None
        self.config = config
        self.jobs: Dict[str, Job] = {}
        self.use_db = config.get("database_enabled", False)
        if self.use_db:
            try:
                self.db_manager = get_db_manager()
                logger.info("Database backend enabled for job tracking")
            except Exception as e:
                logger.warning(f"Failed to initialize database manager: {e}")
                self.use_db = False

    @property
    def transport(self) -> TransportWithSend:
        """Lazy initialization of transport based on settings"""
        if self._transport is None:
            from app.core.config import get_settings

            settings = get_settings()
            transport_config = settings.transport_config
            self._transport_config = transport_config
            transport_type = transport_config.get("type", "http")
            logger.info(f"Initializing transport: {transport_type}")
            self._transport = TransportFactory.create(transport_type, transport_config)
        return self._transport

    def reinitialize_transport(self, transport_config: Dict[str, Any]) -> None:
        """Reinitialize transport with new configuration"""
        # Close old transport if it exists
        if self._transport is not None:
            logger.info("Closing existing transport")
            if hasattr(self._transport, "close"):
                import asyncio

                try:
                    loop = asyncio.get_event_loop()
                    if loop.is_running():
                        asyncio.create_task(self._transport.close())  # type: ignore[attr-defined]
                    else:
                        loop.run_until_complete(self._transport.close())  # type: ignore[attr-defined]
                except Exception as e:
                    logger.warning(f"Failed to close transport: {e}")
            elif hasattr(self._transport, "disconnect"):
                import asyncio

                try:
                    loop = asyncio.get_event_loop()
                    if loop.is_running():
                        asyncio.create_task(self._transport.disconnect())  # type: ignore[attr-defined]
                    else:
                        loop.run_until_complete(self._transport.disconnect())  # type: ignore[attr-defined]
                except Exception as e:
                    logger.warning(f"Failed to disconnect transport: {e}")

        # Create new transport
        self._transport_config = transport_config
        transport_type = transport_config.get("type", "http")
        logger.info(f"Reinitializing transport: {transport_type}")
        self._transport = TransportFactory.create(transport_type, transport_config)

    async def cleanup(self) -> None:
        """Cleanup resources"""
        if self._transport is not None:
            if hasattr(self._transport, "close"):
                await self._transport.close()  # type: ignore[attr-defined]
            elif hasattr(self._transport, "disconnect"):
                await self._transport.disconnect()  # type: ignore[attr-defined]

    async def run_extraction(
        self,
        services: Optional[List[str]] = None,
        regions: Optional[List[str]] = None,
        filters: Optional[Dict[str, Any]] = None,
        batch_size: int = 100,
    ) -> str:
        """
        Run extraction job for specified services

        Args:
            services: List of AWS services to extract (None = all)
            regions: List of regions (None = all)
            filters: Additional filters to apply
            batch_size: Number of artifacts to send per batch

        Returns:
            Job ID for tracking
        """
        job_id = str(uuid.uuid4())
        service_list = services or self.registry.list_services()

        job = Job(
            id=job_id,
            status=JobStatus.RUNNING,
            started_at=datetime.now(timezone.utc),
            services=service_list,
        )
        self.jobs[job_id] = job

        # Save to database if enabled
        if self.use_db:
            try:
                self.db_manager.create_job(
                    job_id=job_id,
                    services=service_list,
                    regions=regions,
                    filters=filters,
                    batch_size=batch_size,
                )
                logger.debug(f"Job {job_id} saved to database")
            except Exception as e:
                logger.warning(f"Failed to save job to database: {e}")

        # Run extraction asynchronously
        asyncio.create_task(
            self._execute_job(job, services, regions, filters, batch_size)
        )

        return job_id

    async def _execute_job(
        self,
        job: Job,
        services: Optional[List[str]],
        regions: Optional[List[str]],
        filters: Optional[Dict[str, Any]],
        batch_size: int,
    ):
        """Execute extraction job"""
        try:
            extractors = self.registry.get_extractors(services)

            all_artifacts: List[Dict[str, Any]] = []
            extraction_tasks = []

            # Build extraction tasks for all providers
            for extractor in extractors:
                if getattr(extractor, "cloud_provider", None) == "azure":
                    # Azure: handle multi-subscription/location extraction
                    if extractor.metadata.supports_regions:
                        # Use locations from session if available
                        locations = getattr(extractor.session, "locations", None)
                        if not locations:
                            locations = regions or extractor.session.list_regions()
                        for location in locations:
                            extraction_tasks.append(
                                extractor.extract(location, filters)
                            )
                    else:
                        extraction_tasks.append(extractor.extract(filters=filters))
                else:
                    # AWS/GCP: standard region-based extraction
                    extraction_tasks.append(
                        self._extract_service(extractor, regions, filters)
                    )

            results = await asyncio.gather(*extraction_tasks, return_exceptions=True)

            for result in results:
                if isinstance(result, Exception):
                    logger.error(f"Service extraction failed: {result}")
                    job.errors.append(str(result))
                else:
                    all_artifacts.extend(result)  # type: ignore

            job.total_artifacts = len(all_artifacts)

            # Send artifacts in batches
            await self._send_artifacts(job, all_artifacts, batch_size)

            job.status = JobStatus.COMPLETED
            job.completed_at = datetime.now(timezone.utc)

        except Exception as e:
            logger.error(f"Job {job.id} failed: {e}")
            job.status = JobStatus.FAILED
            job.errors.append(str(e))
            job.completed_at = datetime.now(timezone.utc)

        finally:
            # Update job in database if enabled
            if self.use_db:
                try:
                    self.db_manager.update_job(
                        job_id=job.id,
                        status=job.status.value,
                        completed_at=job.completed_at,
                        total_artifacts=job.total_artifacts,
                        successful_artifacts=job.successful_artifacts,
                        failed_artifacts=job.failed_artifacts,
                        errors=job.errors,
                    )
                    logger.debug(f"Job {job.id} updated in database")
                except Exception as db_error:
                    logger.warning(f"Failed to update job in database: {db_error}")

    async def _extract_service(
        self, extractor, regions: Optional[List[str]], filters: Optional[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Extract artifacts from a single service"""
        logger.info(f"Extracting from {extractor.metadata.service_name}")

        if extractor.metadata.supports_regions and regions:
            # Extract from specific regions in parallel
            tasks = [extractor.extract(region, filters) for region in regions]
            results = await asyncio.gather(*tasks, return_exceptions=True)

            artifacts: List[Dict[str, Any]] = []
            for result in results:
                if isinstance(result, Exception):
                    logger.error(f"Region extraction failed: {result}")
                else:
                    artifacts.extend(result)  # type: ignore
            return artifacts
        else:
            # Extract from all regions or global service
            return await extractor.extract(filters=filters)

    async def _send_artifacts(
        self, job: Job, artifacts: List[Dict[str, Any]], batch_size: int
    ):
        """Send artifacts to policy scanner in batches"""
        total_batches = (len(artifacts) + batch_size - 1) // batch_size

        for i in range(0, len(artifacts), batch_size):
            batch = artifacts[i : i + batch_size]
            batch_num = i // batch_size + 1

            logger.info(
                f"Sending batch {batch_num}/{total_batches} ({len(batch)} artifacts)"
            )

            # Send artifacts concurrently within batch
            tasks = [self.transport.send(artifact) for artifact in batch]
            results = await asyncio.gather(*tasks, return_exceptions=True)

            # Track results
            for idx, result in enumerate(results):
                if isinstance(result, Exception):
                    logger.error(f"Failed to send artifact: {result}")
                    job.failed_artifacts += 1
                    job.errors.append(
                        f"Artifact {batch[idx].get('resource_id')}: {str(result)}"
                    )
                else:
                    job.successful_artifacts += 1

            # Rate limiting between batches
            if i + batch_size < len(artifacts):
                await asyncio.sleep(self.config.get("batch_delay_seconds", 0.1))

    def get_job_status(self, job_id: str) -> Optional[Job]:
        """Get job status by ID"""
        # Try in-memory first (for running jobs)
        job = self.jobs.get(job_id)
        if job:
            return job

        # If not in memory and database is enabled, check database
        if self.use_db:
            try:
                job_data = self.db_manager.get_job(job_id)
                if job_data:
                    # Convert database data to Job model
                    return Job(
                        id=job_data["id"],
                        status=JobStatus(job_data["status"]),
                        started_at=datetime.fromisoformat(job_data["started_at"]),
                        completed_at=(
                            datetime.fromisoformat(job_data["completed_at"])
                            if job_data["completed_at"]
                            else None
                        ),
                        services=job_data["services"],
                        total_artifacts=job_data["total_artifacts"],
                        successful_artifacts=job_data["successful_artifacts"],
                        failed_artifacts=job_data["failed_artifacts"],
                        errors=job_data["errors"],
                    )
            except Exception as e:
                logger.warning(f"Failed to retrieve job from database: {e}")

        return None

    def list_jobs(self, limit: int = 100) -> List[Job]:
        """List recent jobs"""
        # If database is enabled, get jobs from there
        if self.use_db:
            try:
                jobs_data = self.db_manager.list_jobs(limit=limit)
                jobs = []
                for job_data in jobs_data:
                    try:
                        jobs.append(
                            Job(
                                id=job_data["id"],
                                status=JobStatus(job_data["status"]),
                                started_at=datetime.fromisoformat(
                                    job_data["started_at"]
                                ),
                                completed_at=(
                                    datetime.fromisoformat(job_data["completed_at"])
                                    if job_data["completed_at"]
                                    else None
                                ),
                                services=job_data["services"],
                                total_artifacts=job_data["total_artifacts"],
                                successful_artifacts=job_data["successful_artifacts"],
                                failed_artifacts=job_data["failed_artifacts"],
                                errors=job_data["errors"],
                            )
                        )
                    except Exception as e:
                        logger.warning(f"Failed to parse job data: {e}")
                        continue
                return jobs
            except Exception as e:
                logger.warning(f"Failed to list jobs from database: {e}")

        # Use in-memory jobs if database is disabled or failed
        return sorted(self.jobs.values(), key=lambda x: x.started_at, reverse=True)[
            :limit
        ]
