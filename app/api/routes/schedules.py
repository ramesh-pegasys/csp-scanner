# app/api/routes/schedules.py
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
from typing import List, Optional
from apscheduler.triggers.cron import CronTrigger  # type: ignore[import-untyped]
from app.models.database import get_db_manager
from app.core.config import get_settings
import logging

logger = logging.getLogger(__name__)
router = APIRouter()


class ScheduleRequest(BaseModel):
    name: str
    cron_expression: str
    services: Optional[List[str]] = None
    regions: Optional[List[str]] = None
    filters: Optional[dict] = None
    batch_size: int = 100

    class Config:
        json_schema_extra = {
            "example": {
                "name": "daily-extract",
                "cron_expression": "0 0 * * *",
                "services": ["ec2", "s3"],
                "regions": ["us-west-2"],
                "filters": {"tag": "production"},
                "batch_size": 100,
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
                        "batch_size": 100,
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
                            "cron": "0 0 * * *",
                        }
                    }
                },
            }
        },
    },
)
async def create_schedule(schedule: ScheduleRequest, app_request: Request):
    """Create a scheduled extraction"""
    scheduler = app_request.app.state.scheduler
    orchestrator = app_request.app.state.orchestrator
    settings = get_settings()

    try:
        trigger = CronTrigger.from_crontab(schedule.cron_expression)

        # Add job to scheduler
        job = scheduler.add_job(
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

        # Save to database if enabled
        if settings.database_enabled:
            try:
                db_manager = get_db_manager()
                next_run = job.next_run_time.isoformat() if job.next_run_time else None
                db_manager.create_schedule(
                    schedule_id=schedule.name,
                    name=schedule.name,
                    cron_expression=schedule.cron_expression,
                    services=schedule.services,
                    regions=schedule.regions,
                    filters=schedule.filters,
                    batch_size=schedule.batch_size,
                )
                if next_run:
                    db_manager.update_schedule(
                        schedule_id=schedule.name,
                        next_run_at=job.next_run_time,
                    )
                logger.info(f"Schedule '{schedule.name}' saved to database")
            except Exception as db_error:
                logger.warning(f"Failed to save schedule to database: {db_error}")

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
                                    "next_run": "2025-11-03T00:00:00Z",
                                }
                            ]
                        }
                    }
                },
            }
        }
    },
)
async def list_schedules(app_request: Request):
    """List all schedules"""
    scheduler = app_request.app.state.scheduler
    settings = get_settings()

    # Get schedules from APScheduler
    jobs = scheduler.get_jobs()
    schedules_list = []

    for job in jobs:
        schedule_info = {
            "id": job.id,
            "name": job.name,
            "next_run": (job.next_run_time.isoformat() if job.next_run_time else None),
        }

        # Enrich with database info if available
        if settings.database_enabled:
            try:
                db_manager = get_db_manager()
                db_schedule = db_manager.get_schedule(job.id)
                if db_schedule:
                    schedule_info.update(
                        {
                            "cron_expression": db_schedule["cron_expression"],
                            "services": db_schedule["services"],
                            "regions": db_schedule["regions"],
                            "filters": db_schedule["filters"],
                            "batch_size": db_schedule["batch_size"],
                            "is_active": db_schedule["is_active"],
                            "paused": db_schedule["paused"],
                            "last_run_at": db_schedule["last_run_at"],
                            "description": db_schedule["description"],
                        }
                    )
            except Exception as e:
                logger.warning(f"Failed to get schedule from database: {e}")

        schedules_list.append(schedule_info)

    return {"schedules": schedules_list}


@router.delete(
    "/{schedule_name}",
    openapi_extra={
        "responses": {
            "200": {
                "description": "Schedule Deleted",
                "content": {
                    "application/json": {
                        "example": {
                            "message": "Schedule 'daily-extract' deleted successfully"
                        }
                    }
                },
            }
        }
    },
)
async def delete_schedule(schedule_name: str, app_request: Request):
    """Delete a scheduled extraction"""
    scheduler = app_request.app.state.scheduler
    settings = get_settings()

    try:
        scheduler.remove_job(schedule_name)

        # Delete from database if enabled
        if settings.database_enabled:
            try:
                db_manager = get_db_manager()
                db_manager.delete_schedule(schedule_name)
                logger.info(f"Schedule '{schedule_name}' deleted from database")
            except Exception as db_error:
                logger.warning(f"Failed to delete schedule from database: {db_error}")

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
                        "example": {
                            "message": "Schedule 'daily-extract' paused successfully"
                        }
                    }
                },
            }
        }
    },
)
async def pause_schedule(schedule_name: str, app_request: Request):
    """Pause a scheduled extraction"""
    scheduler = app_request.app.state.scheduler
    settings = get_settings()

    try:
        scheduler.pause_job(schedule_name)

        # Update database if enabled
        if settings.database_enabled:
            try:
                db_manager = get_db_manager()
                db_manager.update_schedule(schedule_id=schedule_name, paused=True)
                logger.info(f"Schedule '{schedule_name}' marked as paused in database")
            except Exception as db_error:
                logger.warning(f"Failed to update schedule in database: {db_error}")

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
                        "example": {
                            "message": "Schedule 'daily-extract' resumed successfully"
                        }
                    }
                },
            }
        }
    },
)
async def resume_schedule(schedule_name: str, app_request: Request):
    """Resume a paused schedule"""
    scheduler = app_request.app.state.scheduler
    settings = get_settings()

    try:
        scheduler.resume_job(schedule_name)

        # Update database if enabled
        if settings.database_enabled:
            try:
                db_manager = get_db_manager()
                db_manager.update_schedule(schedule_id=schedule_name, paused=False)
                logger.info(f"Schedule '{schedule_name}' marked as resumed in database")
            except Exception as db_error:
                logger.warning(f"Failed to update schedule in database: {db_error}")

        return {"message": f"Schedule '{schedule_name}' resumed successfully"}
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))
