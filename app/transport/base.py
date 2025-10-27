# app/transport/base.py
"""
Base transport interface for sending artifacts to external systems.
Provides abstract base class that all transport implementations must follow.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List, Protocol, TypeVar
from enum import Enum
from dataclasses import dataclass
from datetime import datetime, timezone
import logging

from app.core.exceptions import TransportError

logger = logging.getLogger(__name__)

T = TypeVar('T', bound='TransportWithSend')

class TransportWithSend(Protocol):
    """Protocol for transports that have a send method"""
    async def send(self, artifact: Dict[str, Any]) -> Any:
        ...


class TransportStatus(str, Enum):
    """Status of transport operation"""
    SUCCESS = "success"
    FAILED = "failed"
    RETRYING = "retrying"
    TIMEOUT = "timeout"
    RATE_LIMITED = "rate_limited"


@dataclass
class TransportResult:
    """Result of a transport operation"""
    status: TransportStatus
    artifact_id: str
    timestamp: datetime
    response_data: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    retry_count: int = 0
    duration_ms: Optional[float] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert result to dictionary"""
        return {
            'status': self.status.value,
            'artifact_id': self.artifact_id,
            'timestamp': self.timestamp.isoformat(),
            'response_data': self.response_data,
            'error_message': self.error_message,
            'retry_count': self.retry_count,
            'duration_ms': self.duration_ms
        }
    
    @property
    def is_success(self) -> bool:
        """Check if transport was successful"""
        return self.status == TransportStatus.SUCCESS
    
    @property
    def should_retry(self) -> bool:
        """Check if transport should be retried"""
        return self.status in [
            TransportStatus.FAILED,
            TransportStatus.TIMEOUT,
            TransportStatus.RATE_LIMITED
        ]


@dataclass
class TransportMetrics:
    """Metrics for transport operations"""
    total_sent: int = 0
    total_success: int = 0
    total_failed: int = 0
    total_retries: int = 0
    average_duration_ms: float = 0.0
    last_error: Optional[str] = None
    last_success_time: Optional[datetime] = None
    last_failure_time: Optional[datetime] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert metrics to dictionary"""
        return {
            'total_sent': self.total_sent,
            'total_success': self.total_success,
            'total_failed': self.total_failed,
            'total_retries': self.total_retries,
            'average_duration_ms': self.average_duration_ms,
            'success_rate': self.success_rate,
            'last_error': self.last_error,
            'last_success_time': self.last_success_time.isoformat() if self.last_success_time else None,
            'last_failure_time': self.last_failure_time.isoformat() if self.last_failure_time else None
        }
    
    @property
    def success_rate(self) -> float:
        """Calculate success rate percentage"""
        if self.total_sent == 0:
            return 0.0
        return (self.total_success / self.total_sent) * 100


class BaseTransport(ABC):
    """
    Abstract base class for all transport implementations.
    
    Transport implementations handle sending extracted artifacts to external
    systems like policy scanners, message queues, or data lakes.
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize transport with configuration.
        
        Args:
            config: Transport-specific configuration
        """
        self.config = config
        self.metrics = TransportMetrics()
        self._is_connected = False
        self._connection_errors = 0
        self._max_connection_errors = config.get('max_connection_errors', 5)
        
    @abstractmethod
    async def connect(self) -> bool:
        """
        Establish connection to the transport destination.
        
        Returns:
            True if connection successful
            
        Raises:
            TransportError: If connection fails
        """
        pass
    
    @abstractmethod
    async def disconnect(self) -> None:
        """
        Close connection to the transport destination.
        Should cleanup resources and close connections gracefully.
        """
        pass
    
    @abstractmethod
    async def send(self, artifact: Dict[str, Any]) -> TransportResult:
        """
        Send a single artifact to the destination.
        
        Args:
            artifact: The cloud artifact to send
            
        Returns:
            TransportResult indicating success/failure
            
        Raises:
            TransportError: If send operation fails critically
        """
        pass
    
    @abstractmethod
    async def send_batch(self, artifacts: List[Dict[str, Any]]) -> List[TransportResult]:
        """
        Send multiple artifacts in a batch operation.
        
        Args:
            artifacts: List of cloud artifacts to send
            
        Returns:
            List of TransportResult for each artifact
            
        Raises:
            TransportError: If batch operation fails critically
        """
        pass
    
    @abstractmethod
    async def health_check(self) -> bool:
        """
        Check if the transport destination is healthy and reachable.
        
        Returns:
            True if destination is healthy
        """
        pass
    
    def get_metrics(self) -> TransportMetrics:
        """
        Get current transport metrics.
        
        Returns:
            TransportMetrics object with current statistics
        """
        return self.metrics
    
    def reset_metrics(self) -> None:
        """Reset all metrics to initial state"""
        self.metrics = TransportMetrics()
    
    @property
    def is_connected(self) -> bool:
        """Check if transport is currently connected"""
        return self._is_connected
    
    @property
    def supports_batch(self) -> bool:
        """
        Override this property if transport doesn't support batching.
        Default is True.
        """
        return True
    
    async def _update_metrics_success(self, result: TransportResult) -> None:
        """Update metrics after successful send"""
        self.metrics.total_sent += 1
        self.metrics.total_success += 1
        self.metrics.last_success_time = datetime.now(timezone.utc)
        
        if result.duration_ms:
            # Update rolling average
            total = self.metrics.total_sent
            current_avg = self.metrics.average_duration_ms
            self.metrics.average_duration_ms = (
                (current_avg * (total - 1) + result.duration_ms) / total
            )
    
    async def _update_metrics_failure(self, result: TransportResult) -> None:
        """Update metrics after failed send"""
        self.metrics.total_sent += 1
        self.metrics.total_failed += 1
        self.metrics.last_failure_time = datetime.now(timezone.utc)
        
        if result.error_message:
            self.metrics.last_error = result.error_message
        
        if result.retry_count > 0:
            self.metrics.total_retries += result.retry_count
    
    async def _handle_connection_error(self, error: Exception) -> None:
        """
        Handle connection errors with circuit breaker pattern.
        
        Args:
            error: The connection error that occurred
        """
        self._connection_errors += 1
        logger.error(
            f"Connection error ({self._connection_errors}/{self._max_connection_errors}): {error}"
        )
        
        if self._connection_errors >= self._max_connection_errors:
            self._is_connected = False
            logger.critical(
                f"Transport connection failed after {self._connection_errors} attempts. "
                "Circuit breaker opened."
            )
    
    async def _reset_connection_errors(self) -> None:
        """Reset connection error counter after successful operation"""
        if self._connection_errors > 0:
            logger.info(f"Resetting connection error count from {self._connection_errors}")
            self._connection_errors = 0
    
    def __repr__(self) -> str:
        """String representation of transport"""
        return (
            f"{self.__class__.__name__}("
            f"connected={self._is_connected}, "
            f"sent={self.metrics.total_sent}, "
            f"success_rate={self.metrics.success_rate:.1f}%"
            ")"
        )


class BatchTransportMixin:
    """
    Mixin to provide default batch implementation for transports
    that don't natively support batching.
    """
    
    async def send_batch(self, artifacts: List[Dict[str, Any]]) -> List[TransportResult]:
        """
        Default batch implementation that sends artifacts one by one.
        
        Args:
            artifacts: List of artifacts to send
            
        Returns:
            List of TransportResult for each artifact
        """
        import asyncio
        
        logger.info(f"Sending batch of {len(artifacts)} artifacts sequentially")
        
        results = []
        for artifact in artifacts:
            try:
                result = await self.send(artifact)  # type: ignore
                results.append(result)
            except Exception as e:
                logger.error(f"Error sending artifact in batch: {e}")
                results.append(
                    TransportResult(
                        status=TransportStatus.FAILED,
                        artifact_id=artifact.get('resource_id', 'unknown'),
                        timestamp=datetime.now(timezone.utc),
                        error_message=str(e)
                    )
                )
        
        return results


class ParallelBatchTransportMixin:
    """
    Mixin to provide parallel batch implementation for transports
    that support concurrent operations.
    """
    
    async def send_batch(
        self, 
        artifacts: List[Dict[str, Any]], 
        max_concurrent: int = 10
    ) -> List[TransportResult]:
        """
        Send artifacts in parallel with concurrency control.
        
        Args:
            artifacts: List of artifacts to send
            max_concurrent: Maximum number of concurrent sends
            
        Returns:
            List of TransportResult for each artifact
        """
        import asyncio
        from asyncio import Semaphore
        
        logger.info(
            f"Sending batch of {len(artifacts)} artifacts with "
            f"max concurrency {max_concurrent}"
        )
        
        semaphore = Semaphore(max_concurrent)
        
        async def send_with_semaphore(artifact: Dict[str, Any]) -> TransportResult:
            async with semaphore:
                try:
                    return await self.send(artifact)  # type: ignore
                except Exception as e:
                    logger.error(f"Error sending artifact in parallel batch: {e}")
                    return TransportResult(
                        status=TransportStatus.FAILED,
                        artifact_id=artifact.get('resource_id', 'unknown'),
                        timestamp=datetime.now(timezone.utc),
                        error_message=str(e)
                    )
        
        tasks = [send_with_semaphore(artifact) for artifact in artifacts]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Convert any exceptions to TransportResult
        processed_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                processed_results.append(
                    TransportResult(
                        status=TransportStatus.FAILED,
                        artifact_id=artifacts[i].get('resource_id', 'unknown'),
                        timestamp=datetime.now(timezone.utc),
                        error_message=str(result)
                    )
                )
            else:
                processed_results.append(result)
        
        return processed_results


class NullTransport(BaseTransport):
    """
    Null transport implementation for testing and development.
    Accepts all artifacts without sending them anywhere.
    """
    
    async def connect(self) -> bool:
        """Always succeeds"""
        logger.info("NullTransport: Connected (no-op)")
        self._is_connected = True
        return True
    
    async def disconnect(self) -> None:
        """Always succeeds"""
        logger.info("NullTransport: Disconnected (no-op)")
        self._is_connected = False
    
    async def send(self, artifact: Dict[str, Any]) -> TransportResult:
        """
        Simulate successful send without actually sending.
        
        Args:
            artifact: The artifact to "send"
            
        Returns:
            Success TransportResult
        """
        import time
        start_time = time.time()
        
        # Simulate network delay
        import asyncio
        await asyncio.sleep(0.01)
        
        duration_ms = (time.time() - start_time) * 1000
        
        result = TransportResult(
            status=TransportStatus.SUCCESS,
            artifact_id=artifact.get('resource_id', 'unknown'),
            timestamp=datetime.now(timezone.utc),
            duration_ms=duration_ms,
            response_data={'simulated': True}
        )
        
        await self._update_metrics_success(result)
        
        logger.debug(f"NullTransport: Simulated send of {result.artifact_id}")
        return result
    
    async def send_batch(self, artifacts: List[Dict[str, Any]]) -> List[TransportResult]:
        """
        Simulate successful batch send.
        
        Args:
            artifacts: List of artifacts to "send"
            
        Returns:
            List of success TransportResults
        """
        results = []
        for artifact in artifacts:
            result = await self.send(artifact)
            results.append(result)
        return results
    
    async def health_check(self) -> bool:
        """Always healthy"""
        return True


class TransportFactory:
    """Factory for creating transport instances"""
    
    _transports: Dict[str, type] = {}
    
    @classmethod
    def register(cls, name: str, transport_class: type) -> None:
        """
        Register a transport implementation.
        
        Args:
            name: Name to register transport under
            transport_class: Transport class to register
        """
        if not issubclass(transport_class, BaseTransport):
            raise ValueError(
                f"{transport_class.__name__} must inherit from BaseTransport"
            )
        
        cls._transports[name.lower()] = transport_class
        logger.info(f"Registered transport: {name}")
    
    @classmethod
    def create(cls, transport_type: str, config: Dict[str, Any]) -> BaseTransport:
        """
        Create a transport instance.
        
        Args:
            transport_type: Type of transport to create
            config: Configuration for the transport
            
        Returns:
            Transport instance
            
        Raises:
            ValueError: If transport type not registered
        """
        transport_type = transport_type.lower()
        
        if transport_type not in cls._transports:
            raise ValueError(
                f"Unknown transport type: {transport_type}. "
                f"Available: {', '.join(cls._transports.keys())}"
            )
        
        transport_class = cls._transports[transport_type]
        return transport_class(config)
    
    @classmethod
    def list_transports(cls) -> List[str]:
        """List all registered transport types"""
        return list(cls._transports.keys())


# Register default transports
TransportFactory.register('null', NullTransport)
