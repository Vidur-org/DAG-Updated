"""Base Agent Interface

Defines the contract for external agents that can be composed
into larger meta-agent systems.
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from enum import Enum


class AgentStatus(Enum):
    """Standard agent execution statuses"""
    SUCCESS = "success"
    INSUFFICIENT_DATA = "insufficient_data"
    ERROR = "error"
    LOW_CONFIDENCE = "low_confidence"


class ExternalAgent(ABC):
    """
    Base class for all external agents.
    
    Design principles:
    - Never hallucinate
    - Return structured data only
    - Include confidence scores
    - Fail explicitly, not silently
    """
    
    @abstractmethod
    async def execute(self, query: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Execute the agent on a query.
        
        Args:
            query: User's natural language query
            context: Optional context from previous agents
            
        Returns:
            Standardized response dict with:
            {
                "agent": str,           # Agent identifier
                "status": AgentStatus,  # Execution status
                "confidence": float,    # 0.0 - 1.0
                "data": Dict,           # Structured results
                "metadata": Dict,       # Execution metadata
                "error": Optional[str]  # Error message if failed
            }
        """
        pass
    
    @abstractmethod
    def capabilities(self) -> Dict[str, Any]:
        """
        Describe what this agent can do.
        
        Returns:
            Dict describing:
            - domains: What domains it covers
            - query_types: What kinds of queries it handles
            - regions: Geographic coverage
            - freshness: Data freshness (realtime/daily/etc)
            - limitations: Known limitations
        """
        pass
    
    @abstractmethod
    def can_handle(self, query: str) -> float:
        """
        Assess if this agent can handle the query.
        
        Args:
            query: User query
            
        Returns:
            Confidence score 0.0 - 1.0
        """
        pass