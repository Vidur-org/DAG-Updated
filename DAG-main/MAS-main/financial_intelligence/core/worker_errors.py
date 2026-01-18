"""
Standardized error handling for all workers.
"""

from dataclasses import dataclass
from typing import Dict, Any, Optional
from enum import Enum


class WorkerErrorStatus(Enum):
    """Standardized error statuses for all workers."""
    DATA_UNAVAILABLE = "DATA_UNAVAILABLE"
    NETWORK_ERROR = "NETWORK_ERROR"
    VALIDATION_ERROR = "VALIDATION_ERROR"
    TIMEOUT_ERROR = "TIMEOUT_ERROR"
    RATE_LIMIT_ERROR = "RATE_LIMIT_ERROR"
    AUTHENTICATION_ERROR = "AUTHENTICATION_ERROR"
    PARSE_ERROR = "PARSE_ERROR"
    TIMELock_VIOLATION = "TIMELOCK_VIOLATION"
    DOMAIN_CONTAMINATION = "DOMAIN_CONTAMINATION"
    CONTAMINATION_DETECTED = "CONTAMINATION_DETECTED"
    UNVERIFIABLE_SOURCE = "UNVERIFIABLE_SOURCE"
    FORWARD_LOOKING_DETECTED = "FORWARD_LOOKING_DETECTED"


@dataclass
class WorkerError:
    """
    Standardized error structure for all workers.
    
    This ensures consistent error handling across the system
    and provides proper metadata for debugging and governance.
    """
    
    status: WorkerErrorStatus
    message: str
    worker_name: str
    query: Optional[str] = None
    entities: Optional[list] = None
    metadata: Optional[Dict[str, Any]] = None
    timestamp: Optional[str] = None
    retry_count: Optional[int] = 0
    
    def __post_init__(self):
        """Initialize timestamp if not provided."""
        if self.timestamp is None:
            from datetime import datetime
            self.timestamp = datetime.now().isoformat()
        
        if self.metadata is None:
            self.metadata = {}
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API responses."""
        return {
            "status": self.status.value,
            "message": self.message,
            "worker_name": self.worker_name,
            "query": self.query,
            "entities": self.entities,
            "metadata": self.metadata,
            "timestamp": self.timestamp,
            "retry_count": self.retry_count
        }
    
    def is_retryable(self) -> bool:
        """Check if this error is retryable."""
        retryable_statuses = [
            WorkerErrorStatus.NETWORK_ERROR,
            WorkerErrorStatus.TIMEOUT_ERROR,
            WorkerErrorStatus.RATE_LIMIT_ERROR,
            WorkerErrorStatus.AUTHENTICATION_ERROR
        ]
        return self.status in retryable_statuses
    
    def is_blocking(self) -> bool:
        """Check if this error should block the entire query."""
        blocking_statuses = [
            WorkerErrorStatus.TIMELOCK_VIOLATION,
            WorkerErrorStatus.DOMAIN_CONTAMINATION,
            WorkerErrorStatus.CONTAMINATION_DETECTED
        ]
        return self.status in blocking_statuses


class WorkerException(Exception):
    """Exception wrapper for WorkerError."""
    
    def __init__(self, error: WorkerError):
        self.error = error
        super().__init__(error.message)


# Convenience functions for common errors
def create_data_unavailable_error(worker_name: str, message: str, **kwargs) -> WorkerError:
    """Create a data unavailable error."""
    return WorkerError(
        status=WorkerErrorStatus.DATA_UNAVAILABLE,
        message=message,
        worker_name=worker_name,
        **kwargs
    )


def create_network_error(worker_name: str, message: str, **kwargs) -> WorkerError:
    """Create a network error."""
    return WorkerError(
        status=WorkerErrorStatus.NETWORK_ERROR,
        message=message,
        worker_name=worker_name,
        **kwargs
    )


def create_timelock_violation_error(worker_name: str, data_date: str, max_date: str, **kwargs) -> WorkerError:
    """Create a timelock violation error."""
    return WorkerError(
        status=WorkerErrorStatus.TIMELOCK_VIOLATION,
        message=f"Data date {data_date} exceeds max_allowed_date {max_date}",
        worker_name=worker_name,
        metadata={"data_date": data_date, "max_allowed_date": max_date, **kwargs.get("metadata", {})},
        **{k: v for k, v in kwargs.items() if k != "metadata"}
    )


def create_contamination_error(worker_name: str, contamination_type: str, **kwargs) -> WorkerError:
    """Create a contamination detection error."""
    return WorkerError(
        status=WorkerErrorStatus.CONTAMINATION_DETECTED,
        message=f"{contamination_type} contamination detected",
        worker_name=worker_name,
        metadata={"contamination_type": contamination_type, **kwargs.get("metadata", {})},
        **{k: v for k, v in kwargs.items() if k != "metadata"}
    )


def create_forward_looking_error(worker_name: str, source: str, **kwargs) -> WorkerError:
    """Create a forward-looking content detection error."""
    return WorkerError(
        status=WorkerErrorStatus.FORWARD_LOOKING_DETECTED,
        message=f"Forward-looking content detected in {source}",
        worker_name=worker_name,
        metadata={"source": source, **kwargs.get("metadata", {})},
        **{k: v for k, v in kwargs.items() if k != "metadata"}
    )
