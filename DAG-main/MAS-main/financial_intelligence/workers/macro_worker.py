"""
Enhanced Macro Worker with Critical Fixes

Key improvements:
1. Fixed GDP YoY calculation (quarterly vs monthly)
2. Metric-specific trend thresholds
3. Region validation guard
4. Historical time range support
5. Event-year compatibility check
6. Enhanced confidence scoring
"""
import os
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from enum import Enum

import pandas as pd
from fredapi import Fred


# ============================
# METRIC SPECIFICATIONS
# ============================

class MeasureType(Enum):
    """How to interpret a time series"""
    LEVEL = "level"              # Use as-is (rates, yields)
    YOY = "yoy"                  # Year-over-year % change
    QOQ = "qoq"                  # Quarter-over-quarter % change
    MOM = "mom"                  # Month-over-month % change
    TREND = "trend"              # Direction over period


class Frequency(Enum):
    """Data release frequency"""
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    ANNUAL = "annual"


class TrendDirection(Enum):
    """Directional assessment"""
    ACCELERATING = "accelerating"
    STABLE = "stable"
    SLOWING = "slowing"
    CONTRACTING = "contracting"
    UNKNOWN = "unknown"


class Confidence(Enum):
    """Confidence in assessment"""
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


METRIC_SPECS = {
    "policy_rate": {
        "concept": "Central bank policy stance",
        "measure": MeasureType.LEVEL,
        "frequency": Frequency.MONTHLY,
        "unit": "percent",
        "trend_thresholds": {
            "accelerating": 0.05,
            "slowing": -0.05
        },
        "series": {
            "US": {"source": "FRED", "id": "FEDFUNDS"},
            "IN": {"source": "RBI", "id": "REPO_RATE"}
        }
    },
    
    "inflation_headline": {
        "concept": "Consumer price inflation",
        "measure": MeasureType.YOY,
        "frequency": Frequency.MONTHLY,
        "unit": "percent",
        "trend_thresholds": {
            "accelerating": 0.3,
            "slowing": -0.3
        },
        "series": {
            "US": {"source": "FRED", "id": "CPIAUCSL"},
            "IN": {"source": "FRED", "id": "INDCPIALLMINMEI"}
        }
    },
    
    "inflation_core": {
        "concept": "Core inflation (ex food & energy)",
        "measure": MeasureType.YOY,
        "frequency": Frequency.MONTHLY,
        "unit": "percent",
        "trend_thresholds": {
            "accelerating": 0.3,
            "slowing": -0.3
        },
        "series": {
            "US": {"source": "FRED", "id": "CPILFESL"}
        }
    },
    
    "growth": {
        "concept": "Real GDP growth",
        "measure": MeasureType.YOY,
        "frequency": Frequency.QUARTERLY,
        "unit": "percent",
        "trend_thresholds": {
            "accelerating": 0.7,
            "slowing": -0.7
        },
        "series": {
            "US": {"source": "FRED", "id": "GDP"},
            "IN": {"source": "FRED", "id": "MKTGDPINA646NWDB"}
        }
    },
    
    "bond_10y": {
        "concept": "10-year government bond yield",
        "measure": MeasureType.LEVEL,
        "frequency": Frequency.DAILY,
        "unit": "percent",
        "trend_thresholds": {
            "accelerating": 0.1,
            "slowing": -0.1
        },
        "series": {
            "US": {"source": "FRED", "id": "DGS10"}
        }
    },
    
    "liquidity_growth": {
        "concept": "Broad money supply growth",
        "measure": MeasureType.YOY,
        "frequency": Frequency.MONTHLY,
        "unit": "percent",
        "trend_thresholds": {
            "accelerating": 0.5,
            "slowing": -0.5
        },
        "series": {
            "US": {"source": "FRED", "id": "M2SL"},
            "IN": {"source": "RBI", "id": "M3"}
        }
    }
}


# ============================
# MACRO WORKER V2.1
# ============================

class MacroWorker:
    """
    Professional-grade macro data engine.
    
    Fixed issues:
    - GDP YoY now uses correct period (4 quarters, not 12 months)
    - Metric-specific trend thresholds
    - Region validation
    - Historical time range support
    - Event-year compatibility checks
    - Enhanced confidence scoring
    """

    SUPPORTED_REGIONS = {"US", "IN"}

    def __init__(self):
        api_key = os.getenv("FRED_API_KEY")
        if not api_key:
            print("⚠️  FRED_API_KEY not set - macro data will be limited")
        self.fred = Fred(api_key=api_key) if api_key else None

    # ----------------------------
    # ENTRY POINT
    # ----------------------------

    async def fetch(self, macro_plan: Dict[str, Any]) -> Dict[str, Any]:
        """
        Fetch and analyze macro indicators.
        
        Returns structured data with clear separation:
        - macro_facts: Raw data and computed metrics
        - macro_state: Interpretive signals
        - limitations: What we can't answer
        """
        
        region = macro_plan["region"]
        indicators = macro_plan["indicators"]
        time_range = macro_plan.get("time_range", {"scope": "latest"})
        query = macro_plan.get("query", "")
        
        # GUARD: Validate region
        if region not in self.SUPPORTED_REGIONS:
            return {
                "status": "error",
                "worker": "MACRO",
                "error": f"Unsupported region: {region}. Supported: {self.SUPPORTED_REGIONS}",
                "timestamp": datetime.now().isoformat()
            }
        
        # GUARD: Check event-year compatibility if specified
        event_year = macro_plan.get("event_year")
        if event_year:
            current_year = datetime.now().year
            if abs(current_year - event_year) > 2:
                # Historical query - validate time range
                if time_range.get("scope") == "latest":
                    return {
                        "status": "out_of_scope",
                        "worker": "MACRO",
                        "error": f"Query asks about {event_year} but time_range is 'latest'",
                        "recommendation": "Use historical time range",
                        "timestamp": datetime.now().isoformat()
                    }
        
        # Fetch raw data
        macro_facts = {}
        
        for indicator in indicators:
            try:
                fact = await self._fetch_and_analyze_indicator(
                    indicator, 
                    region, 
                    time_range,
                    event_year
                )
                macro_facts[indicator] = fact
            except Exception as e:
                macro_facts[indicator] = {
                    "status": "error",
                    "error": str(e)
                }
        
        # Compute derived state
        macro_state = self._compute_macro_state(macro_facts, region)
        
        # Identify limitations
        limitations = self._identify_limitations(macro_plan, macro_facts)
        
        # Compute overall confidence
        confidence = self._compute_confidence(
            macro_facts, 
            region, 
            query, 
            event_year
        )
        
        return {
            "status": "success",
            "worker": "MACRO",
            "region": region,
            "confidence": confidence,
            "macro_facts": macro_facts,
            "macro_state": macro_state,
            "limitations": limitations,
            "timestamp": datetime.now().isoformat()
        }

    # ----------------------------
    # DATA FETCHING & ANALYSIS
    # ----------------------------

    async def _fetch_and_analyze_indicator(
        self, 
        indicator: str, 
        region: str,
        time_range: Dict[str, Any],
        event_year: Optional[int] = None
    ) -> Dict[str, Any]:
        """Fetch and analyze a single indicator with metric-aware logic"""
        
        # Get metric spec
        spec = METRIC_SPECS.get(indicator)
        if not spec:
            return {"status": "error", "error": "Unknown indicator"}
        
        series_config = spec["series"].get(region)
        if not series_config:
            return {
                "status": "unavailable",
                "reason": f"{indicator} not available for {region}"
            }
        
        # Fetch series
        if series_config["source"] == "FRED":
            if not self.fred:
                return {"status": "error", "error": "FRED API key not configured"}
            
            series = await self._fetch_fred_series(
                series_config["id"],
                time_range,
                spec["frequency"],
                event_year
            )
        else:
            return {
                "status": "not_implemented",
                "reason": f"{series_config['source']} adapter not yet implemented"
            }
        
        if series is None or series.empty:
            return {"status": "error", "error": "No data returned"}
        
        # GUARD: Event-year alignment check
        if event_year:
            data_year = series.index[-1].year
            if abs(data_year - event_year) > 2:
                return {
                    "status": "temporal_mismatch",
                    "error": f"Data ends in {data_year}, query asks about {event_year}",
                    "data_year": data_year,
                    "event_year": event_year
                }
        
        # Analyze with metric-aware logic
        analysis = self._analyze_metric(series, spec)
        
        return {
            "status": "success",
            "concept": spec["concept"],
            "latest_date": series.index[-1].strftime("%Y-%m-%d"),
            "frequency": spec["frequency"].value,
            **analysis
        }

    async def _fetch_fred_series(
        self,
        series_id: str,
        time_range: Dict[str, Any],
        frequency: Frequency,
        event_year: Optional[int] = None
    ) -> Optional[pd.Series]:
        """Fetch data from FRED with appropriate lookback"""
        
        scope = time_range["scope"]
        
        if scope == "historical" and "from" in time_range:
            # Historical query with explicit dates
            start = datetime.strptime(time_range["from"], "%Y-%m")
            end = datetime.strptime(time_range["to"], "%Y-%m") if "to" in time_range else datetime.now()
        
        elif event_year:
            # Event-based query
            start = datetime(event_year - 2, 1, 1)
            end = datetime(event_year + 2, 12, 31)
        
        else:
            # Latest data
            end = datetime.now()
            
            # Determine lookback based on frequency
            if frequency == Frequency.QUARTERLY:
                start = end - timedelta(days=730)  # 2 years
            elif frequency == Frequency.MONTHLY:
                start = end - timedelta(days=545)  # 18 months
            else:
                start = end - timedelta(days=365)  # 1 year
        
        try:
            series = self.fred.get_series(
                series_id,
                observation_start=start,
                observation_end=end
            )
            return series.dropna()
        except Exception as e:
            print(f"FRED error for {series_id}: {e}")
            return None

    # ----------------------------
    # METRIC-AWARE ANALYSIS
    # ----------------------------

    def _analyze_metric(
        self, 
        series: pd.Series, 
        spec: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Analyze series according to its measure type.
        
        This is the KEY fix - no more one-size-fits-all.
        """
        
        measure = spec["measure"]
        unit = spec["unit"]
        thresholds = spec.get("trend_thresholds", {
            "accelerating": 0.3,
            "slowing": -0.3
        })
        
        if measure == MeasureType.LEVEL:
            return self._analyze_level(series, unit, thresholds)
        
        elif measure == MeasureType.YOY:
            return self._analyze_yoy(series, unit, thresholds, spec["frequency"])
        
        elif measure == MeasureType.QOQ:
            return self._analyze_qoq(series, unit)
        
        else:
            return {"error": f"Unsupported measure type: {measure}"}

    def _analyze_level(
        self, 
        series: pd.Series, 
        unit: str,
        thresholds: Dict[str, float]
    ) -> Dict[str, Any]:
        """Analyze level data (rates, yields)"""
        
        latest = series.iloc[-1]
        
        # Recent change (3 months)
        if len(series) >= 3:
            three_months_ago = series.iloc[-4] if len(series) >= 4 else series.iloc[0]
            change_3m = latest - three_months_ago
        else:
            change_3m = 0
        
        # Trend direction (using metric-specific thresholds)
        if len(series) >= 6:
            recent_trend = series.iloc[-6:].diff().mean()
            accel_threshold = thresholds.get("accelerating", 0.05)
            slow_threshold = thresholds.get("slowing", -0.05)
            
            if recent_trend > accel_threshold:
                trend = TrendDirection.ACCELERATING
            elif recent_trend < slow_threshold:
                trend = TrendDirection.SLOWING
            else:
                trend = TrendDirection.STABLE
        else:
            trend = TrendDirection.UNKNOWN
        
        return {
            "latest_value": round(float(latest), 2),
            "change_3m": round(float(change_3m), 2),
            "trend": trend.value,
            "unit": unit
        }

    def _analyze_yoy(
        self, 
        series: pd.Series, 
        unit: str,
        thresholds: Dict[str, float],
        frequency: Frequency
    ) -> Dict[str, Any]:
        """
        Analyze YoY growth data (inflation, GDP growth)
        
        CRITICAL FIX: Use correct period for YoY calculation
        - Quarterly data: 4 periods
        - Monthly data: 12 periods
        """
        
        # Compute YoY with frequency-aware period
        if frequency == Frequency.QUARTERLY:
            if len(series) < 5:
                return {"error": "Insufficient data for quarterly YoY (need 5+ quarters)"}
            yoy_series = series.pct_change(4) * 100
        else:
            # Monthly or other frequencies
            if len(series) < 13:
                return {"error": "Insufficient data for YoY (need 13+ periods)"}
            yoy_series = series.pct_change(12) * 100
        
        yoy_series = yoy_series.dropna()
        
        if yoy_series.empty:
            return {"error": "Unable to compute YoY"}
        
        latest_yoy = yoy_series.iloc[-1]
        
        # Trend in YoY (is inflation accelerating or decelerating?)
        if len(yoy_series) >= 3:
            prev_yoy = yoy_series.iloc[-4] if len(yoy_series) >= 4 else yoy_series.iloc[-2]
            yoy_change = latest_yoy - prev_yoy
            
            # Use metric-specific thresholds
            accel_threshold = thresholds.get("accelerating", 0.3)
            slow_threshold = thresholds.get("slowing", -0.3)
            
            if yoy_change > accel_threshold:
                trend = TrendDirection.ACCELERATING
            elif yoy_change < slow_threshold:
                trend = TrendDirection.SLOWING
            else:
                trend = TrendDirection.STABLE
        else:
            trend = TrendDirection.UNKNOWN
            yoy_change = None
        
        return {
            "latest_yoy": round(float(latest_yoy), 2),
            "yoy_change": round(float(yoy_change), 2) if yoy_change is not None else None,
            "trend": trend.value,
            "unit": unit
        }

    def _analyze_qoq(self, series: pd.Series, unit: str) -> Dict[str, Any]:
        """Analyze QoQ growth data"""
        
        if len(series) < 2:
            return {"error": "Insufficient data for QoQ calculation"}
        
        qoq_series = series.pct_change(1) * 100
        qoq_series = qoq_series.dropna()
        
        latest_qoq = qoq_series.iloc[-1]
        
        return {
            "latest_qoq": round(float(latest_qoq), 2),
            "unit": unit
        }

    # ----------------------------
    # MACRO STATE COMPUTATION
    # ----------------------------

    def _compute_macro_state(
        self, 
        macro_facts: Dict[str, Any],
        region: str
    ) -> Dict[str, Any]:
        """
        Compute interpretive macro state.
        
        This replaces hardcoded regime labels with dimensional assessment.
        """
        
        state = {}
        
        # Real rates (if we have both policy rate and inflation)
        policy = macro_facts.get("policy_rate", {})
        inflation = macro_facts.get("inflation_headline", {})
        
        if policy.get("status") == "success" and inflation.get("status") == "success":
            policy_rate = policy.get("latest_value", 0)
            inflation_yoy = inflation.get("latest_yoy", 0)
            
            if policy_rate and inflation_yoy:
                real_rate = policy_rate - inflation_yoy
                
                if real_rate > 1.0:
                    stance = "restrictive"
                    confidence = Confidence.HIGH
                elif real_rate > 0:
                    stance = "neutral_tight"
                    confidence = Confidence.MEDIUM
                elif real_rate > -1.0:
                    stance = "neutral_loose"
                    confidence = Confidence.MEDIUM
                else:
                    stance = "accommodative"
                    confidence = Confidence.HIGH
                
                state["real_rates"] = {
                    "value": round(real_rate, 2),
                    "stance": stance,
                    "confidence": confidence.value,
                    "unit": "percent"
                }
        
        # Growth assessment
        growth = macro_facts.get("growth", {})
        if growth.get("status") == "success":
            growth_yoy = growth.get("latest_yoy")
            growth_trend = growth.get("trend")
            
            if growth_yoy is not None:
                state["growth_state"] = {
                    "latest_yoy": growth_yoy,
                    "trend": growth_trend,
                    "confidence": Confidence.MEDIUM.value
                }
        
        # Inflation assessment
        if inflation.get("status") == "success":
            inflation_trend = inflation.get("trend")
            
            state["inflation_state"] = {
                "latest_yoy": inflation.get("latest_yoy"),
                "trend": inflation_trend,
                "confidence": Confidence.HIGH.value if inflation_trend != "unknown" else Confidence.LOW.value
            }
        
        return state

    # ----------------------------
    # CONFIDENCE SCORING
    # ----------------------------

    def _compute_confidence(
        self,
        macro_facts: Dict[str, Any],
        region: str,
        query: str,
        event_year: Optional[int]
    ) -> float:
        """
        Compute overall confidence score for this macro response.
        
        HIGH confidence only if:
        - All requested metrics fetched
        - Region matches
        - Time range aligns with query
        """
        
        confidence = 1.0
        
        # Penalize for missing data
        success_count = sum(
            1 for fact in macro_facts.values()
            if fact.get("status") == "success"
        )
        total_count = len(macro_facts)
        
        if total_count > 0:
            data_completeness = success_count / total_count
            confidence *= data_completeness
        else:
            confidence = 0.3
        
        # Penalize for temporal mismatches
        if event_year:
            current_year = datetime.now().year
            if abs(current_year - event_year) > 2:
                confidence *= 0.7  # Historical queries are less certain
        
        # Check for region alignment
        query_lower = query.lower()
        if region == "IN" and "us" in query_lower and "india" not in query_lower:
            confidence *= 0.6  # Possible region mismatch
        elif region == "US" and "india" in query_lower and "us" not in query_lower:
            confidence *= 0.6
        
        return round(confidence, 2)

    # ----------------------------
    # LIMITATIONS
    # ----------------------------

    def _identify_limitations(
        self, 
        macro_plan: Dict[str, Any],
        macro_facts: Dict[str, Any]
    ) -> List[str]:
        """
        Explicitly state what we cannot answer.
        
        This builds trust and prevents false confidence.
        """
        
        limitations = []
        
        # Check for missing data
        for indicator in macro_plan["indicators"]:
            fact = macro_facts.get(indicator, {})
            if fact.get("status") != "success":
                error = fact.get("error", fact.get("reason", "unknown reason"))
                limitations.append(
                    f"Unable to fetch {indicator}: {error}"
                )
        
        # Forward-looking queries
        query_lower = macro_plan.get("query", "").lower()
        
        if any(word in query_lower for word in ["will", "next", "future", "expect", "forecast"]):
            limitations.append(
                "This query requires forward-looking expectations. "
                "Official macro data is backward-looking. "
                "Consider market-implied expectations (futures, surveys, Fed dot plot)."
            )
        
        # Granular timing
        if any(word in query_lower for word in ["today", "this week", "tomorrow"]):
            limitations.append(
                "Macro indicators are released monthly/quarterly with lag. "
                "Real-time intraday signals not available from official sources."
            )
        
        # Regional limitations
        region = macro_plan.get("region")
        if region == "IN":
            limitations.append(
                "India macro data primarily from FRED (international sources). "
                "Direct RBI adapter not yet implemented for real-time policy updates."
            )
        
        return limitations