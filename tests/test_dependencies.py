"""Tests for API dependencies."""

from types import SimpleNamespace
import pytest
from fastapi import HTTPException
from typing import cast
from starlette.requests import Request

from app.api import dependencies
from app.core.config import Settings
from app.services.orchestrator import ExtractionOrchestrator
from app.services.registry import ExtractorRegistry


def make_request(state_attrs=None, headers=None, client=None, method="GET", path="/"):
    """Helper to create a request-like object."""
    state = SimpleNamespace(**(state_attrs or {}))
    app = SimpleNamespace(state=state)
    request = SimpleNamespace(
        app=app,
        headers=headers or {},
        client=client,
        method=method,
        url=SimpleNamespace(path=path),
    )
    return request


def test_get_config_returns_settings(monkeypatch):
    settings = Settings()
    monkeypatch.setattr(dependencies, "get_settings", lambda: settings)

    assert dependencies.get_config() is settings


def test_get_orchestrator_success():
    orchestrator = object()
    request = make_request({"orchestrator": orchestrator})

    assert dependencies.get_orchestrator(cast(Request, request)) is orchestrator

    assert dependencies.get_orchestrator(cast(Request, request)) is orchestrator


def test_get_orchestrator_missing():
    request = make_request()

    with pytest.raises(HTTPException) as exc:
        dependencies.get_orchestrator(cast(Request, request))

    assert exc.value.status_code == 503


def test_get_registry_and_scheduler_missing():
    request = make_request()

    with pytest.raises(HTTPException):
        dependencies.get_registry(cast(Request, request))

    with pytest.raises(HTTPException):
        dependencies.get_scheduler(cast(Request, request))


def test_get_registry_and_scheduler_success():
    registry = object()
    scheduler = object()
    request = make_request({"registry": registry, "scheduler": scheduler})

    assert dependencies.get_registry(cast(Request, request)) is registry
    assert dependencies.get_scheduler(cast(Request, request)) is scheduler


@pytest.mark.asyncio
async def test_verify_api_key_disabled_returns_true():
    settings = Settings(api_key_enabled=False)
    assert await dependencies.verify_api_key(settings=settings) is True


@pytest.mark.asyncio
async def test_verify_api_key_success(monkeypatch):
    settings = Settings(api_key_enabled=True, api_key="secret")
    monkeypatch.setattr(dependencies.logger, "warning", lambda *args, **kwargs: None)
    assert (
        await dependencies.verify_api_key(x_api_key="secret", settings=settings) is True
    )


@pytest.mark.asyncio
async def test_verify_api_key_missing_and_invalid(monkeypatch):
    settings = Settings(api_key_enabled=True, api_key="secret")
    warnings = []
    monkeypatch.setattr(dependencies.logger, "warning", warnings.append)

    with pytest.raises(HTTPException) as exc_missing:
        await dependencies.verify_api_key(x_api_key=None, settings=settings)
    assert exc_missing.value.status_code == 401

    with pytest.raises(HTTPException) as exc_invalid:
        await dependencies.verify_api_key(x_api_key="bad", settings=settings)
    assert exc_invalid.value.status_code == 401

    assert len(warnings) == 2


@pytest.mark.asyncio
async def test_optional_verify_api_key_behaviour():
    settings = Settings(api_key_enabled=True, api_key="secret")
    assert (
        await dependencies.optional_verify_api_key(x_api_key=None, settings=settings)
        is False
    )
    assert (
        await dependencies.optional_verify_api_key(x_api_key="bad", settings=settings)
        is False
    )
    assert (
        await dependencies.optional_verify_api_key(
            x_api_key="secret", settings=settings
        )
        is True
    )


@pytest.mark.asyncio
async def test_optional_verify_api_key_disabled():
    settings = Settings(api_key_enabled=False)
    assert (
        await dependencies.optional_verify_api_key(
            x_api_key="anything", settings=settings
        )
        is False
    )


@pytest.mark.asyncio
async def test_check_rate_limit(monkeypatch):
    limiter = dependencies.RateLimiter()
    limiter._max_requests = 1  # type: ignore[attr-defined]

    monkeypatch.setattr(dependencies, "rate_limiter", limiter)
    request = make_request(client=SimpleNamespace(host="tester"))
    settings = Settings(rate_limiting_enabled=True)

    assert (
        await dependencies.check_rate_limit(cast(Request, request), settings=settings)
        is True
    )

    with pytest.raises(HTTPException) as exc:
        await dependencies.check_rate_limit(cast(Request, request), settings=settings)
    assert exc.value.status_code == 429

    disabled_settings = Settings(rate_limiting_enabled=False)
    assert (
        await dependencies.check_rate_limit(
            cast(Request, request), settings=disabled_settings
        )
        is True
    )


def test_pagination_params_success():
    params = dependencies.get_pagination_params(page=2, page_size=10)
    assert params.page == 2
    assert params.page_size == 10
    assert params.skip == 10
    assert params.limit == 10


def test_pagination_params_validation_errors():
    with pytest.raises(HTTPException):
        dependencies.PaginationParams(page=0)
    with pytest.raises(HTTPException):
        dependencies.PaginationParams(page=1, page_size=0)
    with pytest.raises(HTTPException):
        dependencies.PaginationParams(page=1, page_size=1001)


@pytest.mark.asyncio
async def test_check_service_health(monkeypatch):
    orchestrator = cast(ExtractionOrchestrator, object())
    registry = cast(ExtractorRegistry, SimpleNamespace(list_services=lambda: ["ec2"]))

    assert await dependencies.check_service_health(orchestrator, registry) is True

    registry_empty = cast(ExtractorRegistry, SimpleNamespace(list_services=lambda: []))
    with pytest.raises(HTTPException):
        await dependencies.check_service_health(orchestrator, registry_empty)


def test_request_validator_services_and_regions():
    registry = cast(
        ExtractorRegistry, SimpleNamespace(list_services=lambda: ["ec2", "s3"])
    )
    validator = dependencies.RequestValidator()

    assert validator.validate_services(["ec2"], registry) == ["ec2"]
    assert validator.validate_services(None, registry) is None

    with pytest.raises(HTTPException):
        validator.validate_services(["bad"], registry)

    assert validator.validate_regions(["us-east-1"]) == ["us-east-1"]
    assert validator.validate_regions(None) is None
    with pytest.raises(HTTPException):
        validator.validate_regions(["not-a-region"])


def test_request_validator_batch_size():
    validator = dependencies.RequestValidator()
    assert validator.validate_batch_size(10) == 10

    with pytest.raises(HTTPException):
        validator.validate_batch_size(0)
    with pytest.raises(HTTPException):
        validator.validate_batch_size(1001)


@pytest.mark.asyncio
async def test_validate_extraction_request(monkeypatch):
    registry = cast(ExtractorRegistry, SimpleNamespace(list_services=lambda: ["ec2"]))
    validated = await dependencies.validate_extraction_request(
        services=["ec2"],
        regions=["us-east-1"],
        batch_size=5,
        registry=registry,
    )

    assert validated["services"] == ["ec2"]
    assert validated["regions"] == ["us-east-1"]
    assert validated["batch_size"] == 5


def test_request_context_and_tracker():
    request = make_request(
        headers={"x-request-id": "req-1", "user-agent": "pytest"},
        client=SimpleNamespace(host="127.0.0.1"),
        method="POST",
        path="/extract",
    )
    context = dependencies.get_request_context(cast(Request, request))
    context_dict = context.to_dict()

    assert context_dict["request_id"] == "req-1"
    assert context_dict["client_ip"] == "127.0.0.1"
    assert context_dict["path"] == "/extract"
    assert context_dict["method"] == "POST"

    tracker = dependencies.BackgroundTaskTracker()
    tracker.add_task("task-1", "example")
    task = tracker.get_task("task-1")
    assert task is not None
    assert task["name"] == "example"
    assert "task-1" in tracker.list_tasks()

    global_tracker = dependencies.get_background_task_tracker()
    assert global_tracker is dependencies.background_task_tracker
