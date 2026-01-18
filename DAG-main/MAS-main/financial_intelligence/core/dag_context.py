"""DAG Context and Error Classes

Core data structures for governance and validation
"""
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any
from datetime import datetime
from enum import Enum


class DomainType(Enum):
    """Domain classification"""
    FINANCIAL = "FINANCIAL"
    NON_FINANCIAL = "NON_FINANCIAL"
    MIXED = "MIXED"


class QuarantineStatus(Enum):
    """Intelligence quarantine status"""
    CLEAN = "CLEAN"
    FORWARD_LOOKING = "FORWARD_LOOKING"
    UNVERIFIABLE = "UNVERIFIABLE"
    CONTAMINATED = "CONTAMINATED"


@dataclass
class Timelock:
    """Temporal consistency enforcement"""
    as_of_date: str  # YYYY-MM-DD
    max_allowed_date: str  # YYYY-MM-DD
    
    def validate_date(self, date_str: str) -> bool:
        """Check if date is within allowed range"""
        try:
            date = datetime.strptime(date_str, "%Y-%m-%d")
            max_date = datetime.strptime(self.max_allowed_date, "%Y-%m-%d")
            return date <= max_date
        except (ValueError, TypeError):
            return False
    
    def to_dict(self) -> Dict[str, str]:
        return {
            "as_of_date": self.as_of_date,
            "max_allowed_date": self.max_allowed_date
        }


@dataclass
class DAGContext:
    """Complete context for DAG-safe execution"""
    query: str
    intent: str
    entities: List[Dict[str, Any]] = field(default_factory=list)
    timelock: Timelock = None
    domain_hint: DomainType = DomainType.FINANCIAL
    required_metrics: List[str] = field(default_factory=list)
    confidence: float = 0.5
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            "query": self.query,
            "intent": self.intent,
            "entities": self.entities,
            "timelock": self.timelock.to_dict() if self.timelock else None,
            "domain_hint": self.domain_hint.value,
            "required_metrics": self.required_metrics,
            "confidence": self.confidence
        }


@dataclass
class GovernanceMetadata:
    """Metadata for governance validation results"""
    timelock_validated: bool = False
    domain_purity_check: str = "NOT_CHECKED"  # PASSED | FAILED | NOT_CHECKED
    completeness_score: float = 0.0
    quarantine_status: QuarantineStatus = QuarantineStatus.CLEAN
    validation_timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "timelock_validated": self.timelock_validated,
            "domain_purity_check": self.domain_purity_check,
            "completeness_score": self.completeness_score,
            "quarantine_status": self.quarantine_status.value,
            "validation_timestamp": self.validation_timestamp
        }


# ==========================================
# ERROR CLASSES
# ==========================================

class WorkerError(Exception):
    """Base error for all workers"""
    def __init__(self, status: str, message: str, metadata: Dict = None):
        self.status = status
        self.message = message
        self.metadata = metadata or {}
        super().__init__(message)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "status": "error",
            "error_type": self.status,
            "message": self.message,
            "metadata": self.metadata
        }


class TimelockViolationError(WorkerError):
    """Raised when data exceeds max_allowed_date"""
    def __init__(self, message: str, date_found: str, max_allowed: str):
        super().__init__(
            status="TIMELOCK_VIOLATION",
            message=message,
            metadata={"date_found": date_found, "max_allowed": max_allowed}
        )


class DomainContaminationError(WorkerError):
    """Raised when non-financial data contaminates financial queries"""
    def __init__(self, message: str, expected_domain: str, actual_domain: str):
        super().__init__(
            status="DOMAIN_CONTAMINATION",
            message=message,
            metadata={"expected": expected_domain, "actual": actual_domain}
        )


class MissingDataError(WorkerError):
    """Raised when required metrics are missing"""
    def __init__(self, message: str, missing_metrics: List[str]):
        super().__init__(
            status="MISSING_DATA",
            message=message,
            metadata={"missing_metrics": missing_metrics}
        )


class IntelligenceContaminationError(WorkerError):
    """Raised when forward-looking data contaminates calculations"""
    def __init__(self, message: str, contaminated_fields: List[str]):
        super().__init__(
            status="INTELLIGENCE_CONTAMINATION",
            message=message,
            metadata={"contaminated_fields": contaminated_fields}
        )


class PlannerError(Exception):
    """Planner-specific errors"""
    pass


class ValidationError(Exception):
    """Validation errors"""
    pass


class AdapterError(Exception):
    """Adapter errors"""
    pass