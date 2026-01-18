"""Enhanced Main Entry Point with OpenAI Fallback Support

Features:
- Structured logging with structlog
- Full governance pipeline
- OpenAI fallback integration
- Enhanced error handling
- Result persistence
"""
import asyncio
import json
import sys
import structlog
from datetime import datetime

from financial_intelligence.planner.planner_llm import invoke_planner_llm
from financial_intelligence.planner.validator import validate_planner_output
from financial_intelligence.orchestrator import ParallelOrchestrator
from financial_intelligence.utils.entity_resolver import resolve_entities
from financial_intelligence.config import AGGREGATE_CONFIDENCE_THRESHOLD

# Configure structured logging
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.processors.JSONRenderer()
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger()
# final=[]

async def run_financial_system(input_query: str):
    """Enhanced main with full governance and OpenAI fallback"""
    
    print("\n" + "=" * 80)
    print("FINANCIAL INTELLIGENCE SYSTEM V2.0 - WITH GOVERNANCE & FALLBACK")
    print("=" * 80 + "\n")
    
    query = input_query.strip()
    
    if not query:
        print("Empty query. Exiting.")
        return
    
    session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    logger.info(
        "session.start",
        session_id=session_id,
        query=query[:100]
    )
    
    try:
        # =============================================================
        # STEP 1: Intent Classification
        # =============================================================
        print("\n📊 STEP 1: Intent Classification...")
        logger.info("step.intent_classification.start")
        
        raw_plan = invoke_planner_llm(query)
        print("\nRAW PLANNER OUTPUT:")
        print(raw_plan)
        
        plan = validate_planner_output(raw_plan)
        
        intent = plan.get('intent')
        confidence = plan.get('confidence')
        reason = plan.get('reason')
        
        print(f"\n✅ Intent: {intent}")
        print(f"   Confidence: {confidence:.2f}")
        print(f"   Reason: {reason}")
        
        logger.info(
            "step.intent_classification.complete",
            intent=intent,
            confidence=confidence
        )
        
        # Confidence gate
        if confidence is None or confidence < 0.3:
            logger.warning(
                "step.intent_classification.low_confidence",
                confidence=confidence
            )
            print("\n⚠️  Low confidence intent classification")
            print("🔍 Falling back to planner decomposition – no workers will be executed")
            return
        
        # =============================================================
        # STEP 2: Entity Resolution
        # =============================================================
        print("\n🔍 STEP 2: Entity Resolution...")
        logger.info("step.entity_resolution.start")
        
        entities = resolve_entities(query)
        
        if entities:
            print(f"✅ Resolved {len(entities)} entities:")
            for e in entities:
                print(f"   - {e['company']} ({e['ticker']}) [{e.get('region', 'UNKNOWN')}]")
            
            logger.info(
                "step.entity_resolution.complete",
                entities_count=len(entities),
                entities=[e['ticker'] for e in entities]
            )
        else:
            print("⚠️  No entities detected")
            logger.info("step.entity_resolution.complete", entities_count=0)
        
        # Attach entities to plan
        plan['entities'] = entities
        plan['query'] = query
        
        # =============================================================
        # STEP 3: Execute Workers with Governance + Fallback
        # =============================================================
        print(f"\n🔄 STEP 3: Executing workers for intent '{intent}'...")
        print(f"   Confidence threshold for fallback: {AGGREGATE_CONFIDENCE_THRESHOLD}")
        logger.info("step.worker_execution.start", intent=intent)
        
        orchestrator = ParallelOrchestrator()
        result = await orchestrator.execute(plan)
        
        logger.info(
            "step.worker_execution.complete",
            status=result.get("status"),
            workers=result.get("workers_executed", []),
            fallback_triggered=result.get("fallback_triggered", False)
        )
        
        # =============================================================
        # STEP 4: Display Results
        # =============================================================
        print("\n" + "=" * 80)
        print("RESULTS")
        print("=" * 80)
        
        # Show governance status
        final_status = result.get("status", "UNKNOWN")
        print(f"\n🔒 GOVERNANCE STATUS: {final_status}")
        
        if final_status == "BLOCKED":
            print("❌ Request blocked by governance checks")
            logger.error("session.blocked", reason=result.get("error", "Unknown"))
        elif final_status == "APPROVED_WITH_WARNINGS":
            print("⚠️  Request approved with warnings - review carefully")
            logger.warning("session.approved_with_warnings")
        else:
            print("✅ Request fully approved")
            logger.info("session.approved")
        
        # Show confidence breakdown
        print(f"\n📈 CONFIDENCE ANALYSIS:")
        print(f"   Planner Confidence: {result.get('planner_confidence', 0):.2f}")
        
        worker_confs = result.get('worker_confidences', {})
        if worker_confs:
            print(f"   Worker Confidences:")
            for worker, conf in worker_confs.items():
                emoji = "✅" if conf >= 0.6 else "⚠️" if conf >= 0.4 else "❌"
                print(f"      {emoji} {worker}: {conf:.2f}")
        
        aggregate = result.get('aggregate_confidence', 0)
        print(f"   Aggregate Confidence: {aggregate:.2f}")
        
        if aggregate < AGGREGATE_CONFIDENCE_THRESHOLD:
            print(f"   ⚠️  Below threshold ({AGGREGATE_CONFIDENCE_THRESHOLD})")
        
        # Show fallback status
        if result.get('fallback_triggered'):
            print(f"\n🔄 OPENAI FALLBACK:")
            print(f"   Triggered: YES")
            print(f"   Reason: {result.get('fallback_reason', 'Unknown')}")
            
            fallback_resp = result.get('fallback_response', {})
            if fallback_resp.get('status') == 'success':
                print(f"   Status: ✅ Success")
                print(f"   Model: {fallback_resp.get('model', 'N/A')}")
                print(f"   Tokens Used: {fallback_resp.get('tokens_used', 'N/A')}")
            else:
                print(f"   Status: ❌ Failed")
                print(f"   Error: {fallback_resp.get('message', 'Unknown')}")
        else:
            print(f"\n🔄 OPENAI FALLBACK: Not triggered")
        
        # Display formatted output
        print("\n" + "=" * 80)
        print("DETAILED OUTPUT")
        print("=" * 80)
        print(orchestrator.format_output(result))
        
        # =============================================================
        # STEP 5: Save Results
        # =============================================================
        output_file = 'last_run_results.json'
        final= json.dumps(result, indent=2)
        with open(output_file, 'w') as f:
            json.dump(result, f, indent=2)
        
        print(f"\n💾 Full results saved to '{output_file}'")
        
        logger.info(
            "session.complete",
            session_id=session_id,
            output_file=output_file,
            status=final_status,
            fallback_triggered=result.get('fallback_triggered', False)
        )
        
        # =============================================================
        # STEP 6: Display Governance Summary
        # =============================================================
        print("\n" + "=" * 80)
        print("GOVERNANCE SUMMARY")
        print("=" * 80)
        
        workers_executed = result.get("workers_executed", [])
        results_data = result.get("results", {})
        
        for worker in workers_executed:
            worker_result = results_data.get(worker, {})
            governance = worker_result.get("_governance", {})
            
            if governance:
                print(f"\n{worker}:")
                print(f"  Timelock Validated: {governance.get('timelock_validated', False)}")
                print(f"  Domain Purity: {governance.get('domain_purity_check', 'N/A')}")
                print(f"  Completeness: {governance.get('completeness_score', 0):.2%}")
                print(f"  Quarantine: {governance.get('quarantine_status', 'N/A')}")
        
        print("\n" + "=" * 80)
        
    except KeyboardInterrupt:
        logger.info("session.cancelled", session_id=session_id)
        print("\n\n⚠️  Session cancelled by user")
        sys.exit(0)
        
    except Exception as e:
        logger.error(
            "session.error",
            session_id=session_id,
            error=str(e),
            exc_info=True
        )
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
    return final


if __name__ == "__main__":
    asyncio.run(main())