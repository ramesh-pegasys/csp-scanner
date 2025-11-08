"""Tests for core modules"""

import os
from types import SimpleNamespace

import pytest
from unittest.mock import Mock, mock_open, patch

from app.core.config import Settings, _load_config_from_database


def test_settings_defaults(monkeypatch):
    """Test settings with default values"""
    monkeypatch.delenv("AWS_REGION", raising=False)
    monkeypatch.delenv("CONFIG_FILE", raising=False)
    settings = Settings()

    assert settings.app_name == "Cloud Artifact Extractor"
    assert settings.environment == "development"
    assert settings.debug is False
    assert settings.transport_config["http_endpoint_url"] == "http://localhost:8000"
    assert settings.transport_config["timeout_seconds"] == 30
    assert settings.transport_config["max_retries"] == 3
    assert settings.max_concurrent_extractors == 10
    assert settings.batch_size == 100
    assert settings.api_key_enabled is False


def test_settings_transport_config():
    """Test transport config property with transport dict"""
    settings = Settings(
        transport={
            "type": "http",
            "http_endpoint_url": "https://scanner.example.com",
            "api_key": "test-key",
            "timeout_seconds": 60,
            "max_retries": 5,
        }
    )

    config = settings.transport_config
    assert config["http_endpoint_url"] == "https://scanner.example.com"
    assert config["api_key"] == "test-key"
    assert config["timeout_seconds"] == 60
    assert config["max_retries"] == 5


def test_settings_transport_config_filesystem():
    """Test filesystem transport config"""
    settings = Settings(
        transport={
            "type": "filesystem",
            "base_dir": "/tmp",
            "create_dir": False,
        }
    )
    config = settings.transport_config
    assert config["type"] == "filesystem"
    assert config["base_dir"] == "/tmp"
    assert config["create_dir"] is False


def test_settings_transport_config_null():
    """Test null transport config"""
    settings = Settings(transport={"type": "null"})
    assert settings.transport_config == {"type": "null"}


def test_settings_transport_config_dict():
    """Test transport config with transport dict"""
    settings = Settings(
        transport={
            "type": "http",
            "http_endpoint_url": "https://example.com",
            "api_key": "key123",
        }
    )
    config = settings.transport_config
    assert config["type"] == "http"
    assert config["http_endpoint_url"] == "https://example.com"
    assert config["api_key"] == "key123"


def test_settings_orchestrator_config():
    """Test orchestrator config property"""
    settings = Settings(max_concurrent_extractors=20, batch_delay_seconds=0.5)

    config = settings.orchestrator_config
    assert config["max_workers"] == 20
    assert config["batch_delay_seconds"] == 0.5


@patch("os.path.exists")
@patch(
    "builtins.open",
    new_callable=mock_open,
    read_data="""
ec2:
  enabled: true
  regions: ['us-east-1', 'us-west-2']
s3:
  enabled: false
""",
)
def test_settings_extractors_config(mock_file, mock_exists):
    """Test extractors config loading"""
    mock_exists.return_value = True

    settings = Settings(extractor_config_path="config/extractors.yaml")
    extractors = settings.extractors

    assert extractors["ec2"]["enabled"] is True
    assert extractors["s3"]["enabled"] is False


@patch("os.path.exists")
def test_settings_extractors_config_missing(mock_exists):
    """Test extractors config when file doesn't exist"""
    mock_exists.return_value = False

    settings = Settings()
    extractors = settings.extractors

    assert extractors == {}


@patch("app.core.config.Settings")
def test_get_settings_cached(mock_settings_class):
    """Test get_settings caching"""
    from app.core.config import get_settings

    # Clear the LRU cache to ensure clean state
    get_settings.cache_clear()

    mock_instance = Mock()
    mock_settings_class.return_value = mock_instance

    # First call
    settings1 = get_settings()
    # Second call should return cached instance
    settings2 = get_settings()

    assert settings1 is settings2
    mock_settings_class.assert_called_once()


def test_get_settings_from_config_file(tmp_path, monkeypatch):
    config_file = tmp_path / "config.yaml"
    config_file.write_text("app_name: Custom App\nmax_concurrent_extractors: 20\n")
    monkeypatch.setenv("CONFIG_FILE", str(config_file))
    monkeypatch.delenv("AWS_REGION", raising=False)

    from app.core import config as config_module

    fake_settings = Settings(
        app_name="Custom App",
        max_concurrent_extractors=20,
    )

    class FakeGetSettings:
        def __call__(self) -> Settings:
            return fake_settings

        @staticmethod
        def cache_clear() -> None:
            return None

    fake_get_settings = FakeGetSettings()
    monkeypatch.setattr(config_module, "get_settings", fake_get_settings)

    settings = config_module.get_settings()

    assert settings.app_name == "Custom App"
    assert settings.max_concurrent_extractors == 20


def test_settings_provider_enabled_properties():
    """Test provider enabled properties in Settings"""
    # Test AWS enabled
    settings_aws = Settings(enabled_providers=["aws"])
    assert settings_aws.is_aws_enabled is True
    assert settings_aws.is_azure_enabled is False
    assert settings_aws.is_gcp_enabled is False

    # Test Azure enabled
    settings_azure = Settings(enabled_providers=["azure"])
    assert settings_azure.is_aws_enabled is False
    assert settings_azure.is_azure_enabled is True
    assert settings_azure.is_gcp_enabled is False

    # Test GCP enabled
    settings_gcp = Settings(enabled_providers=["gcp"])
    assert settings_gcp.is_aws_enabled is False
    assert settings_gcp.is_azure_enabled is False
    assert settings_gcp.is_gcp_enabled is True

    # Test multiple providers
    settings_multi = Settings(enabled_providers=["aws", "gcp"])
    assert settings_multi.is_aws_enabled is True
    assert settings_multi.is_azure_enabled is False
    assert settings_multi.is_gcp_enabled is True

    # Test no providers
    settings_none = Settings(enabled_providers=[])
    assert settings_none.is_aws_enabled is False
    assert settings_none.is_azure_enabled is False
    assert settings_none.is_gcp_enabled is False


def test_settings_database_url_with_credentials(monkeypatch):
    monkeypatch.delenv("CSP_SCANNER_DATABASE_USER", raising=False)
    monkeypatch.delenv("CSP_SCANNER_DATABASE_PASSWORD", raising=False)
    settings = Settings(
        database_enabled=True,
        database_user="user",
        database_password="pass",
        database_host="db.example.com",
        database_port=5433,
        database_name="custom_db",
    )
    assert (
        settings.database_url == "postgresql://user:pass@db.example.com:5433/custom_db"
    )


def test_load_config_from_database_returns_data(monkeypatch):
    monkeypatch.setenv("CSP_SCANNER_DATABASE_ENABLED", "true")

    dummy_db = SimpleNamespace(get_active_config=lambda: {"feature": {"enabled": True}})
    monkeypatch.setattr(
        "app.core.config.get_db_manager", lambda: dummy_db, raising=False
    )
    monkeypatch.setenv("CSP_SCANNER_DATABASE_ENABLED", "true")
    result = _load_config_from_database()
    assert result == {"feature": {"enabled": True}}


@pytest.fixture(autouse=True)
def clear_config_env(monkeypatch):
    monkeypatch.delenv("CONFIG_FILE", raising=False)
    monkeypatch.delenv("AWS_ACCOUNT_ID", raising=False)
    monkeypatch.delenv("AWS_DEFAULT_REGION", raising=False)
    monkeypatch.delenv("AWS_REGION", raising=False)
    monkeypatch.delenv("ENABLED_PROVIDERS", raising=False)
    monkeypatch.delenv("AZURE_SUBSCRIPTION_ID", raising=False)
    monkeypatch.delenv("AZURE_DEFAULT_LOCATION", raising=False)
    monkeypatch.delenv("GCP_PROJECT_ID", raising=False)
    monkeypatch.delenv("GCP_DEFAULT_REGION", raising=False)
    monkeypatch.delenv("DATABASE_ENABLED", raising=False)
    monkeypatch.delenv("GCP_CREDENTIALS_PATH", raising=False)
    # Clear nested database env vars that override Settings defaults
    monkeypatch.delenv("CSP_SCANNER_DATABASE__ENABLED", raising=False)
    monkeypatch.delenv("CSP_SCANNER_DATABASE__HOST", raising=False)
    monkeypatch.delenv("CSP_SCANNER_DATABASE__PORT", raising=False)
    monkeypatch.delenv("CSP_SCANNER_DATABASE__NAME", raising=False)
    monkeypatch.delenv("CSP_SCANNER_DATABASE__USER", raising=False)
    monkeypatch.delenv("CSP_SCANNER_DATABASE__PASSWORD", raising=False)
    monkeypatch.delenv("CSP_SCANNER_DATABASE_ENABLED", raising=False)
    monkeypatch.delenv("CSP_SCANNER_DATABASE_HOST", raising=False)
    monkeypatch.delenv("CSP_SCANNER_DATABASE_PORT", raising=False)
    monkeypatch.delenv("CSP_SCANNER_DATABASE_NAME", raising=False)
    monkeypatch.delenv("CSP_SCANNER_DATABASE_USER", raising=False)
    monkeypatch.delenv("CSP_SCANNER_DATABASE_PASSWORD", raising=False)


def test_settings_aws_accounts_list():
    """Test AWS accounts list property"""
    # Test with aws_accounts set
    settings = Settings(aws_accounts=[{"account_id": "123", "regions": ["us-east-1"]}])
    assert settings.aws_accounts_list == [
        {"account_id": "123", "regions": ["us-east-1"]}
    ]

    # Test with multiple accounts
    settings_multi = Settings(
        aws_accounts=[
            {"account_id": "456", "regions": ["us-west-2"]},
            {"account_id": "789", "regions": ["eu-west-1", "eu-central-1"]},
        ]
    )
    assert len(settings_multi.aws_accounts_list) == 2
    assert settings_multi.aws_accounts_list[0]["account_id"] == "456"
    assert settings_multi.aws_accounts_list[1]["account_id"] == "789"

    # Test empty when no config
    settings_empty = Settings()
    assert settings_empty.aws_accounts_list == []


def test_settings_azure_accounts_list():
    """Test Azure accounts list property"""
    # Clear environment variables that might affect the test

    original_env = {}
    for key in [
        "AZURE_TENANT_ID",
        "AZURE_CLIENT_ID",
        "AZURE_CLIENT_SECRET",
    ]:
        if key in os.environ:
            original_env[key] = os.environ[key]
            del os.environ[key]

    try:
        # Test with azure_accounts set
        settings = Settings(
            azure_accounts=[{"subscription_id": "sub1", "locations": ["eastus"]}]
        )
        assert settings.azure_accounts_list == [
            {"subscription_id": "sub1", "locations": ["eastus"]}
        ]

        # Test with multiple subscriptions
        settings_multi = Settings(
            azure_accounts=[
                {"subscription_id": "sub2", "locations": ["westus"]},
                {"subscription_id": "sub3", "locations": ["uksouth", "northeurope"]},
            ]
        )
        assert len(settings_multi.azure_accounts_list) == 2
        assert settings_multi.azure_accounts_list[0]["subscription_id"] == "sub2"
        assert settings_multi.azure_accounts_list[1]["subscription_id"] == "sub3"

        # Test empty when no config
        settings_empty = Settings()
        assert settings_empty.azure_accounts_list == []
    finally:
        # Restore environment variables
        for key, value in original_env.items():
            os.environ[key] = value


def test_settings_gcp_projects_list():
    """Test GCP projects list property"""
    # Test with gcp_projects set
    settings = Settings(
        gcp_projects=[{"project_id": "proj1", "regions": ["us-central1"]}]
    )
    assert settings.gcp_projects_list == [
        {"project_id": "proj1", "regions": ["us-central1"]}
    ]

    # Test with multiple projects
    settings_multi = Settings(
        gcp_projects=[
            {"project_id": "proj2", "regions": ["europe-west1"]},
            {"project_id": "proj3", "regions": ["asia-east1", "asia-southeast1"]},
        ]
    )
    assert len(settings_multi.gcp_projects_list) == 2
    assert settings_multi.gcp_projects_list[0]["project_id"] == "proj2"
    assert settings_multi.gcp_projects_list[1]["project_id"] == "proj3"

    # Test empty when no config
    settings_empty = Settings()
    assert settings_empty.gcp_projects_list == []


def test_settings_database_url_without_credentials():
    """Test database URL construction without user credentials"""
    settings = Settings(
        database_enabled=True,
        database_host="db.example.com",
        database_port=5432,
        database_name="testdb",
    )
    expected = "postgresql://db.example.com:5432/testdb"
    print(f"Expected: {expected}, Actual: {settings.database_url}")
    assert settings.database_url == expected


@patch("app.core.config._load_config_from_database")
@patch("app.core.config.Settings")
def test_get_settings_with_db_config(mock_settings_class, mock_load_db):
    """Test get_settings with database config"""
    from app.core.config import get_settings

    get_settings.cache_clear()

    mock_load_db.return_value = {"app_name": "DB App", "debug": True}
    mock_instance = Mock()
    mock_settings_class.return_value = mock_instance

    settings = get_settings()

    assert settings is mock_instance
    mock_load_db.assert_called_once()
    mock_settings_class.assert_called_once_with(app_name="DB App", debug=True)


@patch("app.core.config.get_db_manager")
@patch.dict(os.environ, {"CSP_SCANNER_DATABASE_ENABLED": "true"})
def test_load_config_from_database_exception(mock_get_db_manager):
    """Test _load_config_from_database handles exceptions"""
    from app.core.config import _load_config_from_database

    mock_get_db_manager.side_effect = Exception("DB connection failed")

    with patch("logging.getLogger") as mock_get_logger:
        mock_logger = Mock()
        mock_get_logger.return_value = mock_logger
        result = _load_config_from_database()

    assert result == {}
    mock_logger.error.assert_called_once()
