from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.transport.aegis_policy_scanner_transport import (
    AegisPolicyScannerTransport,
)


@pytest.fixture
def transport_config():
    return {
        "aegis_host": "aegis.example.com",
        "policy_name": "default-policy",
        "max_concurrent_requests": 2,
        "max_retries": 3,
        "allow_insecure_ssl": False,
        "labels": {"env": "test"},
        "aws_accounts": [
            {
                "account_id": "123456789012",
                "regions": [
                    {"name": "us-west-2", "policy_name": "aws-us-west-2-policy"},
                    "us-east-1",
                ],
            }
        ],
        "gcp_projects": [
            {
                "project_id": "proj-1",
                "regions": [
                    {"name": "us-central1", "policy_name": "gcp-us-central1-policy"}
                ],
            }
        ],
        "azure_subscriptions": [
            {
                "subscription_id": "sub-1",
                "locations": [
                    {"name": "eastus", "policy_name": "azure-eastus-policy"},
                    "westus",
                ],
            }
        ],
    }


@pytest.fixture(autouse=True)
def mock_env(monkeypatch):
    monkeypatch.setenv("AEGIS_TOKEN", "test-token")


def test_generate_cloud_labels(transport_config):
    transport = AegisPolicyScannerTransport(transport_config)

    labels = transport._generate_cloud_labels(transport_config, {"env": "test"})
    assert labels["env"] == "test"
    assert labels["aws_123456789012_us-west-2"].endswith("policy:aws-us-west-2-policy")
    assert labels["gcp_proj-1_us-central1"].endswith("policy:gcp-us-central1-policy")
    assert labels["azure_sub-1_eastus"].endswith("policy:azure-eastus-policy")
    assert "azure_sub-1_westus" in labels


@pytest.mark.asyncio
async def test_send_success(monkeypatch, transport_config):
    transport = AegisPolicyScannerTransport(transport_config)

    response_mock = SimpleNamespace(
        json=lambda: {"result": "ok"},
        raise_for_status=lambda: None,
    )
    post_mock = AsyncMock(return_value=response_mock)
    monkeypatch.setattr(transport, "client", SimpleNamespace(post=post_mock))

    payload = {"artifact_id": "abc123"}

    result = await transport.send(payload)

    post_mock.assert_awaited_once()
    assert result == {"result": "ok"}
    called_args = post_mock.await_args.kwargs
    assert called_args["headers"]["Authorization"] == "Bearer test-token"
    assert payload["artifact_id"] in called_args["content"]


@pytest.mark.asyncio
async def test_send_raises_transport_error(monkeypatch, transport_config):
    transport = AegisPolicyScannerTransport(transport_config)

    async def _raise(*_args, **_kwargs):
        raise RuntimeError("boom")

    monkeypatch.setattr(
        transport, "client", SimpleNamespace(post=AsyncMock(side_effect=_raise))
    )

    with pytest.raises(Exception) as exc:
        await transport.send({"resource": "x"})

    assert "Aegis policy scan failed" in str(exc.value)
