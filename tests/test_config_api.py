import pytest
from fastapi.testclient import TestClient
from typing import Any, Dict, List
from types import SimpleNamespace

from app.main import app


@pytest.fixture(autouse=True)
def mock_config_dependencies(monkeypatch):
    """Mock database interactions for config endpoints."""
    from app.core.config import Settings

    state: Dict[str, Any] = {
        "config": {
            "debug": False,
            "enabled_providers": ["aws"],
            "aws_accounts": [
                {
                    "account_id": "123456789012",
                    "regions": ["us-east-1"],
                }
            ],
            "aws_access_key_id": "test-key",
            "aws_secret_access_key": "test-secret",
            "aws_default_region": "us-east-1",
        },
        "version": 1,
    }

    def build_settings() -> Settings:
        config = state["config"]
        return Settings(
            database_enabled=True,
            debug=config.get("debug", False),
            max_concurrent_extractors=config.get("max_concurrent_extractors", 10),
            enabled_providers=config.get("enabled_providers", []),
            aws_accounts=config.get("aws_accounts"),
            aws_access_key_id=config.get("aws_access_key_id"),
            aws_secret_access_key=config.get("aws_secret_access_key"),
            aws_default_region=config.get("aws_default_region", "us-east-1"),
        )

    class GetSettingsStub:
        def __call__(self) -> Settings:
            return build_settings()

        @staticmethod
        def cache_clear() -> None:
            # No cached state to clear for the stub
            return None

    class DummyDBManager:
        def __init__(self) -> None:
            active_entry = {
                "id": 1,
                "version": 1,
                "is_active": True,
                "description": "Initial config",
                "created_at": "2025-01-01T00:00:00Z",
                "updated_at": "2025-01-01T00:00:00Z",
                "config": state["config"],
            }
            inactive_entry = {
                "id": 2,
                "version": 2,
                "is_active": False,
                "description": "Old config",
                "created_at": "2025-01-01T00:00:00Z",
                "updated_at": "2025-01-01T00:00:00Z",
                "config": state["config"],
            }
            self._versions: List[Dict[str, Any]] = [active_entry, inactive_entry]

        def get_active_config(self) -> Dict[str, Any]:
            return state["config"]

        def create_config_version(
            self,
            config: Dict[str, Any],
            description: str | None = None,
            set_active: bool = True,
        ) -> int:
            state["config"] = config
            state["version"] += 1
            entry = {
                "id": state["version"],
                "version": state["version"],
                "is_active": True,
                "description": description or "Updated config",
                "created_at": "2025-01-02T00:00:00Z",
                "updated_at": "2025-01-02T00:00:00Z",
                "config": config,
            }
            self._versions.insert(0, entry)
            return state["version"]

        def list_config_versions(self, limit: int = 50) -> List[Dict[str, Any]]:
            return self._versions[:limit]

        def activate_config_version(self, version: int) -> bool:
            # Mock activation - return False for non-existent versions
            for v in self._versions:
                if v["version"] == version:
                    return True
            return False

        def delete_config_version(self, version: int) -> bool:
            # Mock deletion - return False for non-existent or active versions
            for v in self._versions:
                if v["version"] == version:
                    if v["is_active"]:
                        return False  # Cannot delete active version
                    self._versions.remove(v)
                    return True
            return False

        def get_config_version(self, version: int) -> Dict[str, Any] | None:
            # Mock getting a specific version
            for v in self._versions:
                if v["version"] == version:
                    return v["config"]
            return None

    get_settings_stub = GetSettingsStub()
    dummy_db = DummyDBManager()

    monkeypatch.setattr("app.api.routes.config.get_settings", get_settings_stub)
    monkeypatch.setattr("app.api.routes.config.get_db_manager", lambda: dummy_db)


@pytest.fixture
def client():
    return TestClient(app)


@pytest.mark.parametrize(
    "endpoint,expected_status",
    [
        ("/api/v1/config/", 200),
        ("/api/v1/config/versions", 200),
    ],
)
def test_get_config_endpoints(client, endpoint, expected_status):
    response = client.get(endpoint)
    assert response.status_code == expected_status
    assert "config" in response.json() or isinstance(response.json(), list)


def test_patch_config(client):
    client.app.state.orchestrator = SimpleNamespace(max_concurrent=0)
    payload = {
        "config": {"debug": False, "enabled_providers": ["aws"]},
        "description": "Test patch config",
    }
    response = client.patch("/api/v1/config/", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["applied"] is True
    assert data["config"]["debug"] is False
    assert "enabled_providers" in data["config"]


def test_update_config_success(client):
    client.app.state.orchestrator = SimpleNamespace(max_concurrent=0)
    payload = {
        "config": {
            "debug": True,
            "enabled_providers": ["aws"],
            "max_concurrent_extractors": 7,
        },
        "description": "Raise concurrency",
    }
    response = client.put("/api/v1/config/", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["applied"] is True
    assert data["config"]["max_concurrent_extractors"] == 7
    assert client.app.state.orchestrator.max_concurrent == 7


def test_reload_config(client):
    client.app.state.orchestrator = SimpleNamespace(max_concurrent=0)
    response = client.post("/api/v1/config/reload")
    assert response.status_code == 200
    data = response.json()
    assert data["applied"] is True
    assert "config" in data


def test_config_versions(client):
    response = client.get("/api/v1/config/versions")
    assert response.status_code == 200
    versions = response.json()
    assert isinstance(versions, list)
    if versions:
        assert "version" in versions[0]
        assert "is_active" in versions[0]


def test_get_config_version(client):
    response = client.get("/api/v1/config/versions/1")
    assert response.status_code == 200
    data = response.json()
    assert data["version"] == 1
    assert "config" in data


def test_activate_config_version(client):
    response = client.post("/api/v1/config/versions/1/activate")
    assert response.status_code == 200
    data = response.json()
    assert data["applied"] is True


def test_delete_config_version(client):
    response = client.delete("/api/v1/config/versions/2")
    assert response.status_code == 200


@pytest.mark.parametrize(
    "endpoint,method,data,expected_status",
    [
        ("/api/v1/config/", "put", {"config": {"debug": True}}, 400),
        ("/api/v1/config/", "patch", {"config": {"debug": True}}, 400),
        (
            "/api/v1/config/reload",
            "post",
            None,
            200,
        ),  # Reload works even with DB disabled
        ("/api/v1/config/versions", "get", None, 400),
        ("/api/v1/config/versions/1", "get", None, 400),
        ("/api/v1/config/versions/1/activate", "post", None, 400),
        ("/api/v1/config/versions/2", "delete", None, 400),
    ],
)
def test_config_endpoints_database_disabled(
    client, monkeypatch, endpoint, method, data, expected_status
):
    """Test that endpoints return 400 when database is disabled."""
    from app.core.config import Settings

    # Mock get_settings to return database_enabled=False
    class MockSettingsFunction:
        def __call__(self):
            return Settings(
                database_enabled=False,
                debug=False,
                enabled_providers=["aws"],
                aws_accounts=[],
                aws_access_key_id="test",
                aws_secret_access_key="test",
                aws_default_region="us-east-1",
            )

        def cache_clear(self):
            pass

    mock_get_settings = MockSettingsFunction()

    # Override the fixture's monkeypatch
    monkeypatch.setattr("app.api.routes.config.get_settings", mock_get_settings)

    response = None
    if method == "get":
        response = client.get(endpoint)
    elif method == "post":
        response = client.post(endpoint)
    elif method == "put":
        response = client.put(endpoint, json=data)
    elif method == "patch":
        response = client.patch(endpoint, json=data)
    elif method == "delete":
        response = client.delete(endpoint)

    assert response is not None
    assert response.status_code == expected_status
    if expected_status == 400:
        assert "Database must be enabled" in response.json()["detail"]


def test_get_config_version_not_found(client):
    """Test getting a non-existent config version."""
    response = client.get("/api/v1/config/versions/999")
    assert response.status_code == 404
    assert "not found" in response.json()["detail"]


def test_activate_config_version_not_found(client):
    """Test activating a non-existent config version."""
    response = client.post("/api/v1/config/versions/999/activate")
    assert response.status_code == 404
    assert "not found" in response.json()["detail"]
