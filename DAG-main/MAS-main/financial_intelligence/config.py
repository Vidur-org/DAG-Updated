"""
Enhanced Configuration for Financial Intelligence System

Includes:
- API keys and credentials
- Model selection and parameters
- Confidence thresholds
- Fallback configuration
- Worker-specific settings
"""
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# ============================================================================
# API KEYS
# ============================================================================

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
SERPAPI_KEY = os.getenv("SERPAPI_KEY")
FRED_API_KEY = os.getenv("FRED_API_KEY")
POLYGON_API_KEY = os.getenv("POLYGON_API_KEY")
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")

# User agent for web scraping
USER_AGENT = os.getenv(
    "USER_AGENT",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
)

# ============================================================================
# LLM CONFIGURATION
# ============================================================================

# Primary LLM provider
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "groq")

# Planner model (intent classification)
PLANNER_MODEL = os.getenv("PLANNER_MODEL", "llama-3.1-8b-instant")
PLANNER_TEMPERATURE = float(os.getenv("PLANNER_TEMPERATURE", "0"))

# Worker model (data analysis)
WORKER_MODEL = os.getenv("WORKER_MODEL", "llama-3.1-8b-instant")
WORKER_TEMPERATURE = float(os.getenv("WORKER_TEMPERATURE", "0.3"))

# OpenAI fallback model
OPENAI_FALLBACK_MODEL = os.getenv("OPENAI_FALLBACK_MODEL", "gpt-4o-mini")
OPENAI_MAX_TOKENS = int(os.getenv("OPENAI_MAX_TOKENS", "1500"))
OPENAI_TEMPERATURE = float(os.getenv("OPENAI_TEMPERATURE", "0.7"))

# ============================================================================
# CONFIDENCE THRESHOLDS
# ============================================================================

# Minimum confidence to proceed without fallback
AGGREGATE_CONFIDENCE_THRESHOLD = float(os.getenv("CONFIDENCE_THRESHOLD", "0.65"))

# Minimum planner confidence (warn below this)
PLANNER_CONFIDENCE_WARNING = float(os.getenv("PLANNER_CONFIDENCE_WARNING", "0.3"))

# Worker-specific confidence thresholds
WORKER_CONFIDENCE_THRESHOLDS = {
    "PRICES": 0.6,
    "FUNDAMENTALS": 0.5,
    "MACRO": 0.7,
    "NEWS": 0.5,
    "NEWS_ANALYSIS": 0.6
}

# ============================================================================
# FALLBACK CONFIGURATION
# ============================================================================

# Enable/disable OpenAI fallback
ENABLE_OPENAI_FALLBACK = os.getenv("ENABLE_OPENAI_FALLBACK", "true").lower() == "true"

# Fallback system type: "groq", "openai", "hybrid"
FALLBACK_SYSTEM = os.getenv("FALLBACK_SYSTEM", "groq")

# Enable/disable Groq fallback
ENABLE_GROQ_FALLBACK = os.getenv("ENABLE_GROQ_FALLBACK", "true").lower() == "true"

# Fallback triggers (when to activate OpenAI)
FALLBACK_TRIGGERS = {
    "low_aggregate_confidence": True,    # aggregate < threshold
    "all_workers_failed": True,           # all workers returned errors
    "no_useful_data": True,               # all workers returned empty data
    "planner_failure": True,              # intent classification failed
}

# Maximum fallback attempts
MAX_FALLBACK_ATTEMPTS = int(os.getenv("MAX_FALLBACK_ATTEMPTS", "1"))

# ============================================================================
# DATA SOURCE CONFIGURATION
# ============================================================================

# Approved news sources (for quality filtering)
APPROVED_NEWS_SOURCES = [
    "reuters.com",
    "bloomberg.com",
    "economictimes.indiatimes.com",
    "economictimes.com",
    "moneycontrol.com",
    "cnbc.com",
    "ft.com",
    "wsj.com",
    "business-standard.com",
    "livemint.com",
    "marketwatch.com",
    "financialexpress.com",
    "thehindubusinessline.com"
]

# Enable strict source filtering
STRICT_NEWS_SOURCE_FILTERING = os.getenv("STRICT_SOURCE_FILTERING", "false").lower() == "true"

# Maximum articles to fetch and analyze
MAX_NEWS_ARTICLES = int(os.getenv("MAX_NEWS_ARTICLES", "6"))
MIN_ARTICLE_LENGTH = int(os.getenv("MIN_ARTICLE_LENGTH", "300"))

# ============================================================================
# WORKER CONFIGURATION
# ============================================================================

# Prices Worker
PRICES_WORKER_CONFIG = {
    "max_symbols": 10,
    "historical_days": 90,
    "include_volume": True,
    "calculate_volatility": True
}

# Fundamentals Worker
FUNDAMENTALS_WORKER_CONFIG = {
    "max_companies": 5,
    "include_ratios": True,
    "include_balance_sheet": True,
    "timeout_seconds": 15
}

# Macro Worker
MACRO_WORKER_CONFIG = {
    "default_indicators": ["policy_rate", "inflation_headline"],
    "max_indicators": 5,
    "default_lookback_months": 18
}

# News Worker
NEWS_WORKER_CONFIG = {
    "max_articles": MAX_NEWS_ARTICLES,
    "min_article_length": MIN_ARTICLE_LENGTH,
    "enable_full_text_extraction": True,
    "timeout_per_article": 10
}

# ============================================================================
# CACHING
# ============================================================================

CACHE_FILE = os.getenv("CACHE_FILE", "query_cache.json")
ENABLE_CACHING = os.getenv("ENABLE_CACHING", "true").lower() == "true"
CACHE_TTL_SECONDS = int(os.getenv("CACHE_TTL_SECONDS", "300"))  # 5 minutes

# ============================================================================
# LOGGING
# ============================================================================

LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_FILE = os.getenv("LOG_FILE", "financial_intelligence.log")
ENABLE_FILE_LOGGING = os.getenv("ENABLE_FILE_LOGGING", "false").lower() == "true"

# Debug mode (verbose output)
DEBUG_MODE = os.getenv("DEBUG_MODE", "false").lower() == "true"

# ============================================================================
# PERFORMANCE
# ============================================================================

# Maximum concurrent workers
MAX_CONCURRENT_WORKERS = int(os.getenv("MAX_CONCURRENT_WORKERS", "4"))

# Request timeout (seconds)
DEFAULT_REQUEST_TIMEOUT = int(os.getenv("REQUEST_TIMEOUT", "30"))

# Rate limiting
ENABLE_RATE_LIMITING = os.getenv("ENABLE_RATE_LIMITING", "true").lower() == "true"
RATE_LIMIT_REQUESTS_PER_MINUTE = int(os.getenv("RATE_LIMIT_RPM", "60"))

# ============================================================================
# OUTPUT FORMATTING
# ============================================================================

# Save results to file
SAVE_RESULTS = os.getenv("SAVE_RESULTS", "true").lower() == "true"
RESULTS_FILE = os.getenv("RESULTS_FILE", "last_run_results.json")

# Pretty print JSON
PRETTY_PRINT_JSON = os.getenv("PRETTY_PRINT_JSON", "true").lower() == "true"

# Include timestamps in output
INCLUDE_TIMESTAMPS = os.getenv("INCLUDE_TIMESTAMPS", "true").lower() == "true"

# ============================================================================
# VALIDATION
# ============================================================================

def validate_config():
    """Validate configuration and warn about missing keys"""
    
    warnings = []
    errors = []
    
    # Check critical API keys
    if not GROQ_API_KEY:
        errors.append("GROQ_API_KEY not set - system will not function")
    
    # Check fallback system configuration
    if FALLBACK_SYSTEM == "groq" and not (ENABLE_GROQ_FALLBACK and GROQ_API_KEY):
        errors.append("Groq fallback configured but GROQ_API_KEY not set or ENABLE_GROQ_FALLBACK is false")
    
    if FALLBACK_SYSTEM == "openai" and not (ENABLE_OPENAI_FALLBACK and OPENAI_API_KEY):
        errors.append("OpenAI fallback configured but OPENAI_API_KEY not set or ENABLE_OPENAI_FALLBACK is false")
    
    if FALLBACK_SYSTEM == "hybrid":
        if not (ENABLE_GROQ_FALLBACK and GROQ_API_KEY) and not (ENABLE_OPENAI_FALLBACK and OPENAI_API_KEY):
            errors.append("Hybrid fallback configured but neither Groq nor OpenAI fallbacks are properly configured")
    
    if not OPENAI_API_KEY and ENABLE_OPENAI_FALLBACK:
        warnings.append("OPENAI_API_KEY not set - OpenAI fallback disabled")
    
    if not TAVILY_API_KEY and ENABLE_GROQ_FALLBACK:
        warnings.append("TAVILY_API_KEY not set - Groq fallback may not work properly")
    
    if not FRED_API_KEY:
        warnings.append("FRED_API_KEY not set - macro data will be limited")
    
    # Check thresholds
    if not 0 <= AGGREGATE_CONFIDENCE_THRESHOLD <= 1:
        errors.append(f"Invalid CONFIDENCE_THRESHOLD: {AGGREGATE_CONFIDENCE_THRESHOLD}")
    
    # Print warnings and errors
    if warnings:
        print("⚠️  Configuration Warnings:")
        for w in warnings:
            print(f"   - {w}")
        print()
    
    if errors:
        print("❌ Configuration Errors:")
        for e in errors:
            print(f"   - {e}")
        print()
        raise ValueError("Invalid configuration")
    
    return True

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def get_worker_config(worker_name: str) -> dict:
    """Get configuration for specific worker"""
    
    config_map = {
        "PRICES": PRICES_WORKER_CONFIG,
        "FUNDAMENTALS": FUNDAMENTALS_WORKER_CONFIG,
        "MACRO": MACRO_WORKER_CONFIG,
        "NEWS": NEWS_WORKER_CONFIG
    }
    
    return config_map.get(worker_name, {})


def should_enable_fallback() -> bool:
    """Check if any fallback system should be enabled"""
    if FALLBACK_SYSTEM == "groq":
        return ENABLE_GROQ_FALLBACK and GROQ_API_KEY is not None
    elif FALLBACK_SYSTEM == "openai":
        return ENABLE_OPENAI_FALLBACK and OPENAI_API_KEY is not None
    elif FALLBACK_SYSTEM == "hybrid":
        return (ENABLE_GROQ_FALLBACK and GROQ_API_KEY is not None) or \
               (ENABLE_OPENAI_FALLBACK and OPENAI_API_KEY is not None)
    else:
        return False


def should_enable_openai_fallback() -> bool:
    """Check if OpenAI fallback should be enabled"""
    return ENABLE_OPENAI_FALLBACK and OPENAI_API_KEY is not None


def should_enable_groq_fallback() -> bool:
    """Check if Groq fallback should be enabled"""
    return ENABLE_GROQ_FALLBACK and GROQ_API_KEY is not None


def get_fallback_system_type() -> str:
    """Get the configured fallback system type"""
    return FALLBACK_SYSTEM


def get_confidence_threshold(worker_name: str = None) -> float:
    """Get confidence threshold for worker or aggregate"""
    
    if worker_name:
        return WORKER_CONFIDENCE_THRESHOLDS.get(worker_name, 0.5)
    
    return AGGREGATE_CONFIDENCE_THRESHOLD


# ============================================================================
# ENVIRONMENT INFO
# ============================================================================

def print_config_summary():
    """Print configuration summary"""
    
    print("=" * 80)
    print("CONFIGURATION SUMMARY")
    print("=" * 80)
    print(f"\nLLM Provider: {LLM_PROVIDER}")
    print(f"Planner Model: {PLANNER_MODEL}")
    print(f"Worker Model: {WORKER_MODEL}")
    print(f"\nOpenAI Fallback: {'ENABLED' if should_enable_fallback() else 'DISABLED'}")
    if should_enable_fallback():
        print(f"Fallback Model: {OPENAI_FALLBACK_MODEL}")
        print(f"Confidence Threshold: {AGGREGATE_CONFIDENCE_THRESHOLD}")
    print(f"\nAPI Keys Configured:")
    print(f"  GROQ: {'✅' if GROQ_API_KEY else '❌'}")
    print(f"  OpenAI: {'✅' if OPENAI_API_KEY else '❌'}")
    print(f"  FRED: {'✅' if FRED_API_KEY else '❌'}")
    print(f"  Polygon: {'✅' if POLYGON_API_KEY else '❌'}")
    print(f"\nCaching: {'ENABLED' if ENABLE_CACHING else 'DISABLED'}")
    print(f"Debug Mode: {'ON' if DEBUG_MODE else 'OFF'}")
    print("=" * 80)


# Validate configuration on import
if __name__ != "__main__":
    try:
        validate_config()
    except Exception as e:
        print(f"Configuration validation failed: {e}")