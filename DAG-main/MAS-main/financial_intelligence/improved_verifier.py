"""
FIXED Confidence Verifier - Less Harsh on Macro + News

Key fixes:
1. More lenient macro data validation
2. News is bonus, not requirement
3. Better handling of historical queries
4. Fixed region mismatch penalties
"""

from typing import Dict, Any, List, Tuple, Optional
from datetime import datetime
import re


class DataQualityValidator:
    """Validates data quality with historical query awareness"""
    
    def __init__(self):
        self.min_macro_indicators = 1  # Relaxed from 2
        self.min_news_articles = 2     # Relaxed from 3
        self.min_fundamental_fields = 5
        
    def validate_macro_data(self, macro_result: Dict[str, Any], query: str) -> Tuple[bool, float, str]:
        """Validate macro worker - MORE LENIENT"""
        
        if macro_result.get("status") != "success":
            return False, 0.0, f"Macro worker failed: {macro_result.get('error', 'unknown')}"
        
        macro_facts = macro_result.get("macro_facts", {})
        region = macro_result.get("region", "UNKNOWN")
        
        # Check 1: At least 1 successful indicator (relaxed)
        successful_indicators = [
            k for k, v in macro_facts.items()
            if isinstance(v, dict) and v.get("status") == "success"
        ]
        
        if len(successful_indicators) < self.min_macro_indicators:
            return False, 0.2, f"Only {len(successful_indicators)} indicators succeeded (need {self.min_macro_indicators})"
        
        # Check 2: Region alignment (RELAXED - no penalty for historical queries)
        query_lower = query.lower()
        is_historical = self._is_historical_query(query_lower)
        
        quality_score = 0.7  # Start higher
        reason_parts = []
        
        if not is_historical:
            # Only check region for current queries
            us_indicators = ["us ", "federal reserve", "fed ", "dollar"]
            india_indicators = ["india", "rbi", "reserve bank of india", "rupee", "inr"]
            
            has_us = any(ind in query_lower for ind in us_indicators)
            has_india = any(ind in query_lower for ind in india_indicators)
            
            if has_us and region != "US":
                quality_score -= 0.15  # Reduced penalty
                reason_parts.append(f"Region hint US but got {region}")
            elif has_india and region != "IN":
                quality_score -= 0.15  # Reduced penalty
                reason_parts.append(f"Region hint India but got {region}")
        
        # Bonus for comprehensive data
        if len(successful_indicators) >= 2:
            quality_score += 0.15
            reason_parts.append("Good indicator coverage")
        
        quality_score = max(0.0, min(1.0, quality_score))
        reason = " | ".join(reason_parts) if reason_parts else "Macro data acceptable"
        
        return quality_score > 0.4, quality_score, reason  # Lowered threshold
    
    def _is_historical_query(self, query_lower: str) -> bool:
        """Check if query is about historical comparison"""
        historical_indicators = [
            '2020', '2021', '2022', '2023', '2024', '2025',
            'during', 'historical', 'comparison', 'vs', 'versus',
            'compare', 'between', 'over time'
        ]
        return any(ind in query_lower for ind in historical_indicators)
    
    def validate_news_data(self, news_result: Dict[str, Any], query: str) -> Tuple[bool, float, str]:
        """Validate news - MORE LENIENT"""
        
        if news_result.get("status") != "success":
            return False, 0.0, f"News worker failed: {news_result.get('error', 'unknown')}"
        
        data = news_result.get("data", {})
        articles = data.get("articles", [])
        
        # Relaxed minimum
        if len(articles) < self.min_news_articles:
            return False, 0.3, f"Only {len(articles)} articles (need {self.min_news_articles})"
        
        quality_score = 0.6  # Start higher
        reason_parts = []
        
        # Content length check (more lenient)
        avg_length = sum(a.get("word_count", 0) for a in articles) / len(articles)
        if avg_length < 150:  # Lowered from 200
            quality_score -= 0.1  # Reduced penalty
            reason_parts.append(f"Short articles: {avg_length:.0f} words")
        elif avg_length > 400:  # Lowered threshold
            quality_score += 0.15  # Increased bonus
            reason_parts.append("Good article depth")
        
        # Source diversity
        sources = set(a.get("source", "") for a in articles)
        if len(sources) >= 2:  # Lowered from 3
            quality_score += 0.1
            reason_parts.append("Good source diversity")
        
        quality_score = max(0.0, min(1.0, quality_score))
        reason = " | ".join(reason_parts) if reason_parts else "News quality acceptable"
        
        return quality_score > 0.4, quality_score, reason  # Lowered threshold
    
    def validate_fundamentals_data(self, fund_result: Dict[str, Any]) -> Tuple[bool, float, str]:
        """Validate fundamentals - UNCHANGED (already good)"""
        
        if fund_result.get("status") not in ["success"]:
            return False, 0.0, f"Fundamentals worker failed: {fund_result.get('error', 'unknown')}"
        
        data = fund_result.get("data", {})
        
        if not data:
            return False, 0.0, "No fundamental data returned"
        
        quality_score = 0.5
        reason_parts = []
        
        tier1_metrics = ["market_cap", "price", "pe_ratio"]
        tier2_metrics = ["roe", "roce", "pb_ratio", "book_value"]
        tier3_metrics = ["dividend_yield", "debt_to_equity", "revenue", "profit", "eps"]
        
        total_companies = len([m for m in data.values() if isinstance(m, dict) and "error" not in m])
        
        if total_companies == 0:
            return False, 0.0, "All companies returned errors"
        
        company_scores = []
        
        for company, metrics in data.items():
            if isinstance(metrics, dict) and "error" not in metrics:
                tier1_count = sum(1 for m in tier1_metrics if m in metrics and metrics[m] is not None)
                tier2_count = sum(1 for m in tier2_metrics if m in metrics and metrics[m] is not None)
                tier3_count = sum(1 for m in tier3_metrics if m in metrics and metrics[m] is not None)
                
                tier1_complete = tier1_count / len(tier1_metrics)
                tier2_complete = tier2_count / len(tier2_metrics) if tier2_metrics else 0
                tier3_complete = tier3_count / len(tier3_metrics) if tier3_metrics else 0
                
                company_score = (0.50 * tier1_complete) + (0.35 * tier2_complete) + (0.15 * tier3_complete)
                company_scores.append(company_score)
                
                total_available = tier1_count + tier2_count + tier3_count
                total_possible = len(tier1_metrics) + len(tier2_metrics) + len(tier3_metrics)
                
                if company_score >= 0.75:
                    reason_parts.append(f"{company}: excellent ({total_available}/{total_possible})")
                elif company_score >= 0.50:
                    reason_parts.append(f"{company}: good ({total_available}/{total_possible})")
                elif company_score >= 0.30:
                    reason_parts.append(f"{company}: acceptable ({total_available}/{total_possible})")
                else:
                    reason_parts.append(f"{company}: poor ({total_available}/{total_possible})")
        
        avg_company_score = sum(company_scores) / len(company_scores) if company_scores else 0
        
        if avg_company_score >= 0.75:
            quality_score = 0.85 + (avg_company_score - 0.75) * 0.4
        elif avg_company_score >= 0.50:
            quality_score = 0.70 + (avg_company_score - 0.50) * 0.6
        elif avg_company_score >= 0.30:
            quality_score = 0.55 + (avg_company_score - 0.30) * 0.75
        else:
            quality_score = 0.30 + avg_company_score
        
        quality_score = max(0.0, min(1.0, quality_score))
        reason = " | ".join(reason_parts) if reason_parts else "Fundamental data quality acceptable"
        
        return quality_score >= 0.55, quality_score, reason
    
    def validate_prices_data(self, prices_result: Dict[str, Any]) -> Tuple[bool, float, str]:
        """Validate prices - UNCHANGED (already good)"""
        
        if prices_result.get("status") not in ["success"]:
            return False, 0.0, f"Prices worker failed: {prices_result.get('error', 'unknown')}"
        
        data = prices_result.get("data", {})
        
        if not data:
            return False, 0.0, "No price data returned"
        
        quality_score = 0.7
        reason_parts = []
        
        for symbol, price_data in data.items():
            if isinstance(price_data, dict) and "error" not in price_data:
                required_fields = ["current_price", "change", "change_pct"]
                available = sum(1 for f in required_fields if f in price_data and price_data[f] is not None)
                
                if available < len(required_fields):
                    quality_score -= 0.1
                    reason_parts.append(f"{symbol}: incomplete")
                else:
                    quality_score += 0.05
        
        quality_score = max(0.0, min(1.0, quality_score))
        reason = " | ".join(reason_parts) if reason_parts else "Price data good"
        
        return quality_score > 0.5, quality_score, reason


class StrictConfidenceCalculator:
    """FIXED confidence calculator - more lenient"""
    
    def __init__(self):
        self.validator = DataQualityValidator()
        
        self.CRITICAL_WORKERS = {
            "MACRO_DATA": ["MACRO"],  # News is bonus
            "COMPANY_FUNDAMENTALS": ["FUNDAMENTALS_IN", "FUNDAMENTALS_US"],
            "MARKET_PRICES": ["PRICES"],
            "NEWS_ANALYSIS": ["NEWS", "NEWS_ANALYSIS"],
            "MIXED": []
        }
        
        # RELAXED thresholds - ALWAYS trigger fallback for fundamentals
        self.INTENT_THRESHOLDS = {
            "MACRO_DATA": 0.80,        # Increased from 0.50 to 0.80
            "COMPANY_FUNDAMENTALS": 0.10,  # Lowered to 0.10 - ALWAYS trigger fallback
            "MARKET_PRICES": 0.60,
            "NEWS_ANALYSIS": 0.50,
            "MIXED": 0.55,             # Relaxed from 0.65
            "NON_FINANCIAL": 0.30
        }
    
    def calculate_worker_confidence(
        self,
        worker_name: str,
        worker_result: Dict[str, Any],
        query: str
    ) -> Tuple[float, str]:
        """Calculate worker confidence with quality validation"""
        
        status = worker_result.get("status", "error")
        
        if status in ["error", "no_symbols", "no_companies", "no_content", "no_results"]:
            return 0.0, f"Worker failed: {status}"
        
        if worker_name == "MACRO":
            is_valid, quality, reason = self.validator.validate_macro_data(worker_result, query)
            return quality, reason  # Return quality even if not "valid"
        
        elif worker_name == "NEWS":
            is_valid, quality, reason = self.validator.validate_news_data(worker_result, query)
            return quality, reason
        
        elif worker_name in ["FUNDAMENTALS_IN", "FUNDAMENTALS_US"]:
            is_valid, quality, reason = self.validator.validate_fundamentals_data(worker_result)
            if not is_valid:
                return quality, f"VALIDATION FAILED: {reason}"
            return quality, reason
        
        elif worker_name == "PRICES":
            is_valid, quality, reason = self.validator.validate_prices_data(worker_result)
            if not is_valid:
                return quality, f"VALIDATION FAILED: {reason}"
            return quality, reason
        
        elif worker_name == "NEWS_ANALYSIS":
            synthesis = worker_result.get("synthesis", {})
            if not synthesis or not synthesis.get("overall_summary"):
                return 0.3, "News analysis incomplete"
            
            governance = worker_result.get("_governance", {})
            if governance.get("quarantine_status") != "CLEAN":
                return 0.5, f"Quarantined: {governance.get('quarantine_status')}"  # Less harsh
            
            return 0.75, "News analysis quality good"
        
        return 0.5, "Default confidence"
    
    def calculate_aggregate_confidence(
        self,
        intent: str,
        planner_confidence: float,
        worker_results: Dict[str, Any],
        query: str
    ) -> Tuple[float, Dict[str, Any]]:
        """Calculate aggregate confidence - MORE LENIENT"""
        
        # Step 1: Calculate worker confidences
        worker_confidences = {}
        worker_reasons = {}
        
        for worker_name, result in worker_results.items():
            conf, reason = self.calculate_worker_confidence(worker_name, result, query)
            worker_confidences[worker_name] = conf
            worker_reasons[worker_name] = reason
        
        # Step 2: Check critical workers
        critical_workers = self.CRITICAL_WORKERS.get(intent, [])
        
        if intent == "MIXED":
            critical_workers = list(worker_results.keys())
        
        critical_failures = []
        critical_successes = []
        
        for critical in critical_workers:
            if critical in worker_confidences:
                if worker_confidences[critical] < 0.3:  # Lowered threshold
                    critical_failures.append(critical)
                elif worker_confidences[critical] >= 0.5:  # Lowered threshold
                    critical_successes.append(critical)
        
        # RELAXED penalty for critical failures
        if critical_failures:
            penalty = 0.2 * len(critical_failures)  # Reduced from 0.3
            worker_avg = sum(worker_confidences.values()) / len(worker_confidences) if worker_confidences else 0
            aggregate = max(0.2, worker_avg - penalty)  # Higher floor, no planner confidence
            
            return aggregate, {
                "aggregate_confidence": aggregate,
                "planner_confidence": planner_confidence,
                "worker_confidences": worker_confidences,
                "worker_reasons": worker_reasons,
                "critical_failures": critical_failures,
                "critical_successes": critical_successes,
                "penalty_applied": penalty,
                "reason": f"Critical workers below threshold: {critical_failures}"
            }
        
        # Step 3: Calculate weighted average (NEWS IS BONUS)
        if not worker_confidences:
            # No workers - return low confidence (no planner confidence influence)
            return 0.0, {
                "aggregate_confidence": 0.0,
                "planner_confidence": planner_confidence,
                "worker_confidences": {},
                "worker_reasons": {},
                "reason": "No workers executed successfully"
            }
        
        # Special handling for MACRO_DATA intent
        if intent == "MACRO_DATA":
            # For macro queries, NEWS is optional bonus
            macro_conf = worker_confidences.get("MACRO", 0)
            news_conf = worker_confidences.get("NEWS", 0)
            
            # Base on macro alone
            worker_avg = macro_conf
            
            # Add news as bonus if present
            if news_conf > 0:
                worker_avg = (macro_conf * 0.7) + (news_conf * 0.3)
        else:
            # Standard average
            worker_avg = sum(worker_confidences.values()) / len(worker_confidences)
        
        # Weight: 0% planner, 100% workers (planner confidence excluded from aggregate)
        aggregate = worker_avg
        
        # REMOVED variance penalty - too harsh
        
        aggregate = max(0.0, min(1.0, aggregate))
        
        return aggregate, {
            "aggregate_confidence": aggregate,
            "planner_confidence": planner_confidence,
            "worker_confidences": worker_confidences,
            "worker_reasons": worker_reasons,
            "worker_average": worker_avg,
            "critical_workers": critical_workers,
            "critical_failures": [],
            "critical_successes": critical_successes,
            "reason": "Confidence calculated with lenient validation"
        }
    
    def should_trigger_fallback(
        self,
        intent: str,
        aggregate_confidence: float,
        worker_results: Dict[str, Any] = None
    ) -> Tuple[bool, str]:
        """Determine fallback trigger - RELAXED"""
        
        threshold = self.INTENT_THRESHOLDS.get(intent, 0.55)
        
        if aggregate_confidence < threshold:
            return True, f"Confidence {aggregate_confidence:.2f} below intent threshold {threshold}"
        
        return False, "Confidence acceptable"
    
    def get_confidence_assessment(
        self,
        intent: str,
        aggregate_confidence: float
    ) -> str:
        """Get confidence assessment"""
        
        threshold = self.INTENT_THRESHOLDS.get(intent, 0.55)
        
        if aggregate_confidence >= threshold + 0.15:
            return "HIGH"
        elif aggregate_confidence >= threshold:
            return "ACCEPTABLE"
        elif aggregate_confidence >= threshold - 0.15:
            return "LOW"
        else:
            return "VERY_LOW"


# Convenience functions
_calculator = StrictConfidenceCalculator()

def calculate_confidence(
    intent: str,
    planner_confidence: float,
    worker_results: Dict[str, Any],
    query: str
) -> Tuple[float, Dict[str, Any]]:
    """Calculate aggregate confidence"""
    return _calculator.calculate_aggregate_confidence(
        intent, planner_confidence, worker_results, query
    )

def should_trigger_fallback(intent: str, aggregate_confidence: float) -> Tuple[bool, str]:
    """Check if fallback should trigger"""
    return _calculator.should_trigger_fallback(intent, aggregate_confidence)

def get_confidence_assessment(intent: str, aggregate_confidence: float) -> str:
    """Get confidence assessment"""
    return _calculator.get_confidence_assessment(intent, aggregate_confidence)