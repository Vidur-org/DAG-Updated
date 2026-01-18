import json
from financial_intelligence.core.errors import PlannerError

REQUIRED_FIELDS = {"intent", "confidence", "reason"}

def validate_planner_output(text: str) -> dict:
    """Validate and normalize planner output"""
    
    # Clean markdown fences
    cleaned = text.replace("```json", "").replace("```", "").strip()

    try:
        parsed = json.loads(cleaned)
    except json.JSONDecodeError as e:
        raise PlannerError(f"Invalid JSON from planner: {e}")

    # Check required fields
    missing = REQUIRED_FIELDS - parsed.keys()
    if missing:
        raise PlannerError(f"Missing required fields: {missing}")
    
    # Normalize intent
    valid_intents = {
        "COMPANY_FUNDAMENTALS", 
        "MACRO_DATA", 
        "MARKET_PRICES", 
        "NEWS_ANALYSIS", 
        "MIXED", 
        "NON_FINANCIAL"
    }
    
    intent = parsed.get("intent", "").upper()
    if intent not in valid_intents:
        # Try to map legacy intents
        intent_mapping = {
            "INDIA_FUNDAMENTALS": "COMPANY_FUNDAMENTALS",
            "US_FUNDAMENTALS": "COMPANY_FUNDAMENTALS",
            "FUNDAMENTALS": "COMPANY_FUNDAMENTALS",
            "PRICES": "MARKET_PRICES",
            "NEWS": "NEWS_ANALYSIS",
            "MACRO": "MACRO_DATA"
        }
        intent = intent_mapping.get(intent, "NON_FINANCIAL")
        parsed["intent"] = intent
    
    # Ensure confidence is a float between 0 and 1
    try:
        confidence = float(parsed.get("confidence", 0.5))
        parsed["confidence"] = max(0.0, min(1.0, confidence))
    except (ValueError, TypeError):
        parsed["confidence"] = 0.5
    
    # Ensure entities is a list
    if "entities" not in parsed:
        parsed["entities"] = []
    elif not isinstance(parsed["entities"], list):
        parsed["entities"] = []
    
    # Normalize entities
    normalized_entities = []
    for entity in parsed.get("entities", []):
        if isinstance(entity, dict):
            company = entity.get("company", "")
            ticker = entity.get("ticker", "")
            
            # Auto-add .NS for Indian companies if missing
            if ticker and not ticker.endswith((".NS", ".BO")):
                # Check if it's likely an Indian company
                indian_tickers = ["RELIANCE", "TCS", "INFY", "HDFCBANK", "ICICIBANK", "SBIN", "ITC", "WIPRO"]
                if any(ticker.upper().startswith(t) for t in indian_tickers):
                    ticker = ticker + ".NS"
            
            if company or ticker:
                normalized_entities.append({
                    "company": company,
                    "ticker": ticker
                })
    
    parsed["entities"] = normalized_entities
    
    return parsed