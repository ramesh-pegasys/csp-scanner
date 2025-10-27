# app/services/scheduler.py
from typing import Dict, Any, Optional
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.jobstores.memory import MemoryJobStore
from apscheduler.executors.asyncio import AsyncIOExecutor
import logging

logger = logging.getLogger(__name__)

class SchedulerService:
    """Service for managing scheduled extraction jobs using APScheduler"""

    def __init__(self):
        # Configure job stores and executors
        jobstores = {
            'default': MemoryJobStore()
        }
        executors = {
            'default': AsyncIOExecutor()
        }

        # Create scheduler
        self.scheduler = AsyncIOScheduler(
            jobstores=jobstores,
            executors=executors,
            job_defaults={
                'coalesce': True,
                'max_instances': 1,
                'misfire_grace_time': 30
            },
            timezone='UTC'
        )

    def start(self):
        """Start the scheduler"""
        if not self.scheduler.running:
            self.scheduler.start()
            logger.info("Scheduler started")

    def shutdown(self):
        """Shutdown the scheduler"""
        if self.scheduler.running:
            self.scheduler.shutdown()
            logger.info("Scheduler shutdown")

    def add_job(self, func, trigger, id: str, name: str, **kwargs):
        """Add a scheduled job"""
        return self.scheduler.add_job(
            func=func,
            trigger=trigger,
            id=id,
            name=name,
            **kwargs
        )

    def get_jobs(self):
        """Get all scheduled jobs"""
        return self.scheduler.get_jobs()

    def get_job(self, job_id: str):
        """Get a specific job by ID"""
        return self.scheduler.get_job(job_id)

    def remove_job(self, job_id: str):
        """Remove a scheduled job"""
        return self.scheduler.remove_job(job_id)

    def pause_job(self, job_id: str):
        """Pause a scheduled job"""
        return self.scheduler.pause_job(job_id)

    def resume_job(self, job_id: str):
        """Resume a paused job"""
        return self.scheduler.resume_job(job_id)
