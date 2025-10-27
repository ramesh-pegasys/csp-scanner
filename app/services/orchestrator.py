# app/services/orchestrator.py
from typing import List, Dict, Any, Optional
import asyncio
from datetime import datetime, timezone
import uuid
import logging
from app.services.registry import ExtractorRegistry
from app.transport.base import TransportWithSend
from app.models.job import Job, JobStatus

logger = logging.getLogger(__name__)


class ExtractionOrchestrator:
    """Orchestrates the extraction and transport of cloud artifacts"""

    def __init__(
        self,
        registry: ExtractorRegistry,
        transport: TransportWithSend,
        config: Dict[str, Any],
    ):
        self.registry = registry
        self.transport = transport
        self.config = config
        self.jobs: Dict[str, Job] = {}

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
        job = Job(
            id=job_id,
            status=JobStatus.RUNNING,
            started_at=datetime.now(timezone.utc),
            services=services or self.registry.list_services(),
        )
        self.jobs[job_id] = job

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

            # Extract from all services concurrently
            extraction_tasks = [
                self._extract_service(extractor, regions, filters)
                for extractor in extractors
            ]

            results = await asyncio.gather(*extraction_tasks, return_exceptions=True)

            # Flatten all artifacts
            all_artifacts: List[Dict[str, Any]] = []
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
        return self.jobs.get(job_id)

    def list_jobs(self, limit: int = 100) -> List[Job]:
        """List recent jobs"""
        return sorted(self.jobs.values(), key=lambda x: x.started_at, reverse=True)[
            :limit
        ]
