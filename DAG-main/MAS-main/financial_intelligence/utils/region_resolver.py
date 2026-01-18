"""Region resolver utilities

Maps known ticker suffixes to regions and provides helpers to resolve
region from planner entities.
"""
from typing import List, Dict

REGION_BY_TICKER = {
    ".NS": "IN",
    ".BO": "IN",
    # Add more suffixes as needed
}


def resolve_region_from_entities(entities: List[Dict], query: str = "") -> str:
    """Derive region from planner entities (prefer tickers) and query keywords.

    Args:
        entities: List of entity dicts which may contain a `ticker` key.
        query: Query string for keyword-based region detection.

    Returns:
        Region code (e.g., 'IN', 'US'). Defaults to 'US'.
    """
    # First, try ticker-based detection
    for e in entities:
        ticker = (e.get("ticker") or "")
        for suffix, region in REGION_BY_TICKER.items():
            if ticker.endswith(suffix):
                return region

    # If no ticker match, try keyword-based detection
    query_lower = query.lower()
    
    # Indian indicators
    india_keywords = [
        "india", "indian", "reliance", "tcs", "infosys", "hdfc", "icici", "sbi", 
        "tata", "mahindra", "bajaj", "apollo", "l&t", "hul", "itc", "ashok leyland",
        "bharti airtel", "sun pharma", "dr reddy", "cipla", "lupin", "coal india",
        "ongc", "gail", "bpcl", "hpcl", "ntpc", "power grid", "rbi", "reserve bank",
        "nse", "bse", "screener", "crisil", "nifty", "sensex", "rupee", "inr"
    ]
    
    # Check if any Indian keywords are in the query
    if any(keyword in query_lower for keyword in india_keywords):
        return "IN"
    
    # US indicators
    us_keywords = [
        "us", "usa", "united states", "america", "american", "nyse", "nasdaq",
        "sec", "federal reserve", "fed", "dollar", "usd", "s&p 500", "dow jones",
        "apple", "microsoft", "google", "amazon", "tesla", "meta", "nvidia"
    ]
    
    if any(keyword in query_lower for keyword in us_keywords):
        return "US"
    
    # Default to US if no clear indicators
    return "US"
