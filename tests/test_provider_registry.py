from unittest.mock import Mock

from app.cloud.base import CloudProvider
from app.core.config import Settings
from app.services.registry import ExtractorRegistry


def _make_settings(providers=None):
    return Settings(
        enabled_providers=providers or [],
        aws_access_key_id="key",
        aws_secret_access_key="secret",
    )


def _make_registry(sessions=None, settings=None):
    return ExtractorRegistry(sessions or {}, settings or _make_settings())


def _build_aws_sessions(account_id="123456789012", regions=None):
    mock_session = Mock()
    mock_session.account_id = account_id
    mock_session.regions = regions or ["us-east-1"]
    return [
        {
            "session": mock_session,
            "account_id": account_id,
            "regions": regions or ["us-east-1"],
        }
    ]


def test_register_and_unregister_provider():
    registry = _make_registry(settings=_make_settings())
    sessions = _build_aws_sessions()

    added = registry.register_provider(CloudProvider.AWS, sessions)
    assert added > 0
    assert registry.list_services(provider=CloudProvider.AWS)

    removed = registry.unregister_provider_extractors(CloudProvider.AWS)
    assert removed == added
    assert registry.list_services(provider=CloudProvider.AWS) == []


def test_register_multiple_providers():
    registry = _make_registry(settings=_make_settings())

    aws_count = registry.register_provider(
        CloudProvider.AWS, _build_aws_sessions(regions=["us-east-1", "us-west-2"])
    )

    azure_session = Mock()
    azure_session.subscription_id = "sub-1"
    azure_session.locations = ["eastus"]
    azure_count = registry.register_provider(
        CloudProvider.AZURE,
        [
            {
                "session": azure_session,
                "subscription_id": "sub-1",
                "locations": ["eastus"],
            }
        ],
    )

    assert aws_count > 0 and azure_count > 0
    assert len(registry.list_services(provider=CloudProvider.AWS)) == aws_count
    assert len(registry.list_services(provider=CloudProvider.AZURE)) == azure_count

    registry.unregister_provider_extractors(CloudProvider.AWS)
    assert registry.list_services(provider=CloudProvider.AZURE)


def test_unregister_unknown_provider_returns_zero():
    registry = _make_registry()
    assert registry.unregister_provider_extractors(CloudProvider.GCP) == 0


def test_register_provider_with_no_extractors():
    registry = _make_registry()
    empty_sessions = [{"session": Mock(), "account_id": "acct", "regions": []}]
    added = registry.register_provider(CloudProvider.AWS, empty_sessions)
    assert added > 0
    assert len(registry.list_services(provider=CloudProvider.AWS)) == added
