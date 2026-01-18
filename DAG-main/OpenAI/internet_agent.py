import os
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../MAS-main/llm')))
from llm_client import call_llm

try:
    from tavily import TavilyClient
    TAVILY_AVAILABLE = True
except ImportError:
    TAVILY_AVAILABLE = False
    print("⚠️ Warning: Tavily not installed. Internet research will return empty results.")
    print("   To enable: pip install tavily-python")

def internet_agent(query):
    """
    Fetch web search results using Tavily API.
    Returns list of search results with title, url, content, and score.
    """
    if not TAVILY_AVAILABLE:
        return []

    # Summarize query if too long
    if len(query) > 400:
        try:
            system = "You are an expert at rewriting and summarizing search queries for web search. Given a long query, rewrite it as a concise, efficient, and information-rich search query under 400 characters, preserving the core intent. Return only the new query, no explanations."
            user = f"Original query: {query}"
            summarized = call_llm(system, user)
            if summarized and len(summarized) <= 400:
                query = summarized
            else:
                query = summarized[:400]
        except Exception as e:
            print(f"⚠️ Error summarizing query: {e}")
            query = query[:400]

    api_key = os.getenv("TAVILY_API_KEY")
    if not api_key:
        raise ValueError("TAVILY_API_KEY environment variable is not set. Please set it before running.")

    try:
        client = TavilyClient(api_key=api_key)

        # Perform search
        response = client.search(
            query=query,
            search_depth="advanced",  # Use advanced search for more comprehensive results
            max_results=5  # Adjust based on your needs
        )

        # Extract relevant text from results
        results = []
        for result in response.get('results', []):
            content = result.get('content', '')
            # If content is too short, use title + url as fallback
            if not content or len(content.strip()) < 100:
                content = f"{result.get('title', '')} (see: {result.get('url', '')})"
            results.append({
                'title': result.get('title', ''),
                'url': result.get('url', ''),
                'content': content,
                'score': result.get('score', 0)
            })
        return results
    except Exception as e:
        print(f"⚠️ Error in internet_agent: {str(e)}")
        return []


# Example usage
if __name__ == "__main__":
    query = "tata motors stock"
    results = internet_agent(query)
    
    for i, result in enumerate(results, 1):
        print(f"\n--- Result {i} ---")
        print(f"Title: {result['title']}")
        print(f"URL: {result['url']}")
        print(f"Score: {result['score']}")
        print(f"Content: {result['content']}...")  # Print first 200 chars