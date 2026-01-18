"""Fixed Orchestrator - Routes Fundamentals Directly to WebGPT

Key changes:
1. COMPANY_FUNDAMENTALS intent -> skip workers, go to WebGPT
2. Fixed fallback handler interface
3. Better error handling
"""
import asyncio
from typing import Dict, Any, List
from datetime import datetime
import structlog

from financial_intelligence.workers.macro_worker import MacroWorker
from financial_intelligence.workers.fundamentals_worker import FundamentalsWorker
from financial_intelligence.workers.prices_worker import PricesWorker
from financial_intelligence.workers.news_worker import NewsWorker
from financial_intelligence.workers.us_fundamentals_worker import USFundamentalsWorker
from financial_intelligence.utils.region_resolver import resolve_region_from_entities
from financial_intelligence.news_analyzer import NewsAnalyzer
from financial_intelligence.groq_fallback import get_groq_fallback_handler, get_hybrid_fallback_handler
from financial_intelligence.config import (
    AGGREGATE_CONFIDENCE_THRESHOLD, 
    get_fallback_system_type,
    should_enable_fallback,
    should_enable_groq_fallback,
    should_enable_openai_fallback
)
from financial_intelligence.improved_verifier import calculate_confidence, should_trigger_fallback as strict_should_trigger_fallback
from financial_intelligence.core.dag_context import (
    DAGContext, Timelock, DomainType, GovernanceMetadata,
    TimelockViolationError, DomainContaminationError,
    MissingDataError, IntelligenceContaminationError
)

# Initialize structured logger
logger = structlog.get_logger()


class ParallelOrchestrator:
    """Orchestrator with direct WebGPT routing for fundamentals"""
    
    def __init__(self):
        self.macro_worker = MacroWorker()
        self.fundamentals_worker = FundamentalsWorker()
        self.us_fundamentals_worker = USFundamentalsWorker()
        self.prices_worker = PricesWorker()
        self.news_worker = NewsWorker()
        self.news_analyzer = NewsAnalyzer()
        
        # Initialize fallback handler based on configuration
        fallback_system = get_fallback_system_type()
        if fallback_system == "groq":
            self.fallback_handler = get_groq_fallback_handler()
            print(f"🔧 Initialized with Groq fallback system")
        elif fallback_system == "openai":
            self.fallback_handler = get_openai_fallback_handler()
            print(f"🔧 Initialized with OpenAI fallback system")
        elif fallback_system == "hybrid":
            self.fallback_handler = get_hybrid_fallback_handler()
            print(f"🔧 Initialized with Hybrid fallback system")
        else:
            # Default to Groq for backward compatibility
            self.fallback_handler = get_groq_fallback_handler()
            print(f"🔧 Unknown fallback system '{fallback_system}', defaulting to Groq")
        
        # Intent to worker mapping
        self.WORKER_MAP = {
            "MACRO_DATA": ["macro", "news"],
            "COMPANY_FUNDAMENTALS": [],  # EMPTY - ALWAYS route to WebGPT fallback
            "MARKET_PRICES": ["prices", "news"],
            "NEWS_ANALYSIS": ["news"],
            "MIXED": ["macro", "prices", "fundamentals_in", "fundamentals_us", "news"],
            "NON_FINANCIAL": ["news"]
        }
    
    async def execute(self, planner_output: Dict[str, Any]) -> Dict[str, Any]:
        """Execute with direct WebGPT routing for fundamentals"""
        
        start_time = datetime.now()
        
        try:
            # STEP 1: Build DAGContext
            context = self._build_dag_context(planner_output)
            
            logger.info(
                "orchestrator.execute.start",
                intent=context.intent,
                query=context.query[:50],
                entities_count=len(context.entities),
                domain=context.domain_hint.value
            )
            
            # STEP 2: Validate context
            self._validate_context(context)
            
            # STEP 3: Determine workers
            workers_needed = self.WORKER_MAP.get(context.intent, [])
            
            if not workers_needed:
                return await self._handle_no_workers(context, start_time)
            
            # STEP 4: Execute workers in parallel
            worker_results = await self._execute_workers(context, workers_needed)
            
            # STEP 5: Analyze news if available
            if "NEWS" in worker_results:
                worker_results = await self._analyze_news(
                    worker_results, 
                    context
                )
            
            # STEP 6: Calculate aggregate confidence
            aggregate_confidence, confidence_breakdown = calculate_confidence(
                intent=context.intent,
                planner_confidence=context.confidence,
                worker_results=worker_results,
                query=context.query
            )
            
            worker_confidences = confidence_breakdown["worker_confidences"]
            
            logger.info(
                "orchestrator.confidence_check",
                planner_confidence=context.confidence,
                worker_confidences=worker_confidences,
                aggregate_confidence=aggregate_confidence,
                intent=context.intent
            )
            
            # STEP 7: Check if fallback should trigger
            fallback_triggered = False
            fallback_response = None
            fallback_reason = None
            
            should_fallback, strict_fallback_reason = strict_should_trigger_fallback(
                intent=context.intent,
                aggregate_confidence=aggregate_confidence
            )
            
            # DEBUG: Print fallback check details
            print(f"   🐛 DEBUG: Intent={context.intent}, Aggregate={aggregate_confidence:.2f}")
            print(f"   🐛 DEBUG: Should fallback={should_fallback}, Reason={strict_fallback_reason}")
            
            # Special rule: Trigger fallback if NEWS_ANALYSIS confidence < 0.6
            news_analysis_confidence = worker_confidences.get("NEWS_ANALYSIS", 1.0)
            if context.intent == "NEWS_ANALYSIS" and news_analysis_confidence < 0.6:
                should_fallback = True
                strict_fallback_reason = f"NEWS_ANALYSIS confidence {news_analysis_confidence:.2f} below 0.6 threshold"
                print(f"   🐛 DEBUG: NEWS_ANALYSIS confidence {news_analysis_confidence:.2f} < 0.6 - forcing fallback")
            
            if should_fallback:
                fallback_reason = strict_fallback_reason
                
                logger.info(
                    "orchestrator.fallback_trigger",
                    reason=fallback_reason,
                    aggregate_confidence=aggregate_confidence
                )
                
                print(f"\n⚠️  Aggregate confidence ({aggregate_confidence:.2f}) below threshold")
                fallback_system = get_fallback_system_type()
                print(f"🔄 Triggering {fallback_system} fallback: {fallback_reason}")
                
                # Trigger fallback
                try:
                    fallback_response = await self.fallback_handler.answer_query(
                        context.query,
                        worker_results
                    )
                    fallback_triggered = True
                    
                    if fallback_response.get("status") == "success":
                        print(f"✅ {fallback_system} fallback completed successfully")
                    else:
                        print(f"⚠️  {fallback_system} fallback failed: {fallback_response.get('message')}")
                        
                except Exception as e:
                    logger.error("orchestrator.fallback_error", error=str(e))
                    fallback_response = {
                        "status": "error",
                        "message": str(e)
                    }
            
            # STEP 8: Final governance check
            final_status = self._final_governance_check(worker_results, context)
            
            execution_time = (datetime.now() - start_time).total_seconds()
            
            logger.info(
                "orchestrator.execute.complete",
                status=final_status,
                workers=list(worker_results.keys()),
                execution_time=execution_time,
                fallback_triggered=fallback_triggered
            )
            
            # STEP 9: Build response
            response = {
                "status": final_status,
                "query": context.query,
                "intent": context.intent,
                "planner_confidence": context.confidence,
                "worker_confidences": worker_confidences,
                "aggregate_confidence": aggregate_confidence,
                "workers_executed": list(worker_results.keys()),
                "execution_time_seconds": round(execution_time, 2),
                "results": worker_results,
                "timestamp": datetime.now().isoformat(),
                "_context": context.to_dict()
            }
            
            # Add fallback information if triggered
            if fallback_triggered:
                response["fallback_triggered"] = True
                response["fallback_reason"] = fallback_reason
                response["fallback_response"] = fallback_response
            
            return response
            
        except TimelockViolationError as e:
            logger.error("orchestrator.timelock_violation", error=str(e))
            return self._build_error_response("TIMELOCK_VIOLATION", e)
        
        except DomainContaminationError as e:
            logger.error("orchestrator.domain_contamination", error=str(e))
            return self._build_error_response("DOMAIN_CONTAMINATION", e)
        
        except MissingDataError as e:
            logger.error("orchestrator.missing_data", error=str(e))
            return self._build_error_response("MISSING_DATA", e)
        
        except Exception as e:
            logger.error("orchestrator.error", error=str(e))
            return self._build_error_response("UNKNOWN_ERROR", e)
    
    async def _handle_fundamentals_direct(
        self,
        context: DAGContext,
        start_time: datetime
    ) -> Dict[str, Any]:
        """Handle COMPANY_FUNDAMENTALS by routing directly to WebGPT"""
        
        print(f"   🔍 Querying WebGPT for fundamentals...")
        
        try:
            # Call WebGPT directly
            fallback_response = await self.fallback_handler.answer_query(
                context.query,
                None  # No worker results
            )
            
            print(f"   DEBUG: fallback_response type: {type(fallback_response)}")
            if fallback_response:
                print(f"   DEBUG: fallback_response keys: {list(fallback_response.keys()) if isinstance(fallback_response, dict) else 'Not a dict'}")
            
            execution_time = (datetime.now() - start_time).total_seconds()
            
            if fallback_response.get("status") == "success":
                print(f"   ✅ WebGPT fundamentals query completed")
                
                return {
                    "status": "APPROVED",
                    "query": context.query,
                    "intent": context.intent,
                    "planner_confidence": context.confidence,
                    "worker_confidences": {},
                    "aggregate_confidence": 0.0,  # Not applicable
                    "workers_executed": [],
                    "execution_time_seconds": round(execution_time, 2),
                    "fallback_triggered": True,
                    "fallback_reason": "Direct fundamentals query to WebGPT",
                    "fallback_response": fallback_response,
                    "timestamp": datetime.now().isoformat(),
                    "_context": context.to_dict()
                }
            else:
                print(f"   ❌ WebGPT fundamentals query failed: {fallback_response.get('message')}")
                
                return {
                    "status": "error",
                    "query": context.query,
                    "intent": context.intent,
                    "error": f"WebGPT fundamentals query failed: {fallback_response.get('message')}",
                    "fallback_triggered": True,
                    "fallback_reason": "Direct fundamentals query to WebGPT",
                    "fallback_response": fallback_response,
                    "execution_time_seconds": round(execution_time, 2),
                    "timestamp": datetime.now().isoformat()
                }
                
        except Exception as e:
            logger.error("orchestrator.fundamentals_direct_error", error=str(e))
            
            return {
                "status": "error",
                "query": context.query,
                "intent": context.intent,
                "error": f"Failed to query WebGPT for fundamentals: {str(e)}",
                "fallback_triggered": True,
                "fallback_reason": "Direct fundamentals query to WebGPT",
                "execution_time_seconds": (datetime.now() - start_time).total_seconds(),
                "timestamp": datetime.now().isoformat()
            }
    
    async def _handle_no_workers(
        self, 
        context: DAGContext,
        start_time: datetime
    ) -> Dict[str, Any]:
        """Handle case when no workers are needed - triggers fallback"""
        
        logger.info("orchestrator.no_workers.fallback_start")
        
        print("\n⚠️  No workers needed for this query")
        fallback_system = get_fallback_system_type()
        print(f"🔄 Triggering {fallback_system} fallback...")
        
        # Always trigger fallback for no-worker scenarios
        if self.fallback_handler.is_available():
            try:
                fallback_response = await self.fallback_handler.answer_query(
                    context.query,
                    {}  # No worker results
                )
                
                execution_time = (datetime.now() - start_time).total_seconds()
                
                if fallback_response.get("status") == "success":
                    print(f"✅ {fallback_system} fallback completed successfully")
                    
                    return {
                        "status": "success",
                        "query": context.query,
                        "intent": context.intent,
                        "planner_confidence": context.confidence,
                        "worker_confidences": {},
                        "aggregate_confidence": 0.0,
                        "fallback_triggered": True,
                        "fallback_reason": "no_workers_needed",
                        "fallback_response": fallback_response,
                        "workers_executed": [],
                        "execution_time_seconds": round(execution_time, 2),
                        "results": {},
                        "timestamp": datetime.now().isoformat(),
                        "_context": context.to_dict()
                    }
                else:
                    logger.error("orchestrator.fallback.failed", error=fallback_response.get('message'))
                    return {
                        "status": "error",
                        "message": f"{fallback_system} fallback failed and no workers available",
                        "fallback_error": fallback_response.get('message'),
                        "query": context.query,
                        "intent": context.intent,
                        "_context": context.to_dict()
                    }
            except Exception as e:
                logger.error("orchestrator.fallback.exception", error=str(e))
                return {
                    "status": "error",
                    "message": f"{fallback_system} fallback error: {str(e)}",
                    "query": context.query,
                    "intent": context.intent,
                    "_context": context.to_dict()
                }
        else:
            logger.warning("orchestrator.fallback.unavailable")
            return {
                "status": "error",
                "message": f"No workers needed and {fallback_system} fallback not available",
                "intent": context.intent,
                "query": context.query,
                "_context": context.to_dict()
            }
    
    def _build_dag_context(self, planner_output: Dict[str, Any]) -> DAGContext:
        """Build DAGContext from planner output"""
        
        # Build timelock
        now = datetime.now()
        timelock = Timelock(
            as_of_date=now.strftime("%Y-%m-%d"),
            max_allowed_date=now.strftime("%Y-%m-%d")
        )
        
        # Determine domain
        intent = planner_output.get("intent", "NON_FINANCIAL")
        if intent in ["MACRO_DATA", "COMPANY_FUNDAMENTALS", "MARKET_PRICES", "NEWS_ANALYSIS", "MIXED"]:
            domain_hint = DomainType.FINANCIAL
        else:
            domain_hint = DomainType.NON_FINANCIAL
        
        # Extract required metrics (if specified)
        required_metrics = planner_output.get("metrics", [])
        
        return DAGContext(
            query=planner_output.get("query", ""),
            intent=intent,
            entities=planner_output.get("entities", []),
            timelock=timelock,
            domain_hint=domain_hint,
            required_metrics=required_metrics,
            confidence=planner_output.get("confidence", 0.5)
        )
    
    def _validate_context(self, context: DAGContext) -> None:
        """Validate DAGContext before execution"""
        
        # Check confidence threshold
        if context.confidence < 0.3:
            logger.warning(
                "orchestrator.low_confidence",
                confidence=context.confidence
            )
        
        # Validate timelock dates
        if context.timelock:
            try:
                as_of = datetime.strptime(context.timelock.as_of_date, "%Y-%m-%d")
                max_allowed = datetime.strptime(context.timelock.max_allowed_date, "%Y-%m-%d")
                
                if max_allowed < as_of:
                    raise TimelockViolationError(
                        message="max_allowed_date cannot be before as_of_date",
                        date_found=context.timelock.max_allowed_date,
                        max_allowed=context.timelock.as_of_date
                    )
            except ValueError as e:
                raise TimelockViolationError(
                    message=f"Invalid date format: {e}",
                    date_found="",
                    max_allowed=""
                )
    
    async def _execute_workers(
        self, 
        context: DAGContext, 
        workers_needed: List[str]
    ) -> Dict[str, Any]:
        """Execute workers in parallel"""
        
        tasks = []
        worker_names = []
        
        # Build tasks
        if "macro" in workers_needed:
            macro_plan = self._build_macro_plan(context)
            tasks.append(self.macro_worker.fetch(macro_plan))
            worker_names.append("MACRO")
        
        if "fundamentals_in" in workers_needed:
            intent_data = self._context_to_intent_data(context)
            tasks.append(self.fundamentals_worker.fetch(intent_data))
            worker_names.append("FUNDAMENTALS_IN")
        
        if "fundamentals_us" in workers_needed:
            intent_data = self._context_to_intent_data(context)
            tasks.append(self.us_fundamentals_worker.fetch(intent_data))
            worker_names.append("FUNDAMENTALS_US")
        
        if "prices" in workers_needed:
            intent_data = self._context_to_intent_data(context)
            tasks.append(self.prices_worker.fetch(intent_data))
            worker_names.append("PRICES")
        
        if "news" in workers_needed:
            tasks.append(self.news_worker.fetch(context))
            worker_names.append("NEWS")
        
        logger.info(
            "orchestrator.workers.start",
            workers=worker_names,
            count=len(tasks)
        )
        
        # Execute concurrently
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Process results
        worker_results = {}
        for name, result in zip(worker_names, results):
            if isinstance(result, Exception):
                logger.error(
                    "orchestrator.worker.failed",
                    worker=name,
                    error=str(result)
                )
                worker_results[name] = {
                    "status": "error", 
                    "error": str(result)
                }
            else:
                logger.info(
                    "orchestrator.worker.complete",
                    worker=name,
                    status=result.get("status")
                )
                worker_results[name] = result
        
        return worker_results
    
    async def _analyze_news(
        self, 
        worker_results: Dict[str, Any], 
        context: DAGContext
    ) -> Dict[str, Any]:
        """Analyze news with full context"""
        
        news_result = worker_results.get("NEWS", {})
        
        if news_result.get("status") != "success":
            logger.info(
                "orchestrator.news_analysis.skip",
                reason=news_result.get("status")
            )
            return worker_results
        
        logger.info("orchestrator.news_analysis.start")
        
        try:
            loop = asyncio.get_event_loop()
            news_analysis = await loop.run_in_executor(
                None,
                self.news_analyzer.analyze,
                news_result,
                context
            )
            
            analysis_status = news_analysis.get("status")
            
            logger.info(
                "orchestrator.news_analysis.complete",
                status=analysis_status
            )
            
            if analysis_status == "success":
                worker_results["NEWS_ANALYSIS"] = {
                    "status": "success",
                    **news_analysis.get("analysis", {}),
                    "_governance": news_analysis.get("_governance", {}),
                    "_sources": news_analysis.get("_sources", {})
                }
            else:
                worker_results["NEWS_ANALYSIS"] = {
                    "status": analysis_status,
                    "error": news_analysis.get("error", "Analysis failed")
                }
                
        except Exception as e:
            logger.error(
                "orchestrator.news_analysis.error",
                error=str(e)
            )
            worker_results["NEWS_ANALYSIS"] = {
                "status": "error",
                "error": str(e)
            }
        
        return worker_results
    
    def _final_governance_check(
        self, 
        worker_results: Dict[str, Any], 
        context: DAGContext
    ) -> str:
        """Final governance validation"""
        
        # Check quarantine
        quarantine_issues = self._check_quarantine(worker_results)
        if quarantine_issues:
            logger.warning(
                "orchestrator.governance.quarantine_detected",
                issues=quarantine_issues
            )
            return "APPROVED_WITH_WARNINGS"
        
        return "APPROVED"
    
    def _check_quarantine(self, worker_results: Dict[str, Any]) -> List[str]:
        """Check for quarantine issues"""
        
        issues = []
        
        news_analysis = worker_results.get("NEWS_ANALYSIS", {})
        governance = news_analysis.get("_governance", {})
        
        quarantine_status = governance.get("quarantine_status", "CLEAN")
        if quarantine_status != "CLEAN":
            issues.append(f"NEWS_ANALYSIS: {quarantine_status}")
        
        return issues
    
    def _build_macro_plan(self, context: DAGContext) -> Dict[str, Any]:
        """Build macro execution plan"""
        query_lower = context.query.lower()
        
        region = "US"
        if any(e.get("ticker", "").endswith(".NS") for e in context.entities):
            region = "IN"
        if "us" in query_lower or "fed" in query_lower:
            region = "US"
        
        indicators = []
        if "cpi" in query_lower or "inflation" in query_lower:
            indicators.append("inflation_headline")
        if "fed" in query_lower or "rate" in query_lower:
            indicators.append("policy_rate")
        if "bond" in query_lower or "yield" in query_lower:
            indicators.append("bond_10y")
        
        if not indicators:
            indicators = ["policy_rate", "inflation_headline"]
        
        return {
            "region": region,
            "indicators": list(set(indicators)),
            "time_range": {"scope": "latest"}
        }
    
    def _context_to_intent_data(self, context: DAGContext) -> Dict[str, Any]:
        """Convert DAGContext to legacy intent_data format"""
        return {
            "query": context.query,
            "intent": context.intent,
            "confidence": context.confidence,
            "entities": context.entities,
            "required_metrics": context.required_metrics
        }
    
    def _build_error_response(
        self, 
        error_type: str, 
        exception: Exception
    ) -> Dict[str, Any]:
        """Build standardized error response"""
        if hasattr(exception, 'to_dict'):
            return exception.to_dict()
        
        return {
            "status": "error",
            "error_type": error_type,
            "error": str(exception),
            "timestamp": datetime.now().isoformat()
        }
    
    def format_output(self, orchestration_result: Dict[str, Any]) -> str:
        """Format output for display"""
        
        lines = []
        lines.append("=" * 80)
        
        # Handle error case
        if 'error' in orchestration_result:
            lines.append(f"ERROR: {orchestration_result['error']}")
            if 'error_type' in orchestration_result:
                lines.append(f"Error Type: {orchestration_result['error_type']}")
            lines.append("=" * 80)
            return "\n".join(lines)
        
        # Normal case
        lines.append(f"QUERY: {orchestration_result.get('query', 'Unknown')}")
        lines.append(f"INTENT: {orchestration_result.get('intent', 'UNKNOWN')} (confidence: {orchestration_result.get('planner_confidence', 0):.2f})")
        lines.append(f"STATUS: {orchestration_result.get('status', 'UNKNOWN')}")
        
        # Show confidence breakdown
        if 'aggregate_confidence' in orchestration_result:
            lines.append(f"AGGREGATE CONFIDENCE: {orchestration_result['aggregate_confidence']:.2f}")
            worker_confs = orchestration_result.get('worker_confidences', {})
            if worker_confs:
                lines.append("WORKER CONFIDENCES:")
                for worker, conf in worker_confs.items():
                    lines.append(f"  - {worker}: {conf:.2f}")
        
        lines.append(f"EXECUTION TIME: {orchestration_result.get('execution_time_seconds', 0)}s")
        lines.append("=" * 80)
        lines.append("")
        
        # Show fallback info if triggered
        if orchestration_result.get('fallback_triggered'):
            lines.append("🔄 OPENAI FALLBACK TRIGGERED")
            lines.append(f"Reason: {orchestration_result.get('fallback_reason', 'Unknown')}")
            lines.append("=" * 80)
            lines.append("")
            
            fallback_resp = orchestration_result.get('fallback_response', {})
            if fallback_resp.get('status') == 'success':
                lines.append(fallback_resp.get('response', 'No response available'))
                lines.append("")
                lines.append(f"Model: {fallback_resp.get('model', 'N/A')}")
                lines.append(f"Data Source: {fallback_resp.get('data_source', 'N/A')}")
                lines.append(f"Searches: {fallback_resp.get('searches_performed', 0)}")
            else:
                lines.append(f"⚠️ Fallback failed: {fallback_resp.get('message', 'Unknown error')}")
            
            lines.append("")
            lines.append("=" * 80)
            lines.append("")
        
        # Show worker results if any
        results = orchestration_result.get('results', {})
        if results:
            lines.append("\nWORKER RESULTS:")
            for worker_name, worker_result in results.items():
                lines.append(f"\n{worker_name}: {worker_result.get('status', 'N/A')}")
        
        lines.append("\n" + "=" * 80)
        return "\n".join(lines)