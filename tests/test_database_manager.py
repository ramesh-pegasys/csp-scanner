from pathlib import Path

import pytest

from app.models.database import DatabaseManager


def _make_sqlite_url(tmp_path: Path) -> str:
    """Build a sqlite database URL backed by a temporary file."""
    db_file = tmp_path / "db.sqlite"
    return f"sqlite:///{db_file}"


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
    assert (
        recorded["url"]
        == "postgresql://user:pass@envhost:6543/envdb"
    )
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
