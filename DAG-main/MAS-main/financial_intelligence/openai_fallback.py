"""
Enhanced OpenAI Fallback System

Triggers when aggregate confidence < 0.7:
- Synthesizes partial worker results
- Provides comprehensive financial analysis
- Handles edge cases gracefully
"""
import os
import json
from typing import Dict, Any, Optional
from datetime import datetime
from openai import OpenAI
from financial_intelligence.config import OPENAI_API_KEY


class OpenAIFallback:
    """Enhanced fallback handler with better context building"""
    
    def __init__(self):
        self.client = OpenAI(api_key=OPENAI_API_KEY) if OPENAI_API_KEY else None
        self.model = "gpt-4o-mini"  # Fast and cost-effective
        self.max_tokens = 1500
        self.enable_web_search = True
        
    def is_available(self) -> bool:
        """Check if OpenAI API is available"""
        return self.client is not None and OPENAI_API_KEY is not None
    
    def _build_system_prompt(self) -> str:
        """Build comprehensive system prompt"""
        return """You are an expert financial analyst assistant helping users understand financial markets and data.

Your capabilities:
- Analyze market trends and price movements
- Explain fundamental analysis concepts
- Interpret macro economic indicators
- Provide context for financial news
- Give balanced, unbiased perspectives

Guidelines:
1. Be clear and concise
2. Use bullet points for complex information
3. Cite specific data when available
4. Acknowledge uncertainty when appropriate
5. Provide actionable insights when relevant
6. Explain financial terms in simple language
7. Never provide investment advice - only educational information

When data is incomplete:
- Acknowledge what data is missing
- Work with available information
- Suggest where users can find more data

Current date: {date}

Remember: You're providing educational information, not investment recommendations.""".format(
            date=datetime.now().strftime("%Y-%m-%d")
        )
    
    def _build_user_message(self, query: str, worker_results: Optional[Dict] = None, web_context: str = "") -> str:
        """Build comprehensive user message with context"""
        
        message_parts = []
        message_parts.append(f"User Query: {query}\n")
        
        # Add web context if available
        if web_context:
            message_parts.append(f"\n{web_context}")
        
        if worker_results:
            message_parts.append("\nAvailable Financial Data:\n")
            
            # Format each worker's results
            for worker_name, result in worker_results.items():
                if result.get("status") != "success":
                    continue
                
                message_parts.append(f"\n{worker_name}:")
                
                if worker_name == "PRICES":
                    message_parts.append(self._format_prices_context(result))
                
                elif worker_name in ["FUNDAMENTALS_IN", "FUNDAMENTALS_US"]:
                    message_parts.append(self._format_fundamentals_context(result))
                
                elif worker_name == "MACRO":
                    message_parts.append(self._format_macro_context(result))
                
                elif worker_name == "NEWS":
                    message_parts.append(self._format_news_context(result))
                
                elif worker_name == "NEWS_ANALYSIS":
                    message_parts.append(self._format_news_analysis_context(result))
        
        message_parts.append("\nTask: Provide a comprehensive, helpful response to the user's query based on the available data and recent web information. If data is limited, acknowledge this and provide the best analysis possible with what's available.")
        
        return "\n".join(message_parts)
    
    def _format_prices_context(self, result: Dict) -> str:
        """Format price data for context"""
        data = result.get("data", {})
        if not data:
            return "  No price data available"
        
        lines = []
        for symbol, price_data in list(data.items())[:5]:  # Limit to 5 symbols
            if "error" in price_data:
                continue
            
            lines.append(f"  {symbol}:")
            lines.append(f"    - Current Price: {price_data.get('current_price')}")
            lines.append(f"    - Change: {price_data.get('change')} ({price_data.get('change_pct')}%)")
            lines.append(f"    - 52-Week Range: {price_data.get('52_week_low')} - {price_data.get('52_week_high')}")
            lines.append(f"    - Volatility: {price_data.get('volatility')}%")
        
        return "\n".join(lines)
    
    def _format_fundamentals_context(self, result: Dict) -> str:
        """Format fundamentals data for context"""
        data = result.get("data", {})
        if not data:
            return "  No fundamental data available"
        
        lines = []
        for company, fund_data in list(data.items())[:5]:
            if "error" in fund_data:
                continue
            
            lines.append(f"  {company}:")
            lines.append(f"    - P/E Ratio: {fund_data.get('pe_ratio', 'N/A')}")
            lines.append(f"    - P/B Ratio: {fund_data.get('pb_ratio', 'N/A')}")
            lines.append(f"    - ROE: {fund_data.get('roe', 'N/A')}%")
            lines.append(f"    - Market Cap: {fund_data.get('market_cap', 'N/A')}")
            lines.append(f"    - Dividend Yield: {fund_data.get('dividend_yield', 'N/A')}%")
        
        return "\n".join(lines)
    
    def _format_macro_context(self, result: Dict) -> str:
        """Format macro data for context"""
        macro_facts = result.get("macro_facts", {})
        if not macro_facts:
            return "  No macro data available"
        
        lines = []
        for indicator, data in macro_facts.items():
            if data.get("status") != "success":
                continue
            
            lines.append(f"  {indicator.replace('_', ' ').title()}:")
            
            if "latest_value" in data:
                lines.append(f"    - Current: {data['latest_value']} {data.get('unit', '')}")
            if "latest_yoy" in data:
                lines.append(f"    - YoY Change: {data['latest_yoy']}%")
            if "trend" in data:
                lines.append(f"    - Trend: {data['trend']}")
            if "change_3m" in data:
                lines.append(f"    - 3-Month Change: {data['change_3m']}")
        
        return "\n".join(lines)
    
    def _format_news_context(self, result: Dict) -> str:
        """Format news data for context"""
        data = result.get("data", {})
        articles = data.get("articles", [])
        
        if not articles:
            return "  No news articles available"
        
        lines = [f"  Found {len(articles)} recent articles:"]
        
        for i, article in enumerate(articles[:3], 1):  # Top 3 articles
            lines.append(f"\n  Article {i}:")
            lines.append(f"    - Title: {article.get('title', 'N/A')}")
            lines.append(f"    - Source: {article.get('source', 'N/A')}")
            
            content = article.get('content', '')
            if content:
                preview = content[:300].replace('\n', ' ').strip()
                lines.append(f"    - Preview: {preview}...")
        
        return "\n".join(lines)
    
    def _format_news_analysis_context(self, result: Dict) -> str:
        """Format news analysis for context"""
        synthesis = result.get("synthesis", {})
        
        if not synthesis:
            return "  No news analysis available"
        
        lines = ["  Market Analysis:"]
        
        if synthesis.get("overall_summary"):
            lines.append(f"    - Summary: {synthesis['overall_summary']}")
        
        if synthesis.get("market_sentiment"):
            lines.append(f"    - Sentiment: {synthesis['market_sentiment']}")
        
        if synthesis.get("key_themes"):
            lines.append("    - Key Themes:")
            for theme in synthesis['key_themes']:
                lines.append(f"      • {theme}")
        
        if synthesis.get("actionable_insights"):
            lines.append("    - Insights:")
            for insight in synthesis['actionable_insights']:
                lines.append(f"      • {insight}")
        
        return "\n".join(lines)
    
    async def _get_web_context(self, query: str) -> str:
        """Get real-time web context for recent queries"""
        if not self.enable_web_search:
            return ""
        
        # Check if query needs recent information
        needs_web = any(word in query.lower() for word in [
            "news", "recent", "current", "latest", "today", "now", 
            "price", "stock price", "market", "earnings", "results"
        ])
        
        if not needs_web:
            return ""
        
        try:
            from ddgs import DDGS
            ddgs = DDGS()
            
            # Search for recent information
            results = list(ddgs.text(query, max_results=3, timelimit='w'))
            
            if not results:
                return ""
            
            context = "Recent web search results:\n"
            for i, r in enumerate(results, 1):
                context += f"{i}. {r['title']}\n"
                context += f"   {r['body'][:150]}...\n"
                context += f"   Source: {r.get('href', 'Unknown')}\n\n"
            
            return context
            
        except Exception as e:
            print(f"   ⚠️  Web search failed: {e}")
            return ""
    
    async def get_fallback_response(self, query: str, worker_results: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Get fallback response from OpenAI with web search capability
        
        Args:
            query: User's original query
            worker_results: Optional partial results from workers
            
        Returns:
            Dict with response and metadata
        """
        if not self.is_available():
            return {
                "status": "error",
                "message": "OpenAI API not configured. Please set OPENAI_API_KEY in .env file.",
                "timestamp": datetime.now().isoformat()
            }
        
        try:
            # Get web context for recent queries
            web_context = await self._get_web_context(query)
            
            system_prompt = self._build_system_prompt()
            user_message = self._build_user_message(query, worker_results, web_context)
            
            # Add token counting for monitoring
            estimated_input_tokens = len(system_prompt.split()) + len(user_message.split())
            
            print(f"   📤 Sending request to OpenAI ({estimated_input_tokens} estimated input tokens)")
            if web_context:
                print(f"   🌐 Web search enabled: included recent context")
            
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message}
                ],
                max_tokens=self.max_tokens,
                temperature=0.7,  # Balanced creativity and accuracy
                top_p=0.9,
                frequency_penalty=0.3,  # Reduce repetition
                presence_penalty=0.3    # Encourage diverse topics
            )
            
            content = response.choices[0].message.content
            tokens_used = response.usage.total_tokens if response.usage else 0
            
            print(f"   📥 Received response ({tokens_used} total tokens)")
            
            return {
                "status": "success",
                "response": content,
                "model": self.model,
                "tokens_used": tokens_used,
                "finish_reason": response.choices[0].finish_reason,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            error_msg = str(e)
            print(f"   ❌ OpenAI API error: {error_msg}")
            
            return {
                "status": "error",
                "message": f"OpenAI API error: {error_msg}",
                "timestamp": datetime.now().isoformat()
            }
    
    def format_fallback_response(self, fallback_result: Dict[str, Any]) -> str:
        """Format fallback response for display"""
        
        if fallback_result.get("status") != "success":
            return f"❌ Fallback Error: {fallback_result.get('message', 'Unknown error')}"
        
        lines = []
        lines.append("🤖 OPENAI ENHANCED RESPONSE")
        lines.append("=" * 80)
        lines.append("")
        lines.append(fallback_result.get("response", "No response available"))
        lines.append("")
        lines.append("=" * 80)
        lines.append(f"Model: {fallback_result.get('model', 'N/A')}")
        lines.append(f"Tokens Used: {fallback_result.get('tokens_used', 'N/A')}")
        lines.append(f"Finish Reason: {fallback_result.get('finish_reason', 'N/A')}")
        
        return "\n".join(lines)


# Global instance
_fallback_handler = OpenAIFallback()

def get_fallback_handler() -> OpenAIFallback:
    """Get global fallback handler instance"""
    return _fallback_handler


# Utility function to check if fallback should trigger
def should_trigger_fallback(aggregate_confidence: float, threshold: float = 0.7) -> bool:
    """
    Determine if OpenAI fallback should be triggered
    
    Args:
        aggregate_confidence: Overall confidence score
        threshold: Minimum confidence required (default 0.7)
        
    Returns:
        True if fallback should trigger
    """
    return aggregate_confidence < threshold


# Utility function to explain why fallback was triggered
def get_fallback_trigger_reason(
    aggregate_confidence: float,
    worker_confidences: Dict[str, float],
    threshold: float = 0.7
) -> str:
    """
    Generate human-readable explanation for why fallback was triggered
    
    Args:
        aggregate_confidence: Overall confidence score
        worker_confidences: Individual worker confidence scores
        threshold: Confidence threshold
        
    Returns:
        Explanation string
    """
    reasons = []
    
    if aggregate_confidence < threshold:
        reasons.append(f"Aggregate confidence ({aggregate_confidence:.2f}) below threshold ({threshold})")
    
    # Identify failing workers
    low_confidence_workers = [
        name for name, conf in worker_confidences.items()
        if conf < 0.5
    ]
    
    if low_confidence_workers:
        reasons.append(f"Low confidence workers: {', '.join(low_confidence_workers)}")
    
    # Check for all failures
    if all(conf < 0.3 for conf in worker_confidences.values()):
        reasons.append("All workers returned low-quality data")
    
    return " | ".join(reasons) if reasons else "Unknown reason"