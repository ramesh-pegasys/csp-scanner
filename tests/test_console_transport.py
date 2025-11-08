import pytest

from app.transport.console import ConsoleTransport


@pytest.mark.asyncio
async def test_console_transport_send_updates_metrics(capsys):
    transport = ConsoleTransport(config={})
    await transport.connect()

    artifact = {"resource_id": "res-1", "body": {"foo": "bar"}}
    result = await transport.send(artifact)

    await transport.disconnect()

    assert result.is_success
    assert transport.metrics.total_success == 1
    captured = capsys.readouterr()
    assert "Artifact Body" in captured.out
    assert "res-1" in captured.out or "foo" in captured.out


@pytest.mark.asyncio
async def test_console_transport_send_batch_handles_multiple():
    transport = ConsoleTransport(config={})
    await transport.connect()

    artifacts = [
        {"resource_id": "a1", "body": {"a": 1}},
        {"resource_id": "a2", "body": {"a": 2}},
    ]

    results = await transport.send_batch(artifacts)

    assert len(results) == 2
    assert transport.metrics.total_success == 2

    await transport.disconnect()
