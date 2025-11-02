# app/api/routes/extraction.py
from fastapi import APIRouter, HTTPException, Request, Depends
from typing import Any, Dict, List, Optional
from pydantic import BaseModel
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from app.models.job import Job
from app.cloud.base import CloudProvider
import os
from fastapi import FastAPI


def custom_openapi(app: FastAPI):
    if app.openapi_schema:
        return app.openapi_schema
    # Call the original FastAPI openapi method to avoid recursion
    from fastapi.openapi.utils import get_openapi

    openapi_schema = get_openapi(
        title=app.title,
        version=app.version,
        openapi_version=app.openapi_version,
        description=app.description,
        routes=app.routes,
    )
    # Add JWT Bearer security scheme
    openapi_schema["components"]["securitySchemes"] = {
        "BearerAuth": {"type": "http", "scheme": "bearer", "bearerFormat": "JWT"}
    }
    # Secure all paths except /health
    for path, methods in openapi_schema["paths"].items():
        if path == "/health":
            continue
        for method in methods:
            methods[method]["security"] = [{"BearerAuth": []}]
    # Always show HTTPS server in OpenAPI servers list
    openapi_schema["servers"] = [
        {
            "url": "https://localhost:8443",
            "description": "Local HTTPS (self-signed certs)",
        }
    ]
    app.openapi_schema = openapi_schema
    return app.openapi_schema


router = APIRouter()

# JWT config (static token usage)
SECRET_KEY = os.getenv("JWT_SECRET_KEY", "your-secret-key")
ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/token")

# TODO: Support external JWT providers (Auth0, Cognito, Google IAM) in future


def verify_jwt_token(token: str = Depends(oauth2_scheme)):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired token")


class ExtractionRequest(BaseModel):
    provider: Optional[str] = (
        None  # Cloud provider filter (None = all enabled providers)
    )
    services: Optional[List[str]] = None
    regions: Optional[List[str]] = None
    filters: Optional[dict] = None
    batch_size: int = 100

    class Config:
        schema_extra = {
            "example": {
                "provider": "aws",
                "services": ["ec2", "s3"],
                "regions": ["us-west-2"],
                "filters": {"tag": "production"},
                "batch_size": 100,
            }
        }


class ExtractionResponse(BaseModel):
    job_id: str
    message: str

    class Config:
        schema_extra = {
            "example": {
                "job_id": "job-123",
                "message": "Extraction started successfully",
            }
        }


@router.post(
    "/trigger",
    response_model=ExtractionResponse,
    openapi_extra={
        "requestBody": {
            "content": {
                "application/json": {
                    "example": {
                        "provider": "aws",
                        "services": ["ec2", "s3"],
                        "regions": ["us-west-2"],
                        "filters": {"tag": "production"},
                        "batch_size": 100,
                    }
                }
            }
        },
        "responses": {
            "200": {
                "description": "Successful Response",
                "content": {
                    "application/json": {
                        "example": {
                            "job_id": "job-123",
                            "message": "Extraction started successfully",
                        }
                    }
                },
            }
        },
    },
)
async def trigger_extraction(
    request: ExtractionRequest,
    app_request: Request,
    token_data: dict = Depends(verify_jwt_token),
):
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


@router.get(
    "/jobs/{job_id}",
    response_model=Job,
    openapi_extra={
        "responses": {
            "200": {
                "description": "Successful Response",
                "content": {
                    "application/json": {
                        "example": {
                            "id": "job-123",
                            "status": "completed",
                            "started_at": "2025-11-02T10:00:00Z",
                            "completed_at": "2025-11-02T10:05:00Z",
                            "services": ["EC2", "S3"],
                            "total_artifacts": 10,
                            "successful_artifacts": 9,
                            "failed_artifacts": 1,
                            "errors": ["Timeout on S3"],
                        }
                    }
                },
            }
        }
    },
)
async def get_job_status(
    job_id: str, app_request: Request, token_data: dict = Depends(verify_jwt_token)
):
    """Get job status"""
    orchestrator = app_request.app.state.orchestrator

    job = orchestrator.get_job_status(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    return job


@router.get(
    "/jobs",
    response_model=List[Job],
    openapi_extra={
        "responses": {
            "200": {
                "description": "Successful Response",
                "content": {
                    "application/json": {
                        "example": [
                            {
                                "id": "job-123",
                                "status": "completed",
                                "started_at": "2025-11-02T10:00:00Z",
                                "completed_at": "2025-11-02T10:05:00Z",
                                "services": ["EC2", "S3"],
                                "total_artifacts": 10,
                                "successful_artifacts": 9,
                                "failed_artifacts": 1,
                                "errors": ["Timeout on S3"],
                            }
                        ]
                    }
                },
            }
        }
    },
)
async def list_jobs(
    app_request: Request, limit: int = 100, token_data: dict = Depends(verify_jwt_token)
):
    """List recent jobs"""
    orchestrator = app_request.app.state.orchestrator
    return orchestrator.list_jobs(limit)


@router.get(
    "/services",
    openapi_extra={
        "responses": {
            "200": {
                "description": "Successful Response",
                "content": {
                    "application/json": {
                        "example": {
                            "services_by_provider": {
                                "aws": [
                                    {
                                        "service": "ec2",
                                        "description": "Amazon EC2 Instances",
                                        "resource_types": ["instance"],
                                        "version": "1.0",
                                    }
                                ]
                            },
                            "total_services": 1,
                        }
                    }
                },
            }
        }
    },
)
async def list_services(
    app_request: Request,
    provider: Optional[str] = None,
    token_data: dict = Depends(verify_jwt_token),
):
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
    services_by_provider: Dict[str, List[Dict[str, Any]]] = {}
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


@router.get(
    "/providers",
    openapi_extra={
        "responses": {
            "200": {
                "description": "Successful Response",
                "content": {
                    "application/json": {
                        "example": {"providers": ["aws", "azure", "gcp"], "total": 3}
                    }
                },
            }
        }
    },
)
async def list_providers(app_request: Request):
    """List enabled cloud providers"""
    registry = app_request.app.state.registry
    extractors = registry.get_extractors()

    providers = list(set(e.cloud_provider for e in extractors))

    return {"providers": providers, "total": len(providers)}


@router.get(
    "/health",
    openapi_extra={
        "responses": {
            "200": {
                "description": "Health Check",
                "content": {"application/json": {"example": {"status": "ok"}}},
            }
        }
    },
)
async def health():
    """Health endpoint (no JWT required)"""
    return {"status": "ok"}
