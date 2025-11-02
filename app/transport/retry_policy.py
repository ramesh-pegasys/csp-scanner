# app/transport/retry_policy.py
"""
Custom retry policy implementation with exponential backoff.
Provides flexible retry logic for transport operations with configurable backoff strategies.
"""

from typing import Dict, Any, Optional, Callable, List, Type
from enum import Enum
from dataclasses import dataclass
from datetime import datetime, timezone
import asyncio
import random
import logging
import time

logger = logging.getLogger(__name__)


class RetryStrategy(str, Enum):
    """Retry strategies for backoff calculation"""

    EXPONENTIAL = "exponential"
    LINEAR = "linear"
    FIXED = "fixed"


class JitterType(str, Enum):
    """Types of jitter to apply to backoff delays"""

    NONE = "none"
    FULL = "full"
    EQUAL = "equal"
    DECORRELATED = "decorrelated"


@dataclass
class RetryConfig:
    """Configuration for retry policy"""

    max_attempts: int = 3
    base_delay: float = 1.0  # seconds
    max_delay: float = 60.0  # seconds
    backoff_multiplier: float = 2.0
    strategy: RetryStrategy = RetryStrategy.EXPONENTIAL
    jitter_type: JitterType = JitterType.NONE
    jitter_factor: float = 0.1
    retryable_exceptions: Optional[List[Type[Exception]]] = None
    retry_condition: Optional[Callable[[Exception], bool]] = None

    def __post_init__(self):
        """Validate configuration"""
        if self.max_attempts < 1:
            raise ValueError("max_attempts must be at least 1")
        if self.base_delay <= 0:
            raise ValueError("base_delay must be positive")
        if self.max_delay < self.base_delay:
            raise ValueError("max_delay must be >= base_delay")
        if self.backoff_multiplier <= 1 and self.strategy == RetryStrategy.EXPONENTIAL:
            raise ValueError("backoff_multiplier must be > 1 for exponential strategy")


@dataclass
class RetryAttempt:
    """Information about a retry attempt"""

    attempt_number: int
    delay: float
    exception: Optional[Exception] = None
    timestamp: Optional[datetime] = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now(timezone.utc)


class RetryPolicy:
    """
    Custom retry policy with exponential backoff and configurable strategies.

    Supports different backoff strategies, jitter, and flexible retry conditions.
    """

    def __init__(self, config: RetryConfig):
        """
        Initialize retry policy with configuration.

        Args:
            config: RetryConfig with policy settings
        """
        self.config = config
        self.attempts: List[RetryAttempt] = []

    def calculate_delay(self, attempt_number: int) -> float:
        """
        Calculate delay for the given attempt number.

        Args:
            attempt_number: Current attempt number (0-based)

        Returns:
            Delay in seconds
        """
        if attempt_number == 0:
            return 0.0

        base_delay = self.config.base_delay

        # Calculate base delay based on strategy
        if self.config.strategy == RetryStrategy.EXPONENTIAL:
            delay = base_delay * (self.config.backoff_multiplier**attempt_number)
        elif self.config.strategy == RetryStrategy.LINEAR:
            delay = base_delay + (base_delay * attempt_number)
        elif self.config.strategy == RetryStrategy.FIXED:
            delay = base_delay
        else:
            delay = base_delay

        # Apply maximum delay cap
        delay = min(delay, self.config.max_delay)

        # Apply jitter
        delay = self._apply_jitter(delay, attempt_number)

        return delay

    def _apply_jitter(self, delay: float, attempt_number: int) -> float:
        """
        Apply jitter to the calculated delay.

        Args:
            delay: Base delay before jitter
            attempt_number: Current attempt number

        Returns:
            Delay with jitter applied
        """
        if self.config.jitter_type == JitterType.NONE:
            return delay

        jitter_factor = self.config.jitter_factor

        if self.config.jitter_type == JitterType.FULL:
            # Full jitter: random delay between 0 and calculated delay
            return random.uniform(0, delay)

        elif self.config.jitter_type == JitterType.EQUAL:
            # Equal jitter: add random jitter around the delay
            jitter = delay * jitter_factor * random.uniform(-1, 1)
            return max(0, delay + jitter)

        elif self.config.jitter_type == JitterType.DECORRELATED:
            # Decorrelated jitter: exponential backoff with randomization
            if attempt_number == 1:
                return delay
            prev_delay = (
                self.attempts[-1].delay if self.attempts else self.config.base_delay
            )
            return random.uniform(self.config.base_delay, prev_delay * 3)

        return delay

    def should_retry(self, exception: Exception, attempt_number: int) -> bool:
        """
        Determine if the operation should be retried.

        Args:
            exception: The exception that occurred
            attempt_number: Current attempt number (0-based)

        Returns:
            True if should retry, False otherwise
        """
        # Check max attempts
        if attempt_number >= self.config.max_attempts - 1:
            return False

        # Check retryable exceptions
        if self.config.retryable_exceptions:
            if not any(
                isinstance(exception, exc_type)
                for exc_type in self.config.retryable_exceptions
            ):
                return False

        # Check custom retry condition
        if self.config.retry_condition:
            if not self.config.retry_condition(exception):
                return False

        return True

    async def execute_with_retry(
        self, operation: Callable[[], Any], operation_name: str = "operation"
    ) -> Any:
        """
        Execute an operation with retry logic.

        Args:
            operation: Async callable to execute
            operation_name: Name for logging purposes

        Returns:
            Result of the operation

        Raises:
            Exception: Last exception if all retries exhausted
        """
        self.attempts = []
        last_exception = None

        for attempt in range(self.config.max_attempts):
            try:
                logger.debug(
                    f"Attempting {operation_name} (attempt {attempt + 1}/{self.config.max_attempts})"
                )

                # Calculate delay for this attempt
                delay = self.calculate_delay(attempt)

                # Wait if not the first attempt
                if delay > 0:
                    logger.debug(f"Waiting {delay:.2f}s before retry")
                    await asyncio.sleep(delay)

                # Execute operation
                start_time = time.time()
                result = await operation()
                duration = time.time() - start_time

                logger.debug(
                    f"{operation_name} succeeded on attempt {attempt + 1} in {duration:.2f}s"
                )
                return result

            except Exception as e:
                last_exception = e
                attempt_info = RetryAttempt(
                    attempt_number=attempt + 1,
                    delay=self.calculate_delay(attempt),
                    exception=e,
                )
                self.attempts.append(attempt_info)

                logger.warning(f"{operation_name} failed on attempt {attempt + 1}: {e}")

                # Check if we should retry
                if not self.should_retry(e, attempt):
                    logger.error(
                        f"{operation_name} failed permanently after {attempt + 1} attempts"
                    )
                    break

        # All retries exhausted
        if last_exception:
            raise last_exception
        else:
            raise RuntimeError(f"{operation_name} failed with unknown error")

    def get_retry_stats(self) -> Dict[str, Any]:
        """
        Get statistics about retry attempts.

        Returns:
            Dictionary with retry statistics
        """
        if not self.attempts:
            return {
                "total_attempts": 0,
                "successful_attempt": None,
                "total_delay": 0.0,
                "last_exception": None,
            }

        total_delay = sum(attempt.delay for attempt in self.attempts)

        return {
            "total_attempts": len(self.attempts),
            "successful_attempt": None,  # Would be set if we tracked success
            "total_delay": total_delay,
            "last_exception": (
                str(self.attempts[-1].exception)
                if self.attempts[-1].exception
                else None
            ),
            "attempts": [
                {
                    "number": attempt.attempt_number,
                    "delay": attempt.delay,
                    "exception": str(attempt.exception) if attempt.exception else None,
                    "timestamp": (
                        attempt.timestamp.isoformat() if attempt.timestamp else None
                    ),
                }
                for attempt in self.attempts
            ],
        }


# Pre-configured retry policies for common use cases
DEFAULT_RETRY_CONFIG = RetryConfig(
    max_attempts=3,
    base_delay=1.0,
    max_delay=30.0,
    backoff_multiplier=2.0,
    strategy=RetryStrategy.EXPONENTIAL,
    jitter_type=JitterType.EQUAL,
    jitter_factor=0.1,
)

AGGRESSIVE_RETRY_CONFIG = RetryConfig(
    max_attempts=5,
    base_delay=0.5,
    max_delay=60.0,
    backoff_multiplier=2.0,
    strategy=RetryStrategy.EXPONENTIAL,
    jitter_type=JitterType.FULL,
)

CONSERVATIVE_RETRY_CONFIG = RetryConfig(
    max_attempts=2,
    base_delay=2.0,
    max_delay=10.0,
    backoff_multiplier=1.5,
    strategy=RetryStrategy.EXPONENTIAL,
    jitter_type=JitterType.NONE,
)


def create_retry_policy(config: Optional[RetryConfig] = None) -> RetryPolicy:
    """
    Create a retry policy with the given configuration.

    Args:
        config: RetryConfig to use, defaults to DEFAULT_RETRY_CONFIG

    Returns:
        Configured RetryPolicy instance
    """
    if config is None:
        config = DEFAULT_RETRY_CONFIG
    return RetryPolicy(config)
