from agents.base import Agent
import asyncio
from concurrent.futures import ThreadPoolExecutor
from llm.llm_client import call_llm
from financial_intelligence.main_parallel import run_financial_system

class InternetAgent(Agent):
    def __init__(self):
        super().__init__("internet_agent")

    def preprocess(self, task_input: str):
        # Directly send query to LLM
        return task_input

    def call_tool(self, processed_input):
        # Run async code in separate thread to avoid nested event loop issues
        def run_in_thread():
            return asyncio.run(run_financial_system(processed_input))
        
        with ThreadPoolExecutor() as executor:
            future = executor.submit(run_in_thread)
            output = future.result()
            
            # Extract citations (URLs) from the financial_intelligence output
            citations = []
            
            if isinstance(output, dict):
                # Check for results structure
                results = output.get('results', {})
                
                # Extract URLs from NEWS worker
                if 'NEWS' in results:
                    news_data = results['NEWS'].get('data', {})
                    articles = news_data.get('articles', [])
                    for article in articles:
                        if isinstance(article, dict) and article.get('url'):
                            citations.append({
                                "title": article.get('title', 'Untitled'),
                                "url": article.get('url'),
                                "source": article.get('source', 'Unknown'),
                                "published": article.get('published', 'unknown')
                            })
                
                # Extract URLs from NEWS_ANALYSIS worker
                if 'NEWS_ANALYSIS' in results:
                    analysis_sources = results['NEWS_ANALYSIS'].get('_sources', {})
                    urls = analysis_sources.get('urls', [])
                    for url in urls:
                        # Avoid duplicates
                        if not any(c['url'] == url for c in citations):
                            citations.append({
                                "title": "Additional Source",
                                "url": url,
                                "source": "NEWS_ANALYSIS",
                                "published": "unknown"
                            })
                
                # Check top-level _sources as fallback
                if not citations and '_sources' in output:
                    sources = output['_sources']
                    if isinstance(sources, dict) and 'urls' in sources:
                        for url in sources['urls']:
                            citations.append({
                                "title": "Financial Intelligence Source",
                                "url": url,
                                "source": "financial_intelligence",
                                "published": "unknown"
                            })
            
            return {
                "status": "success",
                "data": output,
                "citations": citations
            }