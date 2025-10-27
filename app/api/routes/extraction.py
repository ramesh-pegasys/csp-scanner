# app/api/routes/extraction.py
from fastapi import APIRouter, HTTPException, Depends, Request
from typing import List, Optional
from pydantic import BaseModel
from app.models.job import Job

router = APIRouter()

class ExtractionRequest(BaseModel):
    services: Optional[List[str]] = None
    regions: Optional[List[str]] = None
    filters: Optional[dict] = None
    batch_size: int = 100

class ExtractionResponse(BaseModel):
    job_id: str
    message: str

@router.post("/trigger", response_model=ExtractionResponse)
async def trigger_extraction(request: ExtractionRequest, app_request: Request):
    """Trigger ad-hoc extraction"""
    orchestrator = app_request.app.state.orchestrator
    
    try:
        job_id = await orchestrator.run_extraction(
            services=request.services,
            regions=request.regions,
            filters=request.filters,
            batch_size=request.batch_size
        )
        
        return ExtractionResponse(
            job_id=job_id,
            message="Extraction job started successfully"
        )
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
async def list_services(app_request: Request):
    """List available services"""
    registry = app_request.app.state.registry
    return {"services": registry.list_services()}