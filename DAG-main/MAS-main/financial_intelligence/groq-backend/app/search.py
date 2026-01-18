import os
from tavily import TavilyClient
from dotenv import load_dotenv

load_dotenv()

tavily_client = TavilyClient(api_key=os.getenv("TAVILY_API_KEY"))

def web_search(query: str, max_results: int = 5):
    """
    Perform web search using Tavily API
    Returns structured search results with content
    """
    try:
        response = tavily_client.search(
            query=query,
            max_results=max_results,
            search_depth="advanced",
            include_answer=True,
            include_raw_content=False
        )
        
        return {
            "answer": response.get("answer", ""),
            "results": response.get("results", []),
            "query": query
        }
    except Exception as e:
        return {
            "error": str(e),
            "answer": "",
            "results": [],
            "query": query
        }

def format_search_context(search_results: dict) -> str:
    """Format search results into context for LLM"""
    context_parts = []
    
    # Add quick answer if available
    if search_results.get("answer"):
        context_parts.append(f"Quick Answer: {search_results['answer']}\n")
    
    # Add detailed results
    context_parts.append("Search Results:\n")
    for idx, result in enumerate(search_results.get("results", []), 1):
        context_parts.append(f"\n[{idx}] {result.get('title', 'No title')}")
        context_parts.append(f"URL: {result.get('url', 'N/A')}")
        context_parts.append(f"Content: {result.get('content', 'No content')}\n")
    
    return "\n".join(context_parts)