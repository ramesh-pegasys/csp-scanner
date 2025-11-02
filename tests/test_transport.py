"""Tests for transport layer"""

from datetime import datetime
import json
import os
import tempfile
from unittest.mock import AsyncMock, Mock, patch

import httpx
import pytest

from app.core.exceptions import TransportError
from app.transport.base import (
    BaseTransport,
    BatchTransportMixin,
    NullTransport,
    ParallelBatchTransportMixin,
    TransportFactory,
    TransportMetrics,
    TransportResult,
    TransportStatus,
)
from app.transport.filesystem import FilesystemTransport
from app.transport.http_client import HTTPTransport
from app.transport.http_transport import HTTPTransport as HTTPTransportWrapper


def test_transport_result_creation():
    """Test TransportResult creation and properties"""
    timestamp = datetime(2023, 1, 1, 12, 0, 0)

    result = TransportResult(
        status=TransportStatus.SUCCESS,
        artifact_id="test-artifact",
        timestamp=timestamp,
        response_data={"status": "accepted"},
        retry_count=1,
        duration_ms=150.5,
    )

    assert result.status == TransportStatus.SUCCESS
    assert result.artifact_id == "test-artifact"
    assert result.timestamp == timestamp
    assert result.response_data == {"status": "accepted"}
    assert result.retry_count == 1
    assert result.duration_ms == 150.5
    assert result.is_success is True
    assert result.should_retry is False


def test_transport_result_to_dict():
    """Test TransportResult to_dict method"""
    timestamp = datetime(2023, 1, 1, 12, 0, 0)

    result = TransportResult(
        status=TransportStatus.FAILED,
        artifact_id="test-artifact",
        timestamp=timestamp,
        error_message="Connection failed",
        retry_count=2,
    )

    data = result.to_dict()
    assert data["status"] == "failed"
    assert data["artifact_id"] == "test-artifact"
    assert data["error_message"] == "Connection failed"
    assert data["retry_count"] == 2


def test_transport_result_should_retry():
    """Test TransportResult should_retry property"""
    result_success = TransportResult(
        status=TransportStatus.SUCCESS, artifact_id="test", timestamp=datetime.now()
    )
    assert result_success.should_retry is False

    result_failed = TransportResult(
        status=TransportStatus.FAILED, artifact_id="test", timestamp=datetime.now()
    )
    assert result_failed.should_retry is True

    result_timeout = TransportResult(
        status=TransportStatus.TIMEOUT, artifact_id="test", timestamp=datetime.now()
    )
    assert result_timeout.should_retry is True


def test_transport_metrics():
    """Test TransportMetrics functionality"""
    metrics = TransportMetrics()

    assert metrics.total_sent == 0
    assert metrics.success_rate == 0.0

    # Update metrics
    metrics.total_sent = 10
    metrics.total_success = 8
    metrics.total_failed = 2
    metrics.total_retries = 3

    assert metrics.success_rate == 80.0

    data = metrics.to_dict()
    assert data["total_sent"] == 10
    assert data["total_success"] == 8
    assert data["success_rate"] == 80.0


def test_base_transport_initialization():
    """Test BaseTransport initialization"""
    config = {"endpoint": "test-endpoint", "max_connection_errors": 10}

    # Create a concrete implementation for testing
    class TestTransport(BaseTransport):
        async def connect(self):
            return True

        async def disconnect(self):
            pass

        async def send(self, artifact):
            return TransportResult(
                status=TransportStatus.SUCCESS,
                artifact_id=artifact.get("resource_id", "test"),
                timestamp=datetime.now(),
            )

        async def send_batch(self, artifacts):
            return [
                TransportResult(
                    status=TransportStatus.SUCCESS,
                    artifact_id=artifact.get("resource_id", f"test-{i}"),
                    timestamp=datetime.now(),
                )
                for i, artifact in enumerate(artifacts)
            ]

        async def health_check(self):
            return True

    transport = TestTransport(config)

    assert transport.config == config
    assert isinstance(transport.metrics, TransportMetrics)
    assert transport._max_connection_errors == 10
    assert transport._connection_errors == 0
    assert transport._is_connected is False
    assert transport.supports_batch is True
    assert isinstance(transport.get_metrics(), TransportMetrics)
    transport.metrics.total_sent = 5
    transport.reset_metrics()
    assert transport.metrics.total_sent == 0
    repr_text = repr(transport)
    assert "TestTransport" in repr_text


@pytest.mark.asyncio
async def test_base_transport_abstract_methods():
    """Test that BaseTransport abstract methods must be implemented"""
    config = {"endpoint": "test"}

    class IncompleteTransport(BaseTransport):
        pass  # Doesn't implement abstract methods

    # Should raise TypeError when trying to instantiate abstract class
    with pytest.raises(TypeError, match="Can't instantiate abstract class"):
        IncompleteTransport(config)  # type: ignore


@pytest.fixture
def transport_config():
    """Transport configuration fixture"""
    return {
        "http_endpoint_url": "https://scanner.example.com/api/artifacts",
        "timeout_seconds": 30,
        "max_retries": 3,
        "headers": {"User-Agent": "CSP-Scanner/1.0"},
        "api_key": "test-api-key",
    }


def test_http_transport_initialization(transport_config):
    """Test HTTP transport initialization"""
    transport = HTTPTransport(transport_config)

    assert transport.endpoint_url == "https://scanner.example.com/api/artifacts"
    assert transport.timeout == 30
    assert transport.max_retries == 3
    assert "Authorization" in transport.headers
    assert transport.headers["Authorization"] == "Bearer test-api-key"
    assert transport.client is not None


@pytest.mark.asyncio
async def test_http_transport_send_success(transport_config):
    """Test successful artifact sending"""
    transport = HTTPTransport(transport_config)

    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"status": "accepted"}
    mock_response.raise_for_status.return_value = None

    with patch.object(transport.client, "post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = mock_response

        artifact = {
            "resource_id": "test-bucket",
            "resource_type": "bucket",
            "service": "s3",
            "configuration": {"name": "test-bucket"},
        }

        result = await transport.send(artifact)

        assert result == {"status": "accepted"}
    mock_post.assert_called_once_with(
        "https://scanner.example.com/api/artifacts", json=artifact
    )


@pytest.mark.asyncio
async def test_http_transport_wrapper_send_success(transport_config):
    wrapper = HTTPTransportWrapper(transport_config)
    wrapper.client = Mock()
    wrapper.client.send = AsyncMock(return_value={"ok": True})

    result = await wrapper.send({"resource_id": "123"})
    assert result.status == TransportStatus.SUCCESS


@pytest.mark.asyncio
async def test_http_transport_wrapper_send_transport_error(transport_config):
    wrapper = HTTPTransportWrapper(transport_config)
    wrapper.client = Mock()
    wrapper.client.send = AsyncMock(side_effect=TransportError("bad request"))

    result = await wrapper.send({"resource_id": "123"})
    assert result.status == TransportStatus.FAILED
    assert "bad request" in (result.error_message or "")


@pytest.mark.asyncio
async def test_http_transport_wrapper_send_unexpected_error(transport_config):
    wrapper = HTTPTransportWrapper(transport_config)
    wrapper.client = Mock()
    wrapper.client.send = AsyncMock(side_effect=RuntimeError("boom"))

    result = await wrapper.send({"resource_id": "123"})
    assert result.status == TransportStatus.FAILED
    assert "Unexpected error" in (result.error_message or "")


@pytest.mark.asyncio
async def test_http_transport_wrapper_health_check(transport_config):
    wrapper = HTTPTransportWrapper(transport_config)
    await wrapper.connect()
    assert await wrapper.health_check() is True

    wrapper._is_connected = False
    assert await wrapper.health_check() is False

    del wrapper._is_connected
    assert await wrapper.health_check() is False


@pytest.mark.asyncio
async def test_http_transport_wrapper_close(monkeypatch, transport_config):
    wrapper = HTTPTransportWrapper(transport_config)
    await wrapper.connect()
    wrapper.client = Mock()
    wrapper.client.close = AsyncMock()

    await wrapper.close()
    wrapper.client.close.assert_called_once()
    assert wrapper.is_connected is False


@pytest.mark.asyncio
async def test_http_transport_wrapper_send_batch(transport_config):
    wrapper = HTTPTransportWrapper(transport_config)
    wrapper.client = Mock()
    wrapper.client.send = AsyncMock(return_value={"ok": True})

    artifacts = [{"resource_id": "1"}, {"resource_id": "2"}]
    results = await wrapper.send_batch(artifacts)
    assert len(results) == 2
    assert all(res.status == TransportStatus.SUCCESS for res in results)


@pytest.mark.asyncio
async def test_http_transport_send_http_error(transport_config):
    """Test HTTP error handling"""
    transport = HTTPTransport(transport_config)

    mock_response = Mock()
    mock_response.status_code = 400
    mock_response.text = "Bad Request"

    with patch.object(transport.client, "post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = mock_response
        mock_post.return_value.raise_for_status.side_effect = httpx.HTTPStatusError(
            "400 Bad Request", request=Mock(), response=mock_response
        )

        artifact = {"resource_id": "test-bucket", "service": "s3", "configuration": {}}

        with pytest.raises(TransportError) as exc_info:
            await transport.send(artifact)

        assert "HTTP 400: Bad Request" in str(exc_info.value)


@pytest.mark.asyncio
async def test_http_transport_send_timeout(transport_config):
    """Test timeout handling"""
    transport = HTTPTransport(transport_config)

    with patch.object(transport.client, "post", new_callable=AsyncMock) as mock_post:
        mock_post.side_effect = httpx.TimeoutException("Request timeout")

        artifact = {"resource_id": "test-bucket", "service": "s3", "configuration": {}}

        with pytest.raises(httpx.TimeoutException):
            await transport.send(artifact)


@pytest.mark.asyncio
async def test_http_transport_send_network_error(transport_config):
    transport = HTTPTransport(transport_config)

    with patch.object(transport.client, "post", new_callable=AsyncMock) as mock_post:
        mock_post.side_effect = httpx.NetworkError("network down")

        with pytest.raises(httpx.NetworkError):
            await transport.send({"resource_id": "x"})


@pytest.mark.asyncio
async def test_http_transport_send_unexpected_error(transport_config):
    transport = HTTPTransport(transport_config)

    with patch.object(transport.client, "post", new_callable=AsyncMock) as mock_post:
        mock_post.side_effect = RuntimeError("boom")

        with pytest.raises(TransportError) as exc_info:
            await transport.send({"resource_id": "x"})

        assert "Unexpected error" in str(exc_info.value)


@pytest.mark.asyncio
async def test_http_transport_close(transport_config):
    """Test client closing"""
    transport = HTTPTransport(transport_config)

    with patch.object(transport.client, "aclose", new_callable=AsyncMock) as mock_close:
        await transport.close()
        mock_close.assert_called_once()


# Filesystem Transport Tests


@pytest.fixture
def temp_dir():
    """Create a temporary directory for filesystem transport tests"""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir


@pytest.fixture
def filesystem_config(temp_dir):
    """Filesystem transport configuration"""
    return {"base_dir": temp_dir, "create_dir": True}


@pytest.mark.asyncio
async def test_filesystem_transport_init(filesystem_config):
    """Test FilesystemTransport initialization"""
    transport = FilesystemTransport(filesystem_config)

    assert transport.base_dir == filesystem_config["base_dir"]
    assert transport.create_dir == filesystem_config["create_dir"]
    assert os.path.exists(transport.base_dir)


def test_filesystem_transport_relative_base_dir(tmp_path):
    rel_config = {"base_dir": "relative_dir", "create_dir": True}
    transport = FilesystemTransport(rel_config)
    assert transport.base_dir.startswith(os.getcwd())
    assert transport.get_base_dir() == transport.base_dir


@pytest.mark.asyncio
async def test_filesystem_transport_connect(filesystem_config):
    """Test FilesystemTransport connection"""
    transport = FilesystemTransport(filesystem_config)

    result = await transport.connect()
    assert result is True
    assert transport.is_connected is True


@pytest.mark.asyncio
async def test_filesystem_transport_connect_failure(filesystem_config, monkeypatch):
    transport = FilesystemTransport(filesystem_config)

    def failing_ensure():
        raise RuntimeError("fail")

    monkeypatch.setattr(transport, "_ensure_base_dir", failing_ensure)

    result = await transport.connect()
    assert result is False
    assert transport.is_connected is False


def test_filesystem_transport_ensure_base_dir_failure(monkeypatch, tmp_path):
    config = {"base_dir": tmp_path / "nope", "create_dir": True}
    transport = FilesystemTransport.__new__(FilesystemTransport)
    BaseTransport.__init__(transport, config)  # type: ignore[misc]
    transport.base_dir = str(config["base_dir"])
    transport.create_dir = True

    def raise_os_error(*args, **kwargs):
        raise OSError("boom")

    monkeypatch.setattr("os.path.exists", lambda path: False)
    monkeypatch.setattr("os.makedirs", raise_os_error)

    with pytest.raises(TransportError):
        transport._ensure_base_dir()


@pytest.mark.asyncio
async def test_filesystem_transport_send(filesystem_config):
    """Test sending artifact to filesystem"""
    transport = FilesystemTransport(filesystem_config)

    artifact = {
        "service": "ec2",
        "resource_type": "instance",
        "resource_id": "i-1234567890abcdef0",
        "region": "us-east-1",
        "data": {"instance_type": "t2.micro", "state": "running"},
    }

    result = await transport.send(artifact)

    assert result.status == TransportStatus.SUCCESS
    assert result.artifact_id == artifact["resource_id"]
    assert result.response_data is not None
    assert "file_path" in result.response_data
    assert "filename" in result.response_data

    # Verify file was created
    file_path = result.response_data["file_path"]
    assert os.path.exists(file_path)

    # Verify file contents
    with open(file_path, "r") as f:
        saved_data = json.load(f)
        assert saved_data == artifact


@pytest.mark.asyncio
async def test_filesystem_transport_send_failure(filesystem_config, monkeypatch):
    transport = FilesystemTransport(filesystem_config)

    artifact = {
        "service": "ec2",
        "resource_type": "instance",
        "resource_id": "i-123",
    }

    def raise_io_error(*args, **kwargs):
        raise OSError("disk full")

    monkeypatch.setattr("builtins.open", raise_io_error)

    result = await transport.send(artifact)
    assert result.status == TransportStatus.FAILED
    assert "disk full" in (result.error_message or "")


@pytest.mark.asyncio
async def test_filesystem_transport_send_batch(filesystem_config):
    """Test sending batch of artifacts to filesystem"""
    transport = FilesystemTransport(filesystem_config)

    artifacts = [
        {
            "service": "s3",
            "resource_type": "bucket",
            "resource_id": "my-bucket-1",
            "region": "us-east-1",
            "data": {"creation_date": "2023-01-01"},
        },
        {
            "service": "s3",
            "resource_type": "bucket",
            "resource_id": "my-bucket-2",
            "region": "us-west-2",
            "data": {"creation_date": "2023-01-02"},
        },
    ]

    results = await transport.send_batch(artifacts)

    assert len(results) == 2
    for result in results:
        assert result.status == TransportStatus.SUCCESS
        assert result.response_data is not None
        assert "file_path" in result.response_data


@pytest.mark.asyncio
async def test_filesystem_transport_health_check(filesystem_config):
    """Test filesystem transport health check"""
    transport = FilesystemTransport(filesystem_config)

    is_healthy = await transport.health_check()
    assert is_healthy is True


@pytest.mark.asyncio
async def test_filesystem_transport_health_check_failure(
    filesystem_config, monkeypatch
):
    transport = FilesystemTransport(filesystem_config)

    def raise_io_error(*args, **kwargs):
        raise OSError("cannot write")

    monkeypatch.setattr("builtins.open", raise_io_error)

    is_healthy = await transport.health_check()
    assert is_healthy is False


@pytest.mark.asyncio
async def test_filesystem_transport_unique_filenames(filesystem_config):
    """Test that filenames are unique for same artifact"""
    transport = FilesystemTransport(filesystem_config)

    artifact = {
        "service": "ec2",
        "resource_type": "instance",
        "resource_id": "i-1234567890abcdef0",
        "region": "us-east-1",
        "data": {"instance_type": "t2.micro"},
    }

    # Send same artifact twice
    result1 = await transport.send(artifact)
    result2 = await transport.send(artifact)

    # Filenames should be different
    assert result1.response_data is not None
    assert result2.response_data is not None
    assert result1.response_data["filename"] != result2.response_data["filename"]

    # Both files should exist
    assert os.path.exists(result1.response_data["file_path"])
    assert os.path.exists(result2.response_data["file_path"])


@pytest.mark.asyncio
async def test_filesystem_transport_filename_format(filesystem_config):
    """Test filename format"""
    transport = FilesystemTransport(filesystem_config)

    artifact = {
        "service": "ec2",
        "resource_type": "instance",
        "resource_id": "i-1234567890abcdef0",
        "region": "us-east-1",
    }

    result = await transport.send(artifact)
    assert result.response_data is not None
    filename = result.response_data["filename"]

    # Filename should start with service_resource_type_resource_id
    assert filename.startswith("ec2_instance_i-1234567890abcdef0_")
    assert filename.endswith(".json")


def test_filesystem_transport_list_files_failure(filesystem_config, monkeypatch):
    transport = FilesystemTransport(filesystem_config)

    def raise_os_error(path):
        raise OSError("cannot list")

    monkeypatch.setattr("os.listdir", raise_os_error)

    files = transport.list_files()
    assert files == []


@pytest.mark.asyncio
async def test_null_transport_metrics_and_send_batch():
    transport = NullTransport({})

    await transport.connect()
    assert transport.is_connected is True

    result = await transport.send({"resource_id": "abc"})
    assert result.is_success

    batch_results = await transport.send_batch(
        [{"resource_id": "one"}, {"resource_id": "two"}]
    )
    assert len(batch_results) == 2
    assert transport.metrics.total_sent >= 3

    await transport.disconnect()
    assert transport.is_connected is False
    assert await transport.health_check() is True


@pytest.mark.asyncio
async def test_transport_connection_error_handling():
    class ErrorTransport(NullTransport):
        pass

    transport = ErrorTransport({"max_connection_errors": 2})
    await transport.connect()

    await transport._handle_connection_error(RuntimeError("boom"))
    assert transport._connection_errors == 1
    assert transport.is_connected is True

    await transport._handle_connection_error(RuntimeError("boom again"))
    assert transport._connection_errors == 2
    assert transport.is_connected is False

    await transport._reset_connection_errors()
    assert transport._connection_errors == 0


@pytest.mark.asyncio
async def test_transport_metrics_failure_update():
    transport = NullTransport({})
    result = TransportResult(
        status=TransportStatus.FAILED,
        artifact_id="bad",
        timestamp=datetime.now(),
        error_message="boom",
        retry_count=2,
    )
    await transport._update_metrics_failure(result)
    assert transport.metrics.total_failed == 1
    assert transport.metrics.last_error == "boom"
    assert transport.metrics.total_retries == 2


@pytest.mark.asyncio
async def test_batch_transport_mixin_sequences():
    class SequentialTransport(BatchTransportMixin, BaseTransport):
        async def connect(self):
            return True

        async def disconnect(self):
            return None

        async def send(self, artifact):
            return TransportResult(
                status=TransportStatus.SUCCESS,
                artifact_id=artifact["resource_id"],
                timestamp=datetime.now(),
            )

        async def send_batch(self, artifacts):  # type: ignore[override]
            return await super().send_batch(artifacts)

        async def health_check(self):
            return True

    transport = SequentialTransport({})
    artifacts = [{"resource_id": "a"}, {"resource_id": "b"}]
    results = await transport.send_batch(artifacts)
    assert [res.artifact_id for res in results] == ["a", "b"]


@pytest.mark.asyncio
async def test_batch_transport_mixin_error():
    class ErrorTransport(BatchTransportMixin, BaseTransport):
        async def connect(self):
            return True

        async def disconnect(self):
            return None

        async def send(self, artifact):
            raise RuntimeError("fail")

        async def send_batch(self, artifacts):  # type: ignore[override]
            return await super().send_batch(artifacts)

        async def health_check(self):
            return True

    transport = ErrorTransport({})
    results = await transport.send_batch([{"resource_id": "x"}])
    assert results[0].status == TransportStatus.FAILED


@pytest.mark.asyncio
async def test_parallel_batch_transport_mixin(monkeypatch):
    order = []

    class ParallelTransport(ParallelBatchTransportMixin, BaseTransport):
        async def connect(self):
            return True

        async def disconnect(self):
            return None

        async def send(self, artifact):
            order.append(artifact["resource_id"])
            return TransportResult(
                status=TransportStatus.SUCCESS,
                artifact_id=artifact["resource_id"],
                timestamp=datetime.now(),
            )

        async def send_batch(self, artifacts, max_concurrent=2):  # type: ignore[override]
            return await super().send_batch(artifacts, max_concurrent=max_concurrent)

        async def health_check(self):
            return True

    transport = ParallelTransport({})
    artifacts = [{"resource_id": str(i)} for i in range(4)]
    results = await transport.send_batch(artifacts, max_concurrent=2)

    assert len(results) == 4
    assert sorted(order) == ["0", "1", "2", "3"]


@pytest.mark.asyncio
async def test_parallel_batch_transport_mixin_errors():
    class ErrorParallelTransport(ParallelBatchTransportMixin, BaseTransport):
        async def connect(self):
            return True

        async def disconnect(self):
            return None

        async def send(self, artifact):
            if artifact["resource_id"] == "bad":
                raise RuntimeError("boom")
            if artifact["resource_id"] == "weird":
                return RuntimeError("odd")
            return TransportResult(
                status=TransportStatus.SUCCESS,
                artifact_id=artifact["resource_id"],
                timestamp=datetime.now(),
            )

        async def send_batch(self, artifacts, max_concurrent=2):  # type: ignore[override]
            return await super().send_batch(artifacts, max_concurrent=max_concurrent)

        async def health_check(self):
            return True

    transport = ErrorParallelTransport({})
    artifacts = [
        {"resource_id": "good"},
        {"resource_id": "bad"},
        {"resource_id": "weird"},
    ]
    results = await transport.send_batch(artifacts, max_concurrent=1)
    statuses = [res.status for res in results]
    assert TransportStatus.FAILED in statuses


def test_transport_factory_register_and_create():
    class DummyTransport(BaseTransport):
        async def connect(self):
            return True

        async def disconnect(self):
            return None

        async def send(self, artifact):
            return TransportResult(
                status=TransportStatus.SUCCESS,
                artifact_id=artifact.get("resource_id", "x"),
                timestamp=datetime.now(),
            )

        async def send_batch(self, artifacts):
            return []

        async def health_check(self):
            return True

    TransportFactory.register("dummy", DummyTransport)
    instance = TransportFactory.create("dummy", {})

    assert isinstance(instance, DummyTransport)
    assert "dummy" in TransportFactory.list_transports()


def test_transport_factory_register_validation():
    class NotTransport:
        pass

    with pytest.raises(ValueError):
        TransportFactory.register("bad", NotTransport)  # type: ignore[arg-type]


def test_transport_factory_create_unknown():
    with pytest.raises(ValueError):
        TransportFactory.create("unknown-type", {})
