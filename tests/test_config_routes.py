from typing import Any, Optional

import pytest
from fastapi import HTTPException

from app.api.routes import config
from app.core.config import Settings


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


def _raise_db_manager():
    raise RuntimeError("boom")


@pytest.mark.asyncio
async def test_get_all_config_db_error(monkeypatch):
    class GetSettingsStub:
        def __call__(self) -> Settings:
            return Settings(database_enabled=True)

        @staticmethod
        def cache_clear() -> None:
            return None

    monkeypatch.setattr(config, "get_settings", GetSettingsStub())
    monkeypatch.setattr(config, "get_db_manager", _raise_db_manager)

    with pytest.raises(HTTPException):
        await config.get_current_config()
