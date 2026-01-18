"""Enhanced Domain Validator with Context Awareness

Key improvements:
- Entity-aware validation (if company detected, news is financial)
- Industry-specific keywords (airlines, banks, tech)
- Relaxed validation for known companies
- Smart fallback logic
"""
from typing import List, Dict
from financial_intelligence.core.dag_context import DAGContext, DomainType, DomainContaminationError


class DomainValidator:
    """Smart domain validation with context awareness"""
    
    # Core financial keywords (always financial)
    CORE_FINANCIAL_KEYWORDS = [
        'stock', 'share', 'market', 'revenue', 'profit',
        'earnings', 'valuation', 'trading', 'price', 'ebitda',
        'eps', 'pe ratio', 'dividend', 'margin', 'debt',
        'equity', 'assets', 'cash flow', 'ipo', 'merger',
        'acquisition', 'buyback', 'split', 'delisting'
    ]
    
    # Industry-specific keywords (financial if company mentioned)
    INDUSTRY_KEYWORDS = {
        'airlines': [
            'flight', 'aircraft', 'passenger', 'cargo', 'route',
            'fleet', 'airline', 'aviation', 'airport', 'load factor',
            'yield', 'capacity', 'grounded', 'atl', 'rpk', 'ask'
        ],
        'banks': [
            'loan', 'deposit', 'npa', 'provision', 'interest',
            'credit', 'lending', 'borrowing', 'capital adequacy',
            'net interest margin', 'casa ratio'
        ],
        'tech': [
            'software', 'cloud', 'saas', 'platform', 'api',
            'developer', 'infrastructure', 'digital', 'ai',
            'machine learning', 'data center', 'semiconductor'
        ],
        'pharma': [
            'drug', 'patent', 'fda', 'approval', 'clinical trial',
            'molecule', 'generic', 'prescription', 'therapy',
            'vaccine', 'treatment'
        ],
        'auto': [
            'vehicle', 'sales', 'production', 'plant', 'model',
            'launch', 'recall', 'safety', 'electric vehicle',
            'ev', 'battery', 'charging'
        ],
        'retail': [
            'store', 'outlet', 'footfall', 'same store sales',
            'inventory', 'supply chain', 'logistics', 'e-commerce',
            'online', 'offline'
        ],
        'energy': [
            'renewable', 'solar', 'wind', 'capacity', 'power',
            'energy', 'electricity', 'generation', 'gw', 'mw',
            'renewables', 'clean energy', 'green energy', 'solar power',
            'wind power', 'capacity addition', 'power plant', 'grid'
        ]
    }
    
    # Known company name patterns
    COMPANY_INDICATORS = [
        'ltd', 'limited', 'inc', 'corp', 'corporation',
        'company', 'group', 'enterprises', 'industries',
        'pvt', 'private', 'public', 'holdings'
    ]
    
    def __init__(self):
        # Flatten industry keywords for quick lookup
        self.all_industry_keywords = set()
        for keywords in self.INDUSTRY_KEYWORDS.values():
            self.all_industry_keywords.update(keywords)
    
    def validate_article(
        self, 
        article: Dict, 
        context: DAGContext
    ) -> bool:
        """
        Validate if article matches expected domain
        
        Returns:
            True if article passes validation
            False if article should be filtered out
        """
        
        # Skip validation for non-financial queries
        if context.domain_hint != DomainType.FINANCIAL:
            return True
        
        content = article.get('content', '').lower()
        title = article.get('title', '').lower()
        text = content + ' ' + title
        
        # RULE 1: If entities detected, assume financial relevance
        if context.entities and len(context.entities) > 0:
            # Check if any entity mentioned in article
            for entity in context.entities:
                company = entity.get('company', '').lower()
                ticker = entity.get('ticker', '').lower()
                
                if company and company in text:
                    return True  # Entity mentioned = financial
                if ticker and ticker.replace('.ns', '').replace('.bo', '') in text:
                    return True
        
        # RULE 2: Check for core financial keywords
        core_score = sum(
            1 for kw in self.CORE_FINANCIAL_KEYWORDS 
            if kw in text
        )
        
        if core_score >= 2:
            return True  # Strong financial signal
        
        # RULE 3: Check for company name patterns
        company_score = sum(
            1 for indicator in self.COMPANY_INDICATORS
            if indicator in text
        )
        
        if company_score >= 1 and core_score >= 1:
            return True  # Company + some financial context
        
        # RULE 4: Industry-specific keywords (more lenient)
        industry_score = sum(
            1 for kw in self.all_industry_keywords
            if kw in text
        )
        
        if industry_score >= 3:
            # If lots of industry keywords, likely financial even without explicit "stock" mentions
            return True
        
        # RULE 5: Detect specific company names in query
        query_lower = context.query.lower()
        known_companies = [
            'indigo', 'spicejet', 'air india', 'vistara',
            'reliance', 'tcs', 'infosys', 'wipro',
            'hdfc', 'icici', 'sbi', 'axis'
        ]
        
        for company in known_companies:
            if company in query_lower and company in text:
                return True  # Query mentioned company, article discusses it
        
        # RULE 6: If we got here, check for minimum relevance
        # Require at least 1 core keyword OR 2 industry keywords
        if core_score >= 1 or industry_score >= 2:
            return True
        
        # FAIL: Article doesn't meet any criteria
        return False
    
    def validate_articles(
        self, 
        articles: List[Dict], 
        context: DAGContext
    ) -> List[Dict]:
        """
        Validate list of articles, return filtered list
        
        Raises:
            DomainContaminationError if ALL articles fail
        """
        
        if context.domain_hint != DomainType.FINANCIAL:
            return articles  # No validation needed
        
        validated = []
        
        for article in articles:
            if self.validate_article(article, context):
                validated.append(article)
            else:
                print(f"    ⚠️  Filtered non-financial: {article.get('title', '')[:60]}")
        
        # If ALL articles filtered, raise error
        if len(validated) == 0 and len(articles) > 0:
            # BUT: Check if this might be a false positive
            if context.entities or self._query_has_company_name(context.query):
                # User clearly asked about a company, don't block
                print("    ℹ️  Domain check bypassed: Company name in query")
                return articles  # Return original articles
            
            raise DomainContaminationError(
                message="No articles match FINANCIAL domain",
                expected_domain="FINANCIAL",
                actual_domain="NON_FINANCIAL"
            )
        
        return validated
    
    def _query_has_company_name(self, query: str) -> bool:
        """Check if query contains company name"""
        query_lower = query.lower()
        
        # Check for company indicators
        for indicator in self.COMPANY_INDICATORS:
            if indicator in query_lower:
                return True
        
        # Check for known company names
        known_companies = [
            'indigo', 'spicejet', 'air india', 'vistara',
            'reliance', 'tcs', 'infosys', 'wipro',
            'hdfc', 'icici', 'sbi', 'axis', 'tata',
            'apple', 'microsoft', 'google', 'amazon',
            'tesla', 'meta', 'netflix', 'nvidia'
        ]
        
        for company in known_companies:
            if company in query_lower:
                return True
        
        return False


# Singleton instance
_validator = DomainValidator()

def validate_domain(articles: List[Dict], context: DAGContext) -> List[Dict]:
    """Convenience function"""
    return _validator.validate_articles(articles, context)