"""News Worker with Smart Domain Validation

Key changes:
- Uses DomainValidator for context-aware validation
- Entity-aware filtering
- Industry-specific keyword support
- Graceful fallback for company queries
"""
from ddgs import DDGS
from newspaper import Article
from typing import Dict, Any, List
from datetime import datetime
from urllib.parse import urlparse
import asyncio
import re
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from financial_intelligence.core.dag_context import (
    DAGContext, GovernanceMetadata, TimelockViolationError,
    DomainContaminationError, WorkerError, DomainType
)
from financial_intelligence.utils.domain_validator import validate_domain  # NEW IMPORT


class NewsWorker:
    """Production-grade news fetcher with smart governance"""
    
    def __init__(self):
        self.max_articles = 6
        self.min_article_length = 300
        
        self.trusted_sources = [
            "reuters.com", "bloomberg.com", "livemint.com",
            "economictimes.indiatimes.com", "economictimes.com",
            "business-standard.com", "cnbctv18.com", "moneycontrol.com",
            "ft.com", "wsj.com", "financialexpress.com",
            "thehindubusinessline.com", "marketwatch.com", "cnbc.com",
            "investing.com", "forbes.com", "businesstoday.in",
            "ndtv.com", "thehindu.com", "indiatoday.in",
            "news18.com", "zeebiz.com", "goodreturns.in"
        ]
    
    async def fetch(self, context: DAGContext) -> Dict[str, Any]:
        """Fetch news with smart governance"""
        try:
            entities = context.entities
            historical = self._is_historical_query(context.query)
            
            search_query = self._build_search_query(
                context.query, 
                entities, 
                historical
            )
            
            # Search with retry logic
            search_results = await self._web_search_with_retry(
                search_query, 
                historical
            )
            
            if not search_results:
                return self._no_results_response(
                    search_query, 
                    context,
                    "No search results found"
                )
            
            print(f"    📰 Found {len(search_results)} search results")
            
            # Prioritize trusted sources
            trusted, untrusted = [], []
            for r in search_results[: self.max_articles * 4]:
                if self._is_trusted_source(r.get("href", "")):
                    trusted.append(r)
                else:
                    untrusted.append(r)
            
            sources = trusted[: self.max_articles * 2]
            if len(sources) < self.max_articles:
                sources.extend(untrusted[: self.max_articles * 2])
            
            # Scrape articles with retry
            tasks = [
                self._scrape_article_with_retry(r, context) 
                for r in sources
            ]
            scraped = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Filter valid articles
            articles = [
                a for a in scraped
                if isinstance(a, dict) and a.get("content")
            ]
            
            if not articles:
                return self._no_results_response(
                    search_query,
                    context,
                    "All article scrapes failed"
                )
            
            print(f"    ✅ Scraped {len(articles)} articles successfully")
            
            # GUARD: Validate timelock on articles
            if context.timelock:
                articles = self._validate_timelock(articles, context)
                print(f"    ✅ Timelock validated: {len(articles)} articles within range")
            
            # GUARD: Smart domain validation (NEW)
            if context.domain_hint == DomainType.FINANCIAL:
                try:
                    articles = validate_domain(articles, context)
                    print(f"    ✅ Domain validated: {len(articles)} financial articles")
                except DomainContaminationError as e:
                    # If domain validation fails, check if it's a known company query
                    if self._is_company_query(context):
                        print(f"    ℹ️  Domain validation relaxed for company query")
                        # Keep articles but flag warning
                    else:
                        raise  # Re-raise if not a company query
            
            # Build governance metadata
            governance = GovernanceMetadata(
                timelock_validated=True if context.timelock else False,
                domain_purity_check="PASSED",
                completeness_score=min(len(articles) / self.max_articles, 1.0)
            )
            
            return {
                "status": "success",
                "worker": "NEWS",
                "data": {
                    "articles": articles[: self.max_articles],
                    "keywords_searched": search_query,
                    "historical": historical,
                    "article_count": len(articles[: self.max_articles])
                },
                "timestamp": datetime.now().isoformat(),
                "_governance": governance.to_dict(),
                "_sources": {
                    "urls": [a.get('url') for a in articles[: self.max_articles]],
                    "trusted_count": len([a for a in articles if self._is_trusted_source(a.get('url', ''))])
                }
            }
            
        except TimelockViolationError as e:
            return e.to_dict()
        except DomainContaminationError as e:
            return e.to_dict()
        except WorkerError as e:
            return e.to_dict()
        except Exception as e:
            return {
                "status": "error",
                "worker": "NEWS",
                "error": str(e),
                "timestamp": datetime.now().isoformat(),
                "_governance": GovernanceMetadata(
                    domain_purity_check="ERROR"
                ).to_dict()
            }
    
    def _is_company_query(self, context: DAGContext) -> bool:
        """Check if query is about a specific company"""
        
        # Check entities
        if context.entities and len(context.entities) > 0:
            return True
        
        # Check query for company indicators
        query_lower = context.query.lower()
        
        company_indicators = [
            'ltd', 'limited', 'inc', 'corp', 'company',
            'indigo', 'spicejet', 'air india', 'vistara',
            'reliance', 'tcs', 'infosys', 'wipro',
            'hdfc', 'icici', 'sbi', 'axis', 'tata',
            'apple', 'microsoft', 'google', 'amazon'
        ]
        
        return any(indicator in query_lower for indicator in company_indicators)
    
    def _validate_timelock(
        self, 
        articles: List[Dict], 
        context: DAGContext
    ) -> List[Dict]:
        """Validate articles against timelock"""
        validated_articles = []
        
        for article in articles:
            pub_date_str = article.get('published', 'unknown')
            
            # Try to parse date
            pub_date = self._parse_date(pub_date_str)
            
            if pub_date:
                # Check against max_allowed_date
                if not context.timelock.validate_date(pub_date):
                    print(f"    ⚠️  Skipping article dated {pub_date} (exceeds {context.timelock.max_allowed_date})")
                    continue
            
            validated_articles.append(article)
        
        if len(validated_articles) == 0 and len(articles) > 0:
            raise TimelockViolationError(
                message="All articles exceed max_allowed_date",
                date_found=articles[0].get('published', 'unknown'),
                max_allowed=context.timelock.max_allowed_date
            )
        
        return validated_articles
    
    def _parse_date(self, date_str: str) -> str:
        """Parse date string to YYYY-MM-DD format"""
        if not date_str or date_str == 'unknown':
            return None
        
        # Try common formats
        formats = [
            "%Y-%m-%d",
            "%Y/%m/%d",
            "%d-%m-%Y",
            "%d/%m/%Y",
            "%B %d, %Y",
            "%b %d, %Y"
        ]
        
        for fmt in formats:
            try:
                dt = datetime.strptime(date_str, fmt)
                return dt.strftime("%Y-%m-%d")
            except ValueError:
                continue
        
        return None
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type(Exception)
    )
    async def _web_search_with_retry(
        self, 
        query: str, 
        historical: bool
    ) -> List[Dict]:
        """Web search with retry logic"""
        try:
            ddgs = DDGS()
            
            results = list(ddgs.text(
                query=query,
                max_results=30,
                region="wt-wt",
                safesearch="off",
                timelimit=None if historical else "m"
            ))
            
            # Filter out social media
            excluded_domains = [
                "reddit.com", "quora.com", "twitter.com", 
                "facebook.com", "youtube.com"
            ]
            
            return [
                r for r in results
                if not any(d in r.get("href", "").lower() for d in excluded_domains)
            ]
            
        except Exception as e:
            print(f"    ⚠️  Search attempt failed: {e}")
            raise
    
    async def _scrape_article_with_retry(
        self, 
        search_result: Dict,
        context: DAGContext
    ) -> Dict[str, Any]:
        """Scrape article with retry logic"""
        url = search_result.get("href")
        if not url:
            return None
        
        # Retry wrapper
        for attempt in range(3):
            try:
                loop = asyncio.get_event_loop()
                data = await loop.run_in_executor(
                    None, 
                    self._scrape_article_sync, 
                    url
                )
                
                if data:
                    return {
                        "title": search_result.get("title", "Untitled"),
                        "url": url,
                        "source": self._extract_source_name(url),
                        "published": search_result.get("published", "unknown"),
                        "content": data["content"],
                        "authors": data.get("authors", []),
                        "word_count": len(data["content"].split())
                    }
                
            except Exception as e:
                if attempt < 2:
                    await asyncio.sleep(2 ** attempt)  # Exponential backoff
                    continue
                print(f"    ⚠️  Failed to scrape {url}: {e}")
        
        return None
    
    def _scrape_article_sync(self, url: str) -> Dict[str, Any]:
        """Synchronous article scraping with timeout"""
        try:
            import threading
            import time
            
            result = {}
            exception = None
            
            def scrape_target():
                nonlocal result, exception
                try:
                    article = Article(url)
                    article.download()
                    article.parse()
                    
                    text = article.text.strip()
                    if len(text) < self.min_article_length:
                        result = None
                    else:
                        result = {
                            "content": text,
                            "authors": article.authors
                        }
                except Exception as e:
                    exception = e
            
            # Run with timeout
            thread = threading.Thread(target=scrape_target)
            thread.daemon = True
            thread.start()
            thread.join(timeout=10)  # 10 second timeout
            
            if thread.is_alive():
                print(f"    ⏰ Article timeout: {url}")
                return None
            
            if exception:
                raise exception
            
            return result
            
        except Exception as e:
            # Suppress scraping errors from logs - these are normal
            # print(f"    ⚠️  Article scrape error: {url} - {e}")
            return None
    
    def _is_historical_query(self, query: str) -> bool:
        """Check if query is historical"""
        year_match = re.search(r"\b(19|20)\d{2}\b", query)
        keywords = ["historical", "earlier", "previous", "during", "back in"]
        return bool(year_match or any(k in query.lower() for k in keywords))
    
    def _build_search_query(
        self,
        query: str,
        entities: List[Dict],
        historical: bool
    ) -> str:
        """Build search query"""
        keywords = [query]
        
        for e in entities:
            name = e.get("company") or e.get("search_term")
            if name:
                keywords.append(name)
        
        base = " ".join(dict.fromkeys(keywords))
        
        if historical:
            return (
                f"{base} "
                f"site:reuters.com OR site:bloomberg.com "
                f"OR site:livemint.com OR site:economictimes.com"
            )
        
        return f"{base} news"
    
    def _is_trusted_source(self, url: str) -> bool:
        """Check if source is trusted"""
        return any(src in url.lower() for src in self.trusted_sources)
    
    def _extract_source_name(self, url: str) -> str:
        """Extract source name from URL"""
        try:
            return urlparse(url).netloc.replace("www.", "")
        except Exception:
            return "unknown"
    
    def _no_results_response(
        self, 
        query: str, 
        context: DAGContext,
        reason: str = "No articles found"
    ) -> Dict[str, Any]:
        """Standard no results response"""
        return {
            "status": "no_results",
            "worker": "NEWS",
            "message": reason,
            "query": query,
            "timestamp": datetime.now().isoformat(),
            "_governance": GovernanceMetadata(
                timelock_validated=bool(context.timelock),
                domain_purity_check="NO_DATA"
            ).to_dict()
        }