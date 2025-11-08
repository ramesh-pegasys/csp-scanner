from pathlib import Path

import pytest

from app.models.database import DatabaseManager


def _make_sqlite_url(tmp_path: Path) -> str:
    """Build a sqlite database URL backed by a temporary file."""
    db_file = tmp_path / "db.sqlite"
    return f"sqlite:///{db_file}"


@pytest.fixture(autouse=True)
def stub_mask_sensitive(monkeypatch):
    """Ensure database manager can mask config even if helper absent."""

    def _noop(config):
        return config

    monkeypatch.setattr(
        "app.models.database.mask_sensitive_config", _noop, raising=False
    )

    import importlib

    config_module = importlib.import_module("app.core.config")
    if not hasattr(config_module, "mask_sensitive_config"):
        monkeypatch.setattr(
            config_module, "mask_sensitive_config", _noop, raising=False
        )


def test_global_config_crud(tmp_path):
    manager = DatabaseManager(_make_sqlite_url(tmp_path))

    # Global config starts empty
    assert manager.get_global_config() is None

    manager.set_global_config({"debug": True})
    assert manager.get_global_config() == {"debug": True}

    manager.set_config_value("logging", {"level": "DEBUG"})
    assert manager.get_config_value("logging") == {"level": "DEBUG"}

    all_config = manager.get_all_config()
    assert "logging" in all_config

    assert manager.delete_config_value("logging") is True
    assert manager.get_config_value("logging") is None
    assert manager.delete_config_value("missing") is False

    # Ensure explicit table creation works when tables already exist
    manager.create_tables()

    assert manager.is_database_available() is True
    manager.close()


def test_config_version_workflow(tmp_path):
    manager = DatabaseManager(_make_sqlite_url(tmp_path))

    first_version = manager.create_config_version(
        {"debug": True}, description="initial", set_active=True
    )
    assert first_version == 1
    assert manager.get_active_config() == {"debug": True}

    second_version = manager.create_config_version(
        {"debug": False}, description="secondary", set_active=False
    )
    assert second_version == 2

    # Active version should still be the first one until we switch
    assert manager.get_active_config() == {"debug": True}

    assert manager.activate_config_version(second_version) is True
    assert manager.get_active_config() == {"debug": False}
    assert manager.activate_config_version(42) is False

    # Latest versions should be ordered newest first
    versions = manager.list_config_versions()
    assert versions[0]["version"] == second_version
    assert versions[-1]["version"] == first_version
    assert versions[0]["is_active"] is True

    assert manager.get_config_version(first_version) == {"debug": True}
    assert manager.get_config_version(99) is None

    # Cannot delete the active version
    assert manager.delete_config_version(second_version) is False
    assert manager.delete_config_version(first_version) is True

    manager.close()


def test_job_crud_operations(tmp_path):
    manager = DatabaseManager(_make_sqlite_url(tmp_path))

    job_id = "job-123"
    manager.create_job(
        job_id,
        services=["s3", "ec2"],
        regions=["us-east-1"],
        filters={"tag": "prod"},
        batch_size=50,
    )

    job = manager.get_job(job_id)
    assert job is not None
    assert job["status"] == "running"
    assert job["services"] == ["s3", "ec2"]

    manager.update_job(
        job_id,
        status="completed",
        total_artifacts=10,
        successful_artifacts=9,
        failed_artifacts=1,
        errors=["one failure"],
    )

    updated = manager.get_job(job_id)
    assert updated["status"] == "completed"
    assert updated["failed_artifacts"] == 1
    assert updated["errors"] == ["one failure"]

    jobs = manager.list_jobs(status="completed")
    assert any(j["id"] == job_id for j in jobs)

    # Mark job as older than cutoff to exercise delete_old_jobs
    from datetime import datetime, timezone, timedelta
    from app.models.database import ExtractionJob

    with manager.get_session() as session:
        db_job = session.query(ExtractionJob).filter(ExtractionJob.id == job_id).first()
        assert db_job is not None
        db_job.started_at = datetime.now(timezone.utc) - timedelta(days=10)
        session.commit()

    deleted = manager.delete_old_jobs(days=5)
    assert deleted == 1
    assert manager.get_job(job_id) is None

    manager.close()


def test_schedule_crud_operations(tmp_path):
    manager = DatabaseManager(_make_sqlite_url(tmp_path))

    schedule_id = "sched-1"
    manager.create_schedule(
        schedule_id,
        name="Nightly",
        cron_expression="0 2 * * *",
        services=["s3"],
        regions=["us-east-1"],
        filters={"tag": "nightly"},
        batch_size=25,
        description="Nightly scan",
    )

    schedule = manager.get_schedule(schedule_id)
    assert schedule is not None
    assert schedule["is_active"] is True

    manager.update_schedule(
        schedule_id,
        paused=True,
        description="Updated schedule",
        batch_size=30,
    )

    updated = manager.get_schedule(schedule_id)
    assert updated["paused"] is True
    assert updated["description"] == "Updated schedule"
    assert updated["batch_size"] == 30

    active_schedules = manager.list_schedules(active_only=True)
    assert len(active_schedules) == 1
    assert active_schedules[0]["id"] == schedule_id

    assert manager.delete_schedule(schedule_id) is True
    assert manager.get_schedule(schedule_id) is None
    manager.close()


def test_database_manager_builds_url_from_env(monkeypatch):
    monkeypatch.setenv("CSP_SCANNER_DATABASE_HOST", "envhost")
    monkeypatch.setenv("CSP_SCANNER_DATABASE_PORT", "6543")
    monkeypatch.setenv("CSP_SCANNER_DATABASE_NAME", "envdb")
    monkeypatch.setenv("CSP_SCANNER_DATABASE_USER", "user")
    monkeypatch.setenv("CSP_SCANNER_DATABASE_PASSWORD", "pass")

    recorded: dict[str, str] = {}

    class DummyEngine:
        def dispose(self) -> None:
            recorded["disposed"] = "yes"

    def fake_create_engine(url: str, echo: bool = False):
        recorded["url"] = url
        return DummyEngine()

    def fake_sessionmaker(**_kwargs):
        return lambda: None

    monkeypatch.setattr("app.models.database.create_engine", fake_create_engine)
    monkeypatch.setattr("app.models.database.sessionmaker", fake_sessionmaker)
    monkeypatch.setattr(
        "app.models.database.Base.metadata.create_all", lambda bind: None
    )

    manager = DatabaseManager()
    assert recorded["url"] == "postgresql://user:pass@envhost:6543/envdb"
    manager.close()
    assert recorded["disposed"] == "yes"


def test_ensure_tables_exist_logs_warning(tmp_path, monkeypatch):
    url = _make_sqlite_url(tmp_path)

    calls: dict[str, int] = {"warning": 0, "info": 0}

    def failing_create_all(bind):
        raise RuntimeError("explosion")

    class DummyLogger:
        def warning(self, *_args, **_kwargs):
            calls["warning"] += 1

        def info(self, *_args, **_kwargs):
            calls["info"] += 1

        def addHandler(self, *_args, **_kwargs):
            pass

        def removeHandler(self, *_args, **_kwargs):
            pass

        def setLevel(self, *_args, **_kwargs):
            pass

        def isEnabledFor(self, *_args, **_kwargs):
            return False

    monkeypatch.setattr(
        "app.models.database.Base.metadata.create_all", failing_create_all
    )
    monkeypatch.setattr("logging.getLogger", lambda name=None: DummyLogger())

    manager = DatabaseManager(url)
    # Ensure fallback paths logged but no exception bubbled
    assert calls["warning"] >= 1
    assert calls["info"] >= 1
    manager.close()
