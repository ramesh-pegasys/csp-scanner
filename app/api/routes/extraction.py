# app/api/routes/extraction.py
from fastapi import APIRouter, HTTPException, Request
from typing import List, Optional
from pydantic import BaseModel
from app.models.job import Job
from app.cloud.base import CloudProvider

router = APIRouter()


class ExtractionRequest(BaseModel):
    provider: Optional[str] = (
        None  # Cloud provider filter (None = all enabled providers)
    )
    services: Optional[List[str]] = None
    regions: Optional[List[str]] = None
    filters: Optional[dict] = None
    batch_size: int = 100


class ExtractionResponse(BaseModel):
    job_id: str
    message: str


@router.post("/trigger", response_model=ExtractionResponse)
async def trigger_extraction(request: ExtractionRequest, app_request: Request):
    """Trigger ad-hoc extraction for specified cloud provider(s) and services"""
    orchestrator = app_request.app.state.orchestrator
    registry = app_request.app.state.registry

    try:
        # Validate and filter by provider if specified
        provider_filter = None
        if request.provider:
            try:
                provider_filter = CloudProvider(request.provider)
            except ValueError:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid provider: {request.provider}. Valid options: aws, azure, gcp",
                )

        # Get services filtered by provider if specified
        services_to_extract = request.services
        if provider_filter:
            # Get only services for the specified provider
            available_services = [
                e.metadata.service_name
                for e in registry.get_extractors(provider=provider_filter)
            ]

            if services_to_extract:
                # Validate services exist for provider
                invalid_services = set(services_to_extract) - set(available_services)
                if invalid_services:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Invalid services for {request.provider}: {invalid_services}",
                    )
            else:
                services_to_extract = available_services

        job_id = await orchestrator.run_extraction(
            services=services_to_extract,
            regions=request.regions,
            filters=request.filters,
            batch_size=request.batch_size,
        )

        provider_msg = (
            f" from {request.provider}"
            if request.provider
            else " from all enabled providers"
        )
        return ExtractionResponse(
            job_id=job_id, message=f"Extraction job started successfully{provider_msg}"
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/jobs/{job_id}", response_model=Job)
async def get_job_status(job_id: str, app_request: Request):
    """Get job status"""
    orchestrator = app_request.app.state.orchestrator

    job = orchestrator.get_job_status(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    return job


@router.get("/jobs", response_model=List[Job])
async def list_jobs(app_request: Request, limit: int = 100):
    """List recent jobs"""
    orchestrator = app_request.app.state.orchestrator
    return orchestrator.list_jobs(limit)


@router.get("/services")
async def list_services(app_request: Request, provider: Optional[str] = None):
    """List available services, optionally filtered by provider"""
    registry = app_request.app.state.registry

    provider_filter = None
    if provider:
        try:
            provider_filter = CloudProvider(provider)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid provider: {provider}. Valid options: aws, azure, gcp",
            )

    # Get extractors filtered by provider
    extractors = registry.get_extractors(provider=provider_filter)

    # Group by provider
    services_by_provider = {}
    for extractor in extractors:
        provider_key = extractor.cloud_provider
        if provider_key not in services_by_provider:
            services_by_provider[provider_key] = []
        services_by_provider[provider_key].append(
            {
                "service": extractor.metadata.service_name,
                "description": extractor.metadata.description,
                "resource_types": extractor.metadata.resource_types,
                "version": extractor.metadata.version,
            }
        )

    return {
        "services_by_provider": services_by_provider,
        "total_services": len(extractors),
    }


@router.get("/providers")
async def list_providers(app_request: Request):
    """List enabled cloud providers"""
    registry = app_request.app.state.registry
    extractors = registry.get_extractors()

    providers = list(set(e.cloud_provider for e in extractors))

    return {"providers": providers, "total": len(providers)}
