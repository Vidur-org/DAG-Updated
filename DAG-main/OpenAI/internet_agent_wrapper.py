"""
Internet Agent Wrapper for Tree Orchestrator
Uses the local Tavily-based internet_agent to fetch additional context for each node
"""

from typing import Dict, List, Any
from internet_agent import internet_agent


class InternetAgentWrapper:
    """
    Wrapper for Tavily-based internet agent to fetch additional context for tree nodes
    """
    
    def __init__(self):
        """Initialize the wrapper - internet_agent is a function, not a class"""
        pass
    
    def fetch_context(self, question: str, orchestrator=None) -> Dict[str, Any]:
        """
        Fetch internet research context using Tavily API for a given question.
        
        Args:
            question: The question/query to search for
            
        Returns:
            {
                "content": str,        # Combined content from all sources
                "citations": List[Dict],  # List of citations with URLs, titles, content, scores
                "urls": List[str],     # Just the URLs
                "summary": str,        # Short summary (limited to 1500 chars)
                "total_sources": int,  # Number of sources found
                "error": str (optional) # Error message if any
            }
        """
        try:
            # Call Tavily-based internet agent
            results = internet_agent(question)
            # Increment orchestrator's internet_search_hits if provided
            if orchestrator is not None:
                if hasattr(orchestrator, 'internet_search_hits'):
                    orchestrator.internet_search_hits += 1
            
            if results:
                # Format citations with all metadata
                citations = []
                urls = []
                content_parts = []
                
                for i, result in enumerate(results, 1):
                    citation = {
                        "title": result.get('title', 'Untitled'),
                        "url": result.get('url', ''),
                        "content": result.get('content', ''),
                        "score": result.get('score', 0),
                        "source_number": i
                    }
                    citations.append(citation)
                    
                    if result.get('url'):
                        urls.append(result['url'])
                    
                    # Build summary content with source attribution
                    if result.get('content'):
                        content_parts.append(
                            f"[Source {i}] {result['title']}\n"
                            f"URL: {result.get('url', 'N/A')}\n"
                            f"{result['content'][:300]}...\n"
                        )
                
                # Combine all content
                combined_content = "\n".join(content_parts)
                summary = combined_content[:1500]  # Limit to prevent token overflow
                
                return {
                    "content": combined_content if combined_content else "No additional internet context available.",
                    "citations": citations,
                    "urls": urls,
                    "summary": summary,
                    "total_sources": len(citations)
                }
            else:
                return {
                    "content": "No additional internet context available.",
                    "citations": [],
                    "urls": [],
                    "summary": "",
                    "total_sources": 0
                }
                
        except Exception as e:
            return {
                "content": f"Error fetching internet context: {str(e)}",
                "citations": [],
                "urls": [],
                "summary": "",
                "error": str(e),
                "total_sources": 0
            }
