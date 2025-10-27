# app/api/routes/schedules.py
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
from typing import List, Optional
from apscheduler.triggers.cron import CronTrigger

router = APIRouter()

class ScheduleRequest(BaseModel):
    name: str
    cron_expression: str
    services: Optional[List[str]] = None
    regions: Optional[List[str]] = None
    filters: Optional[dict] = None
    batch_size: int = 100

@router.post("/")
async def create_schedule(schedule: ScheduleRequest, app_request: Request):
    """Create a scheduled extraction"""
    scheduler = app_request.app.state.scheduler
    orchestrator = app_request.app.state.orchestrator
    
    try:
        trigger = CronTrigger.from_crontab(schedule.cron_expression)
        
        scheduler.add_job(
            orchestrator.run_extraction,
            trigger=trigger,
            id=schedule.name,
            name=schedule.name,
            kwargs={
                'services': schedule.services,
                'regions': schedule.regions,
                'filters': schedule.filters,
                'batch_size': schedule.batch_size
            },
            replace_existing=True
        )
        
        return {
            "message": f"Schedule '{schedule.name}' created successfully",
            "cron": schedule.cron_expression
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/")
async def list_schedules(app_request: Request):
    """List all schedules"""
    scheduler = app_request.app.state.scheduler
    
    jobs = scheduler.get_jobs()
    return {
        "schedules": [
            {
                "id": job.id,
                "name": job.name,
                "next_run": job.next_run_time.isoformat() if job.next_run_time else None
            }
            for job in jobs
        ]
    }

@router.delete("/{schedule_name}")
async def delete_schedule(schedule_name: str, app_request: Request):
    """Delete a scheduled extraction"""
    scheduler = app_request.app.state.scheduler
    
    try:
        scheduler.remove_job(schedule_name)
        return {"message": f"Schedule '{schedule_name}' deleted successfully"}
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"Schedule not found: {str(e)}")

@router.put("/{schedule_name}/pause")
async def pause_schedule(schedule_name: str, app_request: Request):
    """Pause a scheduled extraction"""
    scheduler = app_request.app.state.scheduler
    
    try:
        scheduler.pause_job(schedule_name)
        return {"message": f"Schedule '{schedule_name}' paused successfully"}
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))

@router.put("/{schedule_name}/resume")
async def resume_schedule(schedule_name: str, app_request: Request):
    """Resume a paused schedule"""
    scheduler = app_request.app.state.scheduler
    
    try:
        scheduler.resume_job(schedule_name)
        return {"message": f"Schedule '{schedule_name}' resumed successfully"}
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))