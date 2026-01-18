"""
Groq-based Fallback System for Financial Intelligence

Integrates the groq-backend WebGPT functionality as a replacement for OpenAI fallback.
Provides web search and synthesis capabilities using Groq models and Tavily search.
"""
import json
import os
import asyncio
from typing import Dict, Any, Optional, List
from datetime import datetime
import sys
from pathlib import Path

# Add groq-backend to path to import its modules
groq_backend_path = Path(__file__).parent / "groq-backend"
sys.path.insert(0, str(groq_backend_path))

try:
    from app.agents import route_query, needs_web_search
    from app.search import web_search, format_search_context
    from app.llm import openai_chat
    GROQ_BACKEND_AVAILABLE = True
except ImportError as e:
    print(f"Warning: groq-backend modules not available: {e}")
    GROQ_BACKEND_AVAILABLE = False

try:
    from config import GROQ_API_KEY, TAVILY_API_KEY
except ImportError:
    GROQ_API_KEY = os.getenv("GROQ_API_KEY")
    TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")


class GroqFallback:
    """
    Groq-based fallback system using groq-backend components
    """
    
    def __init__(self):
        self.api_key = GROQ_API_KEY
        self.tavily_key = TAVILY_API_KEY
        self.available = GROQ_BACKEND_AVAILABLE and self.api_key and self.tavily_key
        
        if not self.available:
            missing = []
            if not GROQ_BACKEND_AVAILABLE:
                missing.append("groq-backend modules")
            if not self.api_key:
                missing.append("GROQ_API_KEY")
            if not self.tavily_key:
                missing.append("TAVILY_API_KEY")
            print(f"⚠️ Groq fallback unavailable: missing {', '.join(missing)}")
    
    def is_available(self) -> bool:
        """Check if Groq fallback is available"""
        return self.available
    
    async def get_fallback_response(self, query: str, worker_results: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Get fallback response using Groq-based WebGPT system
        
        Args:
            query: The user query
            worker_results: Optional worker results (not used in Groq implementation)
            
        Returns:
            Dict with response metadata and content
        """
        if not self.available:
            return {
                "status": "error",
                "message": "Groq fallback not available - missing dependencies or API keys",
                "response": None,
                "references": [],
                "model": "groq-unavailable",
                "searches_performed": 0,
                "tokens_used": "N/A",
                "finish_reason": "unavailable",
                "timestamp": datetime.now().isoformat()
            }
        
        start_time = datetime.now()
        
        try:
            print(f"\n🚀 Groq Fallback: Processing query...")
            print(f"   Query: {query[:100]}...")
            
            # Use groq-backend's route_query function
            result = route_query(query)
            
            execution_time = (datetime.now() - start_time).total_seconds()
            
            # Extract response and sources
            reply = result.get("reply", "")
            sources = result.get("sources", [])
            query_type = result.get("type", "unknown")
            
            # Format sources for consistency
            formatted_sources = []
            for source in sources:
                if isinstance(source, dict):
                    formatted_sources.append(source.get("url", ""))
                elif isinstance(source, str):
                    formatted_sources.append(source)
            
            print(f"   ✅ Groq fallback completed in {execution_time:.1f}s")
            print(f"   Type: {query_type}, Sources: {len(formatted_sources)}")
            
            return {
                "status": "success",
                "response": reply,
                "references": formatted_sources,
                "model": "groq-webgpt",
                "data_source": "tavily_search",
                "searches_performed": 1 if query_type == "web_search" else 0,
                "tokens_used": "N/A",  # Groq doesn't provide token usage in this implementation
                "finish_reason": "stop",
                "execution_time_seconds": round(execution_time, 2),
                "query_type": query_type,
                "timestamp": datetime.now().isoformat(),
                "fallback_system": "groq"
            }
            
        except Exception as e:
            execution_time = (datetime.now() - start_time).total_seconds()
            print(f"   ❌ Groq fallback failed: {e}")
            
            return {
                "status": "error",
                "message": str(e),
                "response": None,
                "references": [],
                "model": "groq-error",
                "searches_performed": 0,
                "tokens_used": "N/A",
                "finish_reason": "error",
                "execution_time_seconds": round(execution_time, 2),
                "timestamp": datetime.now().isoformat(),
                "fallback_system": "groq"
            }
    
    async def answer_query(self, query: str, worker_results: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Alias for get_fallback_response for compatibility with existing interface
        """
        return await self.get_fallback_response(query, worker_results)


class HybridFallback:
    """
    Hybrid fallback system that tries Groq first, then falls back to OpenAI if needed
    """
    
    def __init__(self):
        self.groq_fallback = GroqFallback()
        
        # Import OpenAI fallback as backup
        try:
            from openai_fallback import OpenAIFallback
            self.openai_fallback = OpenAIFallback()
        except ImportError:
            self.openai_fallback = None
            print("⚠️ OpenAI fallback not available as backup")
    
    def is_available(self) -> bool:
        """Check if any fallback system is available"""
        return self.groq_fallback.is_available() or (
            self.openai_fallback and self.openai_fallback.is_available()
        )
    
    async def get_fallback_response(self, query: str, worker_results: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Try Groq first, fall back to OpenAI if Groq fails
        """
        # Try Groq first
        if self.groq_fallback.is_available():
            try:
                result = await self.groq_fallback.get_fallback_response(query, worker_results)
                if result.get("status") == "success":
                    result["fallback_system"] = "groq_primary"
                    return result
                else:
                    print(f"⚠️ Groq fallback failed: {result.get('message')}")
            except Exception as e:
                print(f"⚠️ Groq fallback exception: {e}")
        
        # Fall back to OpenAI
        if self.openai_fallback and self.openai_fallback.is_available():
            print("🔄 Falling back to OpenAI...")
            try:
                result = await self.openai_fallback.get_fallback_response(query, worker_results)
                if result.get("status") == "success":
                    result["fallback_system"] = "openai_backup"
                    return result
                else:
                    print(f"⚠️ OpenAI fallback failed: {result.get('message')}")
            except Exception as e:
                print(f"⚠️ OpenAI fallback exception: {e}")
        
        # Both failed
        return {
            "status": "error",
            "message": "Both Groq and OpenAI fallbacks failed",
            "response": None,
            "references": [],
            "model": "none",
            "searches_performed": 0,
            "tokens_used": "N/A",
            "finish_reason": "failed",
            "timestamp": datetime.now().isoformat(),
            "fallback_system": "none"
        }
    
    async def answer_query(self, query: str, worker_results: Optional[Dict] = None) -> Dict[str, Any]:
        """Alias for get_fallback_response"""
        return await self.get_fallback_response(query, worker_results)


# ============================================================================
# FACTORY FUNCTIONS (for compatibility with existing system)
# ============================================================================

_groq_handler = None
_hybrid_handler = None

def get_groq_fallback_handler():
    """Get Groq fallback handler instance"""
    global _groq_handler
    if _groq_handler is None:
        _groq_handler = GroqFallback()
    return _groq_handler

def get_hybrid_fallback_handler():
    """Get hybrid fallback handler instance"""
    global _hybrid_handler
    if _hybrid_handler is None:
        _hybrid_handler = HybridFallback()
    return _hybrid_handler

def should_trigger_fallback(confidence: float, threshold: float = 0.7) -> bool:
    """Check if fallback should be triggered based on confidence"""
    return confidence < threshold

def get_fallback_trigger_reason(confidence: float, worker_confs: dict, threshold: float = 0.7) -> str:
    """Get reason for fallback trigger"""
    reasons = []
    if confidence < threshold:
        reasons.append(f"Confidence {confidence:.2f} < {threshold}")
    low = [n for n, c in worker_confs.items() if c < 0.5]
    if low:
        reasons.append(f"Low: {', '.join(low)}")
    return " | ".join(reasons) or "Unknown"


# ============================================================================
# LEGACY COMPATIBILITY
# ============================================================================

# For backward compatibility, provide the same interface as openai_fallback
class GroqFallbackWrapper:
    """
    Wrapper to make Groq fallback compatible with OpenAI fallback interface
    """
    
    def __init__(self):
        self.groq = GroqFallback()
    
    def is_available(self) -> bool:
        return self.groq.is_available()
    
    async def get_fallback_response(self, query: str, worker_results=None) -> Dict:
        """Legacy interface method"""
        return await self.groq.get_fallback_response(query, worker_results)
    
    async def answer_query(self, query: str, worker_results=None) -> Dict:
        """Direct method"""
        return await self.groq.answer_query(query, worker_results)
