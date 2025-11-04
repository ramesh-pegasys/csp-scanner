import types
from typing import Any, Dict, Optional

import pytest
from fastapi import HTTPException

from app.api.routes import config


class DummySettings:
    def __init__(self, database_enabled: bool = True):
        self.database_enabled = database_enabled


class DummyEntry:
    def __init__(self, description: Optional[str] = None):
        self.description = description


class DummySession:
    def __init__(self, entry: Optional[DummyEntry]):
        self._entry = entry

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        return False

    def query(self, model: Any):
        class _Query:
            def __init__(self, entry: Optional[DummyEntry]):
                self._entry = entry

            def filter(self, *_args, **_kwargs):
                return self

            def first(self):
                return self._entry

        return _Query(self._entry)


@pytest.fixture
def mock_settings(monkeypatch):
    def _mock(database_enabled: bool = True):
        monkeypatch.setattr(
            config, "get_settings", lambda: DummySettings(database_enabled)
        )

    return _mock


def _config_update_payload() -> Dict[str, Any]:
    return {"key": "feature_flag", "value": {"enabled": True}, "description": "test"}


@pytest.mark.asyncio
async def test_get_all_config_success(monkeypatch, mock_settings):
    mock_settings(database_enabled=True)

    class DummyDB:
        def get_all_config(self):
            return {"feature_flag": {"enabled": True}}

    monkeypatch.setattr(config, "get_db_manager", lambda: DummyDB())

    result = await config.get_all_config()
    assert result == {"feature_flag": {"enabled": True}}


@pytest.mark.asyncio
async def test_get_all_config_disabled_database(monkeypatch, mock_settings):
    mock_settings(database_enabled=False)

    with pytest.raises(HTTPException) as exc:
        await config.get_all_config()

    assert exc.value.status_code == 500
    assert exc.value.detail == "Failed to retrieve configuration"


@pytest.mark.asyncio
async def test_get_all_config_unhandled_failure(monkeypatch, mock_settings):
    mock_settings(database_enabled=True)

    def _raise_db_manager():
        raise RuntimeError("boom")

    monkeypatch.setattr(config, "get_db_manager", _raise_db_manager)

    with pytest.raises(HTTPException) as exc:
        await config.get_all_config()

    assert exc.value.status_code == 500


@pytest.mark.asyncio
async def test_get_config_value_success(monkeypatch, mock_settings):
    mock_settings(database_enabled=True)

    class DummyDB:
        def get_config_value(self, key: str):
            assert key == "feature_flag"
            return {"enabled": True}

        def get_session(self):
            return DummySession(DummyEntry(description="toggle for feature"))

    monkeypatch.setattr(config, "get_db_manager", lambda: DummyDB())

    response = await config.get_config_value("feature_flag")
    assert response.key == "feature_flag"
    assert response.value == {"enabled": True}
    assert response.description == "toggle for feature"


@pytest.mark.asyncio
async def test_get_config_value_not_found(monkeypatch, mock_settings):
    mock_settings(database_enabled=True)

    class DummyDB:
        def get_config_value(self, key: str):
            assert key == "missing"
            return None

    monkeypatch.setattr(config, "get_db_manager", lambda: DummyDB())

    with pytest.raises(HTTPException) as exc:
        await config.get_config_value("missing")

    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_get_config_value_database_disabled(mock_settings):
    mock_settings(database_enabled=False)

    with pytest.raises(HTTPException) as exc:
        await config.get_config_value("any")

    assert exc.value.status_code == 400
    assert exc.value.detail == "Database configuration is not enabled"


@pytest.mark.asyncio
async def test_get_config_value_unhandled_failure(monkeypatch, mock_settings):
    mock_settings(database_enabled=True)

    class DummyDB:
        def get_config_value(self, _key: str):
            raise RuntimeError("failure!")

    monkeypatch.setattr(config, "get_db_manager", lambda: DummyDB())

    with pytest.raises(HTTPException) as exc:
        await config.get_config_value("any")

    assert exc.value.status_code == 500


@pytest.mark.asyncio
async def test_create_or_update_config_success(monkeypatch, mock_settings):
    mock_settings(database_enabled=True)
    calls = []

    class DummyDB:
        def set_config_value(
            self, *, key: str, value: Dict[str, Any], description: Optional[str]
        ):
            calls.append((key, value, description))

    monkeypatch.setattr(config, "get_db_manager", lambda: DummyDB())

    payload = _config_update_payload()
    response = await config.create_or_update_config(config.ConfigUpdate(**payload))

    assert calls == [("feature_flag", {"enabled": True}, "test")]
    assert response.key == "feature_flag"
    assert response.value == {"enabled": True}
    assert response.description == "test"


@pytest.mark.asyncio
async def test_create_or_update_config_failure(monkeypatch, mock_settings):
    mock_settings(database_enabled=True)

    class DummyDB:
        def set_config_value(self, **_kwargs):
            raise RuntimeError("cannot write")

    monkeypatch.setattr(config, "get_db_manager", lambda: DummyDB())

    payload = _config_update_payload()

    with pytest.raises(HTTPException) as exc:
        await config.create_or_update_config(config.ConfigUpdate(**payload))

    assert exc.value.status_code == 500


@pytest.mark.asyncio
async def test_create_or_update_config_database_disabled(mock_settings):
    mock_settings(database_enabled=False)

    payload = _config_update_payload()

    with pytest.raises(HTTPException) as exc:
        await config.create_or_update_config(config.ConfigUpdate(**payload))

    assert exc.value.status_code == 500
    assert exc.value.detail == "Failed to update configuration"


@pytest.mark.asyncio
async def test_update_config_value_success(monkeypatch, mock_settings):
    mock_settings(database_enabled=True)
    calls = []

    class DummyDB:
        def get_config_value(self, key: str):
            assert key == "feature_flag"
            return {"enabled": False}

        def set_config_value(self, *, key: str, value: Dict[str, Any], description):
            calls.append((key, value, description))

    monkeypatch.setattr(config, "get_db_manager", lambda: DummyDB())

    response = await config.update_config_value(
        "feature_flag", {"enabled": True}, description="updated"
    )

    assert calls == [("feature_flag", {"enabled": True}, "updated")]
    assert response.value == {"enabled": True}
    assert response.description == "updated"


@pytest.mark.asyncio
async def test_update_config_value_not_found(monkeypatch, mock_settings):
    mock_settings(database_enabled=True)

    class DummyDB:
        def get_config_value(self, key: str):
            assert key == "missing"
            return None

    monkeypatch.setattr(config, "get_db_manager", lambda: DummyDB())

    with pytest.raises(HTTPException) as exc:
        await config.update_config_value("missing", {"enabled": True})

    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_update_config_value_failure(monkeypatch, mock_settings):
    mock_settings(database_enabled=True)

    class DummyDB:
        def get_config_value(self, _key: str):
            return {"enabled": False}

        def set_config_value(self, **_kwargs):
            raise RuntimeError("nope")

    monkeypatch.setattr(config, "get_db_manager", lambda: DummyDB())

    with pytest.raises(HTTPException) as exc:
        await config.update_config_value("feature_flag", {"enabled": True})

    assert exc.value.status_code == 500


@pytest.mark.asyncio
async def test_update_config_value_database_disabled(mock_settings):
    mock_settings(database_enabled=False)

    with pytest.raises(HTTPException) as exc:
        await config.update_config_value("feature_flag", {"enabled": True})

    assert exc.value.status_code == 400
    assert exc.value.detail == "Database configuration is not enabled"


@pytest.mark.asyncio
async def test_delete_config_value_success(monkeypatch, mock_settings):
    mock_settings(database_enabled=True)

    class DummyDB:
        def delete_config_value(self, key: str):
            assert key == "feature_flag"
            return True

    monkeypatch.setattr(config, "get_db_manager", lambda: DummyDB())

    result = await config.delete_config_value("feature_flag")
    assert result == {
        "message": "Configuration key 'feature_flag' deleted successfully"
    }


@pytest.mark.asyncio
async def test_delete_config_value_missing(monkeypatch, mock_settings):
    mock_settings(database_enabled=True)

    class DummyDB:
        def delete_config_value(self, key: str):
            assert key == "missing"
            return False

    monkeypatch.setattr(config, "get_db_manager", lambda: DummyDB())

    with pytest.raises(HTTPException) as exc:
        await config.delete_config_value("missing")

    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_delete_config_value_failure(monkeypatch, mock_settings):
    mock_settings(database_enabled=True)

    class DummyDB:
        def delete_config_value(self, _key: str):
            raise RuntimeError("db error")

    monkeypatch.setattr(config, "get_db_manager", lambda: DummyDB())

    with pytest.raises(HTTPException) as exc:
        await config.delete_config_value("feature_flag")

    assert exc.value.status_code == 500


@pytest.mark.asyncio
async def test_delete_config_value_database_disabled(mock_settings):
    mock_settings(database_enabled=False)

    with pytest.raises(HTTPException) as exc:
        await config.delete_config_value("feature_flag")

    assert exc.value.status_code == 400
    assert exc.value.detail == "Database configuration is not enabled"


@pytest.mark.asyncio
async def test_reload_config(monkeypatch):
    calls = {"cache_clear": False, "called": 0}

    def _get_settings():
        calls["called"] += 1
        return types.SimpleNamespace(environment="unit-test")

    def _cache_clear():
        calls["cache_clear"] = True

    _get_settings.cache_clear = _cache_clear  # type: ignore[attr-defined]

    monkeypatch.setattr("app.core.config.get_settings", _get_settings, raising=False)

    result = await config.reload_config()

    assert calls["cache_clear"] is True
    assert calls["called"] == 1
    assert result == {
        "message": "Configuration reloaded successfully",
        "environment": "unit-test",
    }


@pytest.mark.asyncio
async def test_reload_config_failure(monkeypatch):
    def _failing_get_settings():
        raise RuntimeError("boom")

    _failing_get_settings.cache_clear = lambda: None  # type: ignore[attr-defined]

    monkeypatch.setattr(
        "app.core.config.get_settings", _failing_get_settings, raising=False
    )

    with pytest.raises(HTTPException) as exc:
        await config.reload_config()

    assert exc.value.status_code == 500
    assert exc.value.detail == "Failed to reload configuration"
