# app/api/dependencies.py
"""
Shared dependencies for FastAPI routes.
Provides reusable dependency injection for common resources.
"""

from typing import Optional, Dict, Any
from fastapi import Depends, HTTPException, Header, Request, status
import logging

from app.core.config import Settings, get_settings
from app.services.orchestrator import ExtractionOrchestrator
from app.services.registry import ExtractorRegistry
from app.services.scheduler import SchedulerService

logger = logging.getLogger(__name__)


# Configuration dependency
def get_config() -> Settings:
    """Get application settings"""
    return get_settings()


# Orchestrator dependency
def get_orchestrator(request: Request) -> ExtractionOrchestrator:
    """
    Get the orchestrator instance from app state.

    Raises:
        HTTPException: If orchestrator not initialized
    """
    if not hasattr(request.app.state, "orchestrator"):
        logger.error("Orchestrator not initialized in app state")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Service not fully initialized. Please try again later.",
        )
    return request.app.state.orchestrator


# Registry dependency
def get_registry(request: Request) -> ExtractorRegistry:
    """
    Get the extractor registry from app state.

    Raises:
        HTTPException: If registry not initialized
    """
    if not hasattr(request.app.state, "registry"):
        logger.error("Registry not initialized in app state")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Service not fully initialized. Please try again later.",
        )
    return request.app.state.registry


# Scheduler dependency
def get_scheduler(request: Request) -> SchedulerService:
    """
    Get the scheduler instance from app state.

    Raises:
        HTTPException: If scheduler not initialized
    """
    if not hasattr(request.app.state, "scheduler"):
        logger.error("Scheduler not initialized in app state")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Service not fully initialized. Please try again later.",
        )
    return request.app.state.scheduler


# Authentication dependencies
async def verify_api_key(
    x_api_key: Optional[str] = Header(None), settings: Settings = Depends(get_config)
) -> bool:
    """
    Verify API key for authenticated endpoints.

    Args:
        x_api_key: API key from header
        settings: Application settings

    Returns:
        True if authenticated

    Raises:
        HTTPException: If authentication fails
    """
    # If no API key is configured, allow all requests (development mode)
    if not settings.api_key_enabled:
        return True

    expected_key = settings.api_key

    if not x_api_key:
        logger.warning("API key missing in request")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key required",
            headers={"WWW-Authenticate": "ApiKey"},
        )

    if x_api_key != expected_key:
        logger.warning(f"Invalid API key provided: {x_api_key[:8]}...")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key",
            headers={"WWW-Authenticate": "ApiKey"},
        )

    return True


# Optional authentication (doesn't fail if no key provided)
async def optional_verify_api_key(
    x_api_key: Optional[str] = Header(None), settings: Settings = Depends(get_config)
) -> bool:
    """
    Optional API key verification for endpoints that support both
    authenticated and unauthenticated access.

    Returns:
        True if authenticated, False otherwise
    """
    if not settings.api_key_enabled:
        return False

    if not x_api_key:
        return False

    return x_api_key == settings.api_key


# Rate limiting dependency
class RateLimiter:
    """
    Simple in-memory rate limiter for API endpoints.
    In production, use Redis-backed rate limiting.
    """

    def __init__(self) -> None:
        self._requests: Dict[str, list] = {}
        self._max_requests = 100
        self._time_window = 3600  # 1 hour in seconds

    def is_allowed(self, client_id: str) -> bool:
        """
        Check if request is allowed based on rate limit.

        Args:
            client_id: Unique identifier for the client

        Returns:
            True if request is allowed
        """
        import time

        current_time = time.time()

        if client_id not in self._requests:
            self._requests[client_id] = []

        # Remove old requests outside the time window
        self._requests[client_id] = [
            req_time
            for req_time in self._requests[client_id]
            if current_time - req_time < self._time_window
        ]

        # Check if limit exceeded
        if len(self._requests[client_id]) >= self._max_requests:
            return False

        # Add current request
        self._requests[client_id].append(current_time)
        return True


rate_limiter = RateLimiter()


async def check_rate_limit(
    request: Request, settings: Settings = Depends(get_config)
) -> bool:
    """
    Check rate limit for incoming requests.

    Args:
        request: FastAPI request object
        settings: Application settings

    Returns:
        True if allowed

    Raises:
        HTTPException: If rate limit exceeded
    """
    if not settings.rate_limiting_enabled:
        return True

    # Use client IP as identifier
    client_id = request.client.host if request.client else "unknown"

    if not rate_limiter.is_allowed(client_id):
        logger.warning(f"Rate limit exceeded for client: {client_id}")
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limit exceeded. Please try again later.",
            headers={"Retry-After": "3600"},
        )

    return True


# Pagination dependency
class PaginationParams:
    """Pagination parameters for list endpoints"""

    def __init__(self, page: int = 1, page_size: int = 50, max_page_size: int = 500):
        if page < 1:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Page must be >= 1",
            )

        if page_size < 1:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Page size must be >= 1",
            )

        if page_size > max_page_size:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Page size must be <= {max_page_size}",
            )

        self.page = page
        self.page_size = page_size
        self.skip = (page - 1) * page_size
        self.limit = page_size


def get_pagination_params(page: int = 1, page_size: int = 50) -> PaginationParams:
    """
    Get pagination parameters from query string.

    Args:
        page: Page number (1-indexed)
        page_size: Number of items per page

    Returns:
        PaginationParams object
    """
    return PaginationParams(page=page, page_size=page_size)


# Service availability check
async def check_service_health(
    orchestrator: ExtractionOrchestrator = Depends(get_orchestrator),
    registry: ExtractorRegistry = Depends(get_registry),
) -> bool:
    """
    Verify that critical services are available and healthy.

    Raises:
        HTTPException: If service is unhealthy
    """
    # Check if registry has extractors
    if not registry.list_services():
        logger.error("No extractors registered")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="No extractors available",
        )

    return True


# Request validation dependency
class RequestValidator:
    """Validates common request parameters"""

    @staticmethod
    def validate_services(
        services: Optional[list], registry: ExtractorRegistry
    ) -> Optional[list]:
        """
        Validate that requested services exist.

        Args:
            services: List of service names
            registry: Extractor registry

        Returns:
            Validated service list or None

        Raises:
            HTTPException: If invalid services requested
        """
        if services is None:
            return None

        available_services = set(registry.list_services())
        invalid_services = set(services) - available_services

        if invalid_services:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Invalid services: {', '.join(invalid_services)}. "
                f"Available: {', '.join(available_services)}",
            )

        return services

    @staticmethod
    def validate_regions(regions: Optional[list]) -> Optional[list]:
        """
        Validate AWS region names.

        Args:
            regions: List of region names

        Returns:
            Validated region list or None

        Raises:
            HTTPException: If invalid regions
        """
        if regions is None:
            return None

        # Basic AWS region format validation
        import re

        region_pattern = re.compile(r"^[a-z]{2}-[a-z]+-\d{1}$")

        invalid_regions = [
            region for region in regions if not region_pattern.match(region)
        ]

        if invalid_regions:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Invalid region format: {', '.join(invalid_regions)}",
            )

        return regions

    @staticmethod
    def validate_batch_size(batch_size: int) -> int:
        """
        Validate batch size parameter.

        Args:
            batch_size: Requested batch size

        Returns:
            Validated batch size

        Raises:
            HTTPException: If batch size invalid
        """
        if batch_size < 1:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Batch size must be >= 1",
            )

        if batch_size > 1000:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Batch size must be <= 1000",
            )

        return batch_size


request_validator = RequestValidator()


# Dependency for validated extraction request
async def validate_extraction_request(
    services: Optional[list],
    regions: Optional[list],
    batch_size: int,
    registry: ExtractorRegistry = Depends(get_registry),
) -> Dict[str, Any]:
    """
    Validate all parameters for an extraction request.

    Returns:
        Dictionary of validated parameters
    """
    return {
        "services": request_validator.validate_services(services, registry),
        "regions": request_validator.validate_regions(regions),
        "batch_size": request_validator.validate_batch_size(batch_size),
    }


# Logging context dependency
class RequestContext:
    """Request context for enhanced logging"""

    def __init__(self, request: Request):
        self.request_id = request.headers.get("x-request-id", "unknown")
        self.client_ip = request.client.host if request.client else "unknown"
        self.user_agent = request.headers.get("user-agent", "unknown")
        self.path = request.url.path
        self.method = request.method

    def to_dict(self) -> Dict[str, str]:
        """Convert context to dictionary for logging"""
        return {
            "request_id": self.request_id,
            "client_ip": self.client_ip,
            "user_agent": self.user_agent,
            "path": self.path,
            "method": self.method,
        }


def get_request_context(request: Request) -> RequestContext:
    """
    Get request context for logging.

    Args:
        request: FastAPI request object

    Returns:
        RequestContext object
    """
    return RequestContext(request)


# Background task tracking
class BackgroundTaskTracker:
    """Track background tasks for monitoring"""

    def __init__(self) -> None:
        self._tasks: Dict[str, Dict[str, Any]] = {}

    def add_task(
        self, task_id: str, task_name: str, metadata: Optional[Dict[str, Any]] = None
    ):
        """Add a background task to tracking"""
        self._tasks[task_id] = {
            "name": task_name,
            "started_at": None,
            "metadata": metadata or {},
        }

    def get_task(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Get task information"""
        return self._tasks.get(task_id)

    def list_tasks(self) -> Dict[str, Dict[str, Any]]:
        """List all tracked tasks"""
        return self._tasks.copy()


background_task_tracker = BackgroundTaskTracker()


def get_background_task_tracker() -> BackgroundTaskTracker:
    """Get the background task tracker instance"""
    return background_task_tracker
