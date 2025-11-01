# app/extractors/azure/utils.py
"""
Shared utilities for Azure extractors.
"""

from typing import Any, Callable
from app.transport.retry_policy import create_retry_policy, RetryConfig, RetryStrategy
import logging

logger = logging.getLogger(__name__)


def _is_azure_throttling_error(exception: Exception) -> bool:
    """Check if an exception is an Azure throttling error that should be retried."""
    error_message = str(exception).lower()
    return (
        ("subscriptionrequests" in error_message and "throttled" in error_message)
        or (
            "number of 'read' requests" in error_message and "exceeded" in error_message
        )
        or ("try again after" in error_message)
    )


def create_azure_retry_policy(max_attempts: int = 5) -> Any:
    """Create a retry policy configured for Azure throttling errors."""
    retry_config = RetryConfig(
        max_attempts=max_attempts,
        base_delay=1.0,  # Start with 1 second as suggested in Azure errors
        max_delay=30.0,
        backoff_multiplier=2.0,
        strategy=RetryStrategy.EXPONENTIAL,
        retry_condition=_is_azure_throttling_error,
    )
    return create_retry_policy(retry_config)


async def execute_azure_api_call(
    operation: Callable[[], Any], operation_name: str, max_attempts: int = 5
) -> Any:
    """Execute an Azure API call with retry logic for throttling."""
    retry_policy = create_azure_retry_policy(max_attempts)
    return await retry_policy.execute_with_retry(operation, operation_name)
