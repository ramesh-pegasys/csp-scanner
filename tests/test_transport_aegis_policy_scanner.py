import os
import pytest
import httpx
from unittest.mock import AsyncMock, patch
from app.transport.aegis_policy_scanner_transport import (
    AegisPolicyScannerTransport,
    TransportError,
)


@pytest.mark.asyncio
def test_aegis_policy_scanner_transport_basic(monkeypatch):
    # Set up environment variable for token
    monkeypatch.setenv("AEGIS_TOKEN", "dummy-token")
    config = {
        "type": "aegis_policy_scanner",
        "aegis_host": "aegis.example.com",
        "policy_name": "test-policy",
        "max_concurrent_requests": 1,
        "max_retries": 1,
        "labels": {"env": "test"},
        "aws_accounts": [],
        "gcp_projects": [],
        "azure_subscriptions": [],
    }
    transport = AegisPolicyScannerTransport(config)
    # Check basic attributes
    assert transport.aegis_host == "aegis.example.com"
    assert transport.policy_name == "test-policy"
    assert transport.aegis_token == "dummy-token"
    assert transport.endpoint_url.endswith("/api/eval/policies/test-policy")
    assert transport.headers["Authorization"] == "Bearer dummy-token"
    # Check label generation
    labels = transport._generate_cloud_labels(config, config["labels"])
    assert "env" in labels
    # Close client
    import asyncio

    asyncio.run(transport.close())


@pytest.mark.asyncio
def test_aegis_policy_scanner_transport_token_missing(monkeypatch):
    monkeypatch.delenv("AEGIS_TOKEN", raising=False)
    config = {
        "type": "aegis_policy_scanner",
        "aegis_host": "host",
        "policy_name": "policy",
    }
    with pytest.raises(ValueError):
        AegisPolicyScannerTransport(config)


@pytest.mark.asyncio
def test_aegis_policy_scanner_transport_build_yaml():
    config = {
        "type": "aegis_policy_scanner",
        "aegis_host": "host",
        "policy_name": "policy",
        "labels": {"env": "test"},
    }
    os.environ["AEGIS_TOKEN"] = "dummy-token"
    transport = AegisPolicyScannerTransport(config)
    labels = {"env": "test"}
    input_data = {"foo": "bar"}
    yaml_str = transport._build_yaml(labels, input_data)
    assert "labels:" in yaml_str
    assert "inputData:" in yaml_str
    assert "foo: bar" in yaml_str


@pytest.mark.asyncio
def test_aegis_policy_scanner_transport_close(monkeypatch):
    monkeypatch.setenv("AEGIS_TOKEN", "dummy-token")
    config = {
        "type": "aegis_policy_scanner",
        "aegis_host": "host",
        "policy_name": "policy",
    }
    transport = AegisPolicyScannerTransport(config)
    import asyncio

    asyncio.run(transport.close())


@pytest.mark.asyncio
def test_aegis_policy_scanner_transport_send(monkeypatch):
    monkeypatch.setenv("AEGIS_TOKEN", "dummy-token")
    config = {
        "type": "aegis_policy_scanner",
        "aegis_host": "host",
        "policy_name": "policy",
    }
    transport = AegisPolicyScannerTransport(config)

    # Patch httpx.AsyncClient.post to simulate response
    class DummyResponse:
        def raise_for_status(self):
            pass

        def json(self):
            return {"result": "ok"}

    with patch.object(
        transport.client, "post", new=AsyncMock(return_value=DummyResponse())
    ):
        import asyncio

        result = asyncio.run(transport.send({"foo": "bar"}))
        assert result["result"] == "ok"
        asyncio.run(transport.close())


@pytest.mark.asyncio
def test_aegis_policy_scanner_transport_send_error(monkeypatch):
    monkeypatch.setenv("AEGIS_TOKEN", "dummy-token")
    config = {
        "type": "aegis_policy_scanner",
        "aegis_host": "host",
        "policy_name": "policy",
    }
    transport = AegisPolicyScannerTransport(config)
    # Create valid request/response objects
    req = httpx.Request("POST", "https://host/api/eval/policies/policy")
    resp = httpx.Response(500, request=req)

    async def dummy_post(*args, **kwargs):
        raise httpx.HTTPStatusError("fail", request=req, response=resp)

    with patch.object(transport.client, "post", new=AsyncMock(side_effect=dummy_post)):
        import asyncio

        with pytest.raises(TransportError):
            asyncio.run(transport.send({"foo": "bar"}))
        asyncio.run(transport.close())


@pytest.mark.asyncio
def test_aegis_policy_scanner_transport_send_with_labels(monkeypatch):
    monkeypatch.setenv("AEGIS_TOKEN", "dummy-token")
    config = {
        "type": "aegis_policy_scanner",
        "aegis_host": "host",
        "policy_name": "policy",
        "labels": {"env": "test"},
    }
    transport = AegisPolicyScannerTransport(config)

    class DummyResponse:
        def raise_for_status(self):
            pass

        def json(self):
            return {"result": "ok"}

    with patch.object(
        transport.client, "post", new=AsyncMock(return_value=DummyResponse())
    ):
        import asyncio

        custom_labels = {"custom": "label"}
        result = asyncio.run(transport.send({"foo": "bar"}, labels=custom_labels))
        assert result["result"] == "ok"
        asyncio.run(transport.close())


@pytest.mark.asyncio
def test_aegis_policy_scanner_transport_send_network_error(monkeypatch):
    monkeypatch.setenv("AEGIS_TOKEN", "dummy-token")
    config = {
        "type": "aegis_policy_scanner",
        "aegis_host": "host",
        "policy_name": "policy",
    }
    transport = AegisPolicyScannerTransport(config)

    async def dummy_post(*args, **kwargs):
        raise httpx.NetworkError("network fail")

    with patch.object(transport.client, "post", new=AsyncMock(side_effect=dummy_post)):
        import asyncio

        with pytest.raises(TransportError):
            asyncio.run(transport.send({"foo": "bar"}))
        asyncio.run(transport.close())


@pytest.mark.asyncio
def test_aegis_policy_scanner_transport_send_with_semaphore(monkeypatch):
    monkeypatch.setenv("AEGIS_TOKEN", "dummy-token")
    config = {
        "type": "aegis_policy_scanner",
        "aegis_host": "host",
        "policy_name": "policy",
        "max_concurrent_requests": 1,
    }
    transport = AegisPolicyScannerTransport(config)

    class DummyResponse:
        def raise_for_status(self):
            pass

        def json(self):
            return {"result": "ok"}

    with patch.object(
        transport.client, "post", new=AsyncMock(return_value=DummyResponse())
    ):
        import asyncio

        result = asyncio.run(transport.send({"foo": "bar"}))
        assert result["result"] == "ok"
        asyncio.run(transport.close())


@pytest.mark.asyncio
def test_aegis_policy_scanner_transport_close_no_client(monkeypatch):
    monkeypatch.setenv("AEGIS_TOKEN", "dummy-token")
    config = {
        "type": "aegis_policy_scanner",
        "aegis_host": "host",
        "policy_name": "policy",
    }
    transport = AegisPolicyScannerTransport(config)
    transport.client = None
    import asyncio

    # Should not raise
    try:
        asyncio.run(transport.close())
    except Exception:
        pytest.fail("close() raised unexpectedly when client is None")
