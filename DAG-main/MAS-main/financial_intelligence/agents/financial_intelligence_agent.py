"""Financial Intelligence Agent

Wraps the entire financial intelligence system as a single external agent.
This agent can be composed into larger meta-agent systems.
"""
import asyncio
from typing import Dict, Any, Optional
from datetime import datetime

from external_agents.base_agent import ExternalAgent, AgentStatus
from orchestrator import ParallelOrchestrator
from planner.planner_llm import invoke_planner_llm
from planner.validator import validate_planner_output
from utils.entity_resolver import resolve_entities


class FinancialIntelligenceAgent(ExternalAgent):
    """
    Black-box financial intelligence capability.
    
    Handles:
    - Company fundamentals
    - Market prices
    - Macro indicators
    - News analysis
    """
    
    def __init__(self):
        self.orchestrator = ParallelOrchestrator()
        
        # Confidence thresholds
        self.MIN_CONFIDENCE = 0.3
        self.HIGH_CONFIDENCE = 0.7
        
    async def execute(self, query: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Execute financial intelligence pipeline.
        
        Returns standardized agent response.
        """
        start_time = datetime.now()
        
        try:
            # Step 1: Intent classification
            raw_plan = invoke_planner_llm(query)
            plan = validate_planner_output(raw_plan)
            
            intent = plan.get('intent')
            confidence = plan.get('confidence', 0.0)
            
            # Confidence gate
            if confidence < self.MIN_CONFIDENCE:
                return self._insufficient_confidence_response(
                    query=query,
                    intent=intent,
                    confidence=confidence,
                    reason="Query intent unclear or outside financial domain"
                )
            
            # Step 2: Entity resolution
            entities = resolve_entities(query)
            plan['entities'] = entities
            plan['query'] = query
            
            # Step 3: Execute workers
            result = await self.orchestrator.execute(plan)
            
            # Step 4: Check if we got useful data
            if not self._has_useful_data(result):
                return self._insufficient_data_response(
                    query=query,
                    intent=intent,
                    confidence=confidence,
                    reason="No relevant data found for query"
                )
            
            # Step 5: Build successful response
            execution_time = (datetime.now() - start_time).total_seconds()
            
            return {
                "agent": "financial_intelligence",
                "status": AgentStatus.SUCCESS.value,
                "confidence": confidence,
                "data": {
                    "intent": intent,
                    "entities": entities,
                    "results": result.get("results", {}),
                    "workers_executed": result.get("workers_executed", [])
                },
                "metadata": {
                    "execution_time_seconds": round(execution_time, 2),
                    "timestamp": datetime.now().isoformat(),
                    "query": query
                },
                "error": None
            }
            
        except Exception as e:
            return self._error_response(
                query=query,
                error=str(e),
                execution_time=(datetime.now() - start_time).total_seconds()
            )
    
    def capabilities(self) -> Dict[str, Any]:
        """Describe agent capabilities"""
        return {
            "agent_name": "financial_intelligence",
            "version": "1.0",
            "domains": [
                "macroeconomics",
                "equities",
                "commodities",
                "fixed_income",
                "forex",
                "crypto",
                "market_analysis",
                "news_impact"
            ],
            "query_types": [
                "fundamental_analysis",
                "price_lookup",
                "macro_indicators",
                "news_analysis",
                "impact_assessment"
            ],
            "regions": ["US", "IN", "GLOBAL"],
            "data_sources": [
                "Yahoo Finance",
                "FRED (Federal Reserve)",
                "Screener.in",
                "Web News Search"
            ],
            "freshness": {
                "prices": "15-minute delay",
                "news": "real-time",
                "fundamentals": "quarterly",
                "macro": "monthly/quarterly"
            },
            "limitations": [
                "No forward-looking predictions",
                "No investment advice",
                "Historical data only",
                "No high-frequency data"
            ]
        }
    
    def can_handle(self, query: str) -> float:
        """
        Assess if this agent can handle the query.
        
        Uses the planner's confidence as the primary signal.
        """
        try:
            raw_plan = invoke_planner_llm(query)
            plan = validate_planner_output(raw_plan)
            
            intent = plan.get('intent', 'NON_FINANCIAL')
            confidence = plan.get('confidence', 0.0)
            
            # Penalize NON_FINANCIAL intent
            if intent == 'NON_FINANCIAL':
                return max(0.0, confidence - 0.3)
            
            return confidence
            
        except Exception:
            return 0.0
    
    # Helper methods
    
    def _has_useful_data(self, result: Dict[str, Any]) -> bool:
        """Check if orchestrator returned useful data"""
        if result.get('status') != 'success':
            return False
        
        results = result.get('results', {})
        if not results:
            return False
        
        # Check if at least one worker returned success
        for worker_result in results.values():
            if isinstance(worker_result, dict):
                if worker_result.get('status') == 'success':
                    return True
        
        return False
    
    def _insufficient_confidence_response(
        self, 
        query: str, 
        intent: str, 
        confidence: float,
        reason: str
    ) -> Dict[str, Any]:
        """Return structured response for low confidence"""
        return {
            "agent": "financial_intelligence",
            "status": AgentStatus.LOW_CONFIDENCE.value,
            "confidence": confidence,
            "data": {
                "intent": intent,
                "reason": reason
            },
            "metadata": {
                "timestamp": datetime.now().isoformat(),
                "query": query
            },
            "error": None
        }
    
    def _insufficient_data_response(
        self,
        query: str,
        intent: str,
        confidence: float,
        reason: str
    ) -> Dict[str, Any]:
        """Return structured response when no data found"""
        return {
            "agent": "financial_intelligence",
            "status": AgentStatus.INSUFFICIENT_DATA.value,
            "confidence": confidence,
            "data": {
                "intent": intent,
                "reason": reason
            },
            "metadata": {
                "timestamp": datetime.now().isoformat(),
                "query": query
            },
            "error": None
        }
    
    def _error_response(
        self,
        query: str,
        error: str,
        execution_time: float
    ) -> Dict[str, Any]:
        """Return structured error response"""
        return {
            "agent": "financial_intelligence",
            "status": AgentStatus.ERROR.value,
            "confidence": 0.0,
            "data": {},
            "metadata": {
                "execution_time_seconds": round(execution_time, 2),
                "timestamp": datetime.now().isoformat(),
                "query": query
            },
            "error": error
        }