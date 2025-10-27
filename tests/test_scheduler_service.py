"""Tests for SchedulerService."""

from unittest.mock import MagicMock, patch

from app.services.scheduler import SchedulerService


def test_scheduler_service_lifecycle():
    with patch("app.services.scheduler.AsyncIOScheduler") as mock_scheduler_cls:
        scheduler_instance = MagicMock()
        scheduler_instance.running = False
        mock_scheduler_cls.return_value = scheduler_instance

        service = SchedulerService()

        service.start()
        scheduler_instance.start.assert_called_once()

        scheduler_instance.running = True
        service.shutdown()
        scheduler_instance.shutdown.assert_called_once()


def test_scheduler_service_job_operations():
    with patch("app.services.scheduler.AsyncIOScheduler") as mock_scheduler_cls:
        scheduler_instance = MagicMock()
        mock_scheduler_cls.return_value = scheduler_instance

        service = SchedulerService()

        service.add_job(lambda: None, "interval", id="job", name="Job")
        scheduler_instance.add_job.assert_called_once()

        service.get_jobs()
        scheduler_instance.get_jobs.assert_called_once()

        service.get_job("job")
        scheduler_instance.get_job.assert_called_once_with("job")

        service.pause_job("job")
        scheduler_instance.pause_job.assert_called_once_with("job")

        service.resume_job("job")
        scheduler_instance.resume_job.assert_called_once_with("job")

        service.remove_job("job")
        scheduler_instance.remove_job.assert_called_once_with("job")
