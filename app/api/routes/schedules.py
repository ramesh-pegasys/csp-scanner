# app/api/routes/schedules.py
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
from typing import List, Optional
from apscheduler.triggers.cron import CronTrigger  # type: ignore[import-untyped]

router = APIRouter()


class ScheduleRequest(BaseModel):
    name: str
    cron_expression: str
    services: Optional[List[str]] = None
    regions: Optional[List[str]] = None
    filters: Optional[dict] = None
    batch_size: int = 100

    class Config:
            schema_extra = {
                "example": {
                    "name": "daily-extract",
                    "cron_expression": "0 0 * * *",
                    "services": ["ec2", "s3"],
                    "regions": ["us-west-2"],
                    "filters": {"tag": "production"},
                    "batch_size": 100
                }
            }


@router.post(
    "/",
    openapi_extra={
        "requestBody": {
            "content": {
                "application/json": {
                    "example": {
                        "name": "daily-extract",
                        "cron_expression": "0 0 * * *",
                        "services": ["ec2", "s3"],
                        "regions": ["us-west-2"],
                        "filters": {"tag": "production"},
                        "batch_size": 100
                    }
                }
            }
        },
        "responses": {
            "200": {
                "description": "Schedule Created",
                "content": {
                    "application/json": {
                        "example": {
                            "message": "Schedule 'daily-extract' created successfully",
                            "cron": "0 0 * * *"
                        }
                    }
                }
            }
        }
    },
)
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
                "services": schedule.services,
                "regions": schedule.regions,
                "filters": schedule.filters,
                "batch_size": schedule.batch_size,
            },
            replace_existing=True,
        )

        return {
            "message": f"Schedule '{schedule.name}' created successfully",
            "cron": schedule.cron_expression,
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get(
    "/",
    openapi_extra={
        "responses": {
            "200": {
                "description": "List Schedules",
                "content": {
                    "application/json": {
                        "example": {
                            "schedules": [
                                {
                                    "id": "daily-extract",
                                    "name": "Daily Extract",
                                    "next_run": "2025-11-03T00:00:00Z"
                                }
                            ]
                        }
                    }
                }
            }
        }
    },
)
async def list_schedules(app_request: Request):
    """List all schedules"""
    scheduler = app_request.app.state.scheduler

    jobs = scheduler.get_jobs()
    return {
        "schedules": [
            {
                "id": job.id,
                "name": job.name,
                "next_run": (
                    job.next_run_time.isoformat() if job.next_run_time else None
                ),
            }
            for job in jobs
        ]
    }


@router.delete(
    "/{schedule_name}",
    openapi_extra={
        "responses": {
            "200": {
                "description": "Schedule Deleted",
                "content": {
                    "application/json": {
                        "example": {"message": "Schedule 'daily-extract' deleted successfully"}
                    }
                }
            }
        }
    },
)
async def delete_schedule(schedule_name: str, app_request: Request):
    """Delete a scheduled extraction"""
    scheduler = app_request.app.state.scheduler

    try:
        scheduler.remove_job(schedule_name)
        return {"message": f"Schedule '{schedule_name}' deleted successfully"}
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"Schedule not found: {str(e)}")


@router.put(
    "/{schedule_name}/pause",
    openapi_extra={
        "responses": {
            "200": {
                "description": "Schedule Paused",
                "content": {
                    "application/json": {
                        "example": {"message": "Schedule 'daily-extract' paused successfully"}
                    }
                }
            }
        }
    },
)
async def pause_schedule(schedule_name: str, app_request: Request):
    """Pause a scheduled extraction"""
    scheduler = app_request.app.state.scheduler

    try:
        scheduler.pause_job(schedule_name)
        return {"message": f"Schedule '{schedule_name}' paused successfully"}
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.put(
    "/{schedule_name}/resume",
    openapi_extra={
        "responses": {
            "200": {
                "description": "Schedule Resumed",
                "content": {
                    "application/json": {
                        "example": {"message": "Schedule 'daily-extract' resumed successfully"}
                    }
                }
            }
        }
    },
)
async def resume_schedule(schedule_name: str, app_request: Request):
    """Resume a paused schedule"""
    scheduler = app_request.app.state.scheduler

    try:
        scheduler.resume_job(schedule_name)
        return {"message": f"Schedule '{schedule_name}' resumed successfully"}
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))
