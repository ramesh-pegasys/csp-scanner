"""Tests for core modules"""
import pytest
from unittest.mock import Mock, patch, mock_open
import os
from app.core.config import Settings, get_settings


def test_settings_defaults(monkeypatch):
    """Test settings with default values"""
    monkeypatch.delenv("AWS_REGION", raising=False)
    monkeypatch.delenv("AWS_DEFAULT_REGION", raising=False)
    monkeypatch.delenv("CONFIG_FILE", raising=False)
    settings = Settings()
    
    assert settings.app_name == "Cloud Artifact Extractor"
    assert settings.environment == "development"
    assert settings.debug is False
    assert settings.aws_default_region == "us-east-1"
    assert settings.scanner_endpoint_url == "http://localhost:8000"
    assert settings.transport_timeout_seconds == 30
    assert settings.transport_max_retries == 3
    assert settings.max_concurrent_extractors == 10
    assert settings.batch_size == 100
    assert settings.api_key_enabled is False


def test_settings_transport_config():
    """Test transport config property"""
    settings = Settings(
        scanner_endpoint_url="https://scanner.example.com",
        scanner_api_key="test-key",
        transport_timeout_seconds=60,
        transport_max_retries=5
    )
    
    config = settings.transport_config
    assert config['scanner_endpoint_url'] == "https://scanner.example.com"
    assert config['api_key'] == "test-key"
    assert config['timeout_seconds'] == 60
    assert config['max_retries'] == 5
    assert 'Content-Type' in config['headers']
    assert 'User-Agent' in config['headers']


def test_settings_transport_config_filesystem():
    settings = Settings(transport_type="filesystem", filesystem_base_dir="/tmp", filesystem_create_dir=False)
    config = settings.transport_config
    assert config['base_dir'] == "/tmp"
    assert config['create_dir'] is False


def test_settings_transport_config_null():
    settings = Settings(transport_type="null")
    assert settings.transport_config == {}


def test_settings_orchestrator_config():
    """Test orchestrator config property"""
    settings = Settings(
        max_concurrent_extractors=20,
        batch_delay_seconds=0.5
    )
    
    config = settings.orchestrator_config
    assert config['max_workers'] == 20
    assert config['batch_delay_seconds'] == 0.5


@patch('os.path.exists')
@patch('builtins.open', new_callable=mock_open, read_data="""
ec2:
  enabled: true
  regions: ['us-east-1', 'us-west-2']
s3:
  enabled: false
""")
def test_settings_extractors_config(mock_file, mock_exists):
    """Test extractors config loading"""
    mock_exists.return_value = True
    
    settings = Settings(extractor_config_path="config/extractors.yaml")
    extractors = settings.extractors
    
    assert extractors['ec2']['enabled'] is True
    assert extractors['s3']['enabled'] is False


@patch('os.path.exists')
def test_settings_extractors_config_missing(mock_exists):
    """Test extractors config when file doesn't exist"""
    mock_exists.return_value = False
    
    settings = Settings()
    extractors = settings.extractors
    
    assert extractors == {}


@patch('app.core.config.Settings')
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
    config_file.write_text("app_name: Custom App\naws_default_region: eu-central-1\n")
    monkeypatch.setenv("CONFIG_FILE", str(config_file))
    monkeypatch.delenv("AWS_REGION", raising=False)
    monkeypatch.delenv("AWS_DEFAULT_REGION", raising=False)

    from app.core.config import get_settings
    get_settings.cache_clear()
    settings = get_settings()

    assert settings.app_name == "Custom App"
    assert settings.aws_default_region == "eu-central-1"
