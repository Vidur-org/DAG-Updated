import json
from groq import Groq
from financial_intelligence.config import GROQ_API_KEY, PLANNER_MODEL, PLANNER_TEMPERATURE

client = Groq(api_key=GROQ_API_KEY)

SYSTEM_PROMPT = """
You are a QUERY INTENT CLASSIFIER for a financial intelligence system.

YOUR ONLY TASK:
Classify the user's query into ONE of the following intents:

- MACRO_DATA
- COMPANY_FUNDAMENTALS
- ASSET_PRICES
- NEWS_ANALYSIS
- MIXED
- NON_FINANCIAL

STRICT RULES:
- Do NOT extract entities
- Do NOT infer tickers
- Do NOT suggest data sources
- Do NOT answer the query
- Do NOT include extra fields
- Output ONLY valid JSON
- Intent describes WHAT data is needed (not WHERE or region)
- Geography is irrelevant for intent classification

INTENT DEFINITIONS:

MACRO_DATA:
- GDP, CPI, inflation, interest rates, policy rates, FX rates, macro indicators
- Examples: "What is the current Fed rate?", "Show me India's GDP growth"

COMPANY_FUNDAMENTALS:
- Company valuation, earnings, margins, balance sheet metrics
- PE ratio, ROE, ROCE, debt ratios, revenue growth
- Geography is irrelevant here
- Examples: "Give me fundamentals of Apple", "What is Reliance's PE ratio?"

ASSET_PRICES:
- Stock prices, index prices, commodity prices, forex rates
- Price movements, volatility, technical analysis
- Examples: "What is Apple's stock price?", "Show me gold prices", "Nifty 50 today"

NEWS_ANALYSIS:
- Why, impact, outlook, causes, sentiment, events
- Market reactions to news
- Examples: "Why did Tesla stock fall?", "Impact of Fed decision on markets"

MIXED:
- Query explicitly requests TWO OR MORE of the above domains
- Keywords: "and", "along with", "both", "also", "as well as"
- Examples: 
  * "Give me stock prices AND fundamentals of MRF"
  * "Show me Apple's PE ratio and current stock price"
  * "What are macro indicators and their impact on markets?"

NON_FINANCIAL:
- Not related to financial data

CLASSIFICATION LOGIC:
- If query contains "and", "both", "along with" connecting different data types → MIXED
- If query asks ONLY about fundamentals → COMPANY_FUNDAMENTALS
- If query asks ONLY about prices → ASSET_PRICES
- If query asks about WHY/IMPACT/OUTLOOK → NEWS_ANALYSIS
- If query asks about macro indicators → MACRO_DATA

OUTPUT SCHEMA (STRICT):
{
  "intent": "string",
  "confidence": number,
  "reason": "string"
}

EXAMPLES:

Query: "give me details of stock prices and company fundamentals of mrf"
Output: {"intent": "MIXED", "confidence": 0.95, "reason": "Query explicitly requests both stock prices and company fundamentals"}

Query: "what is apple's pe ratio"
Output: {"intent": "COMPANY_FUNDAMENTALS", "confidence": 0.9, "reason": "Query asks for company valuation metric"}

Query: "show me nifty 50 today"
Output: {"intent": "ASSET_PRICES", "confidence": 0.9, "reason": "Query asks for index price"}

Query: "what is the current fed rate"
Output: {"intent": "MACRO_DATA", "confidence": 0.95, "reason": "Query asks for macro policy indicator"}
"""


def invoke_planner_llm(user_query: str) -> str:
    """Invoke planner with improved prompt and error handling"""
    
    try:
        response = client.chat.completions.create(
            model=PLANNER_MODEL,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_query}
            ],
            temperature=PLANNER_TEMPERATURE,
            max_tokens=500
        )

        content = response.choices[0].message.content.strip()
        
        # Clean markdown code fences
        cleaned = content.replace("```json", "").replace("```", "").strip()
        
        # Validate JSON
        try:
            parsed = json.loads(cleaned)
            
            # Ensure required fields
            if "intent" not in parsed:
                parsed["intent"] = "NON_FINANCIAL"
            if "confidence" not in parsed:
                parsed["confidence"] = 0.5
            if "reason" not in parsed:
                parsed["reason"] = "Classified based on query content"
            if "entities" not in parsed:
                parsed["entities"] = []
                
            return json.dumps(parsed)
            
        except json.JSONDecodeError:
            # Fallback with basic extraction
            return _create_fallback_response(user_query, cleaned)
            
    except Exception as e:
        print(f"Error calling Groq API: {e}")
        return _create_fallback_response(user_query, str(e))


def _create_fallback_response(query: str, error_detail: str) -> str:
    """Create a safe fallback response when LLM fails"""
    
    query_lower = query.lower()
    
    # Basic intent detection
    intent = "NON_FINANCIAL"
    confidence = 0.3
    entities = []
    
    # Check for company fundamentals keywords
    if any(word in query_lower for word in ["fundamental", "pe ratio", "roe", "roce", "balance sheet", "earnings", "revenue", "profit"]):
        intent = "COMPANY_FUNDAMENTALS"
        confidence = 0.6
        
    # Check for macro keywords
    elif any(word in query_lower for word in ["cpi", "inflation", "gdp", "interest rate", "fed", "rbi", "policy rate"]):
        intent = "MACRO_DATA"
        confidence = 0.6
        
    # Check for price keywords
    elif any(word in query_lower for word in ["price", "stock price", "trading", "nifty", "sensex"]):
        intent = "MARKET_PRICES"
        confidence = 0.6
        
    # Check for news keywords
    elif any(word in query_lower for word in ["news", "impact", "outlook", "why", "how will", "analysis"]):
        intent = "NEWS_ANALYSIS"
        confidence = 0.5
    
    # Basic entity extraction
    common_companies = {
        "reliance": {"company": "Reliance", "ticker": "RELIANCE.NS"},
        "tcs": {"company": "TCS", "ticker": "TCS.NS"},
        "infosys": {"company": "Infosys", "ticker": "INFY.NS"},
        "apple": {"company": "Apple", "ticker": "AAPL"},
        "microsoft": {"company": "Microsoft", "ticker": "MSFT"},
        "google": {"company": "Google", "ticker": "GOOGL"},
        "amazon": {"company": "Amazon", "ticker": "AMZN"},
        "tesla": {"company": "Tesla", "ticker": "TSLA"}
    }
    
    for name, entity in common_companies.items():
        if name in query_lower:
            entities.append(entity)
    
    return json.dumps({
        "intent": intent,
        "confidence": confidence,
        "reason": f"Fallback classification due to LLM error: {error_detail[:100]}",
        "entities": entities,
        "_fallback": True
    })