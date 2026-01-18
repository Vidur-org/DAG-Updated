"""
Enhanced Fundamentals Worker with Dual Data Sources

Sources:
- Screener.in: Fundamentals, ratios, financial statements (annual)
- Moneycontrol: Price, quarterly results, news, shareholding

Key improvements:
1. Dual-source data fetching (Screener + Moneycontrol)
2. Quarterly data extraction from Moneycontrol
3. Better company name resolution
4. Region-aware execution (only Indian companies)
"""
import asyncio
import aiohttp
import requests
import re
from bs4 import BeautifulSoup
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime


class CompanyResolver:
    """Universal company name resolver for Indian NSE companies"""
    
    COMMON_MAPPINGS = {
        # Airlines
        "indigo": "InterGlobe Aviation Limited",
        "spicejet": "SpiceJet Limited",
        "air india": "Air India Limited",
        
        # Large Cap - IT
        "reliance": "Reliance Industries Limited",
        "tcs": "Tata Consultancy Services Limited",
        "infosys": "Infosys Limited",
        "wipro": "Wipro Limited",
        "hcl tech": "HCL Technologies Limited",
        
        # Large Cap - Banking
        "hdfc bank": "HDFC Bank Limited",
        "icici bank": "ICICI Bank Limited",
        "sbi": "State Bank of India",
        "axis bank": "Axis Bank Limited",
        
        # Add more as needed...
    }
    
    @staticmethod
    def resolve_company(raw_name: str) -> Dict[str, str]:
        """
        Resolve company name to canonical form and ticker
        
        Returns:
            {
                "company": "Canonical Company Name",
                "ticker": "SYMBOL",
                "screener_slug": "company-name",
                "moneycontrol_slug": "company-name",
                "source": "mapping|screener|fallback"
            }
        """
        name_lower = raw_name.lower().strip()
        
        # 1. Try hardcoded mappings first
        if name_lower in CompanyResolver.COMMON_MAPPINGS:
            canonical = CompanyResolver.COMMON_MAPPINGS[name_lower]
            ticker = CompanyResolver._infer_ticker(name_lower)
            
            return {
                "company": canonical,
                "ticker": ticker,
                "screener_slug": CompanyResolver._to_screener_slug(canonical),
                "moneycontrol_slug": CompanyResolver._to_moneycontrol_slug(canonical),
                "source": "mapping"
            }
        
        # 2. Try Screener.in API with better URL handling
        try:
            # Use the ticker if available (more reliable for banks)
            search_term = raw_name
            
            # Special handling for common abbreviations
            abbrev_map = {
                "sbi": "State Bank of India",
                "hdfc": "HDFC Bank",
                "icici": "ICICI Bank",
                "rbi": "Reserve Bank of India"
            }
            
            if name_lower in abbrev_map:
                search_term = abbrev_map[name_lower]
            
            url = f"https://www.screener.in/api/company/search/?q={search_term}"
            response = requests.get(url, timeout=5)
            
            if response.status_code == 200:
                results = response.json()
                if results:
                    first = results[0]
                    company_name = first["name"]
                    ticker = first.get("ticker", "")
                    
                    # Extract screener slug from URL
                    screener_url = first.get("url", "")
                    if screener_url:
                        # URL format: /company/STATE-BANK-OF-INDIA/consolidated/
                        slug = screener_url.rstrip('/').split('/')[-2] if '/' in screener_url else ""
                    else:
                        slug = CompanyResolver._to_screener_slug(company_name)
                    
                    return {
                        "company": company_name,
                        "ticker": ticker,
                        "screener_slug": slug,
                        "moneycontrol_slug": CompanyResolver._to_moneycontrol_slug(company_name),
                        "source": "screener"
                    }
        except Exception as e:
            print(f"      Screener API failed: {e}")
        
        # 3. Fallback: Use as-is
        return {
            "company": raw_name.title(),
            "ticker": raw_name.upper().replace(" ", ""),
            "screener_slug": raw_name.lower().replace(" ", "-"),
            "moneycontrol_slug": raw_name.lower().replace(" ", "-"),
            "source": "fallback"
        }
    
    @staticmethod
    def _infer_ticker(name_lower: str) -> str:
        """Infer NSE ticker from company name"""
        ticker_map = {
            "reliance": "RELIANCE",
            "tcs": "TCS",
            "infosys": "INFY",
            "wipro": "WIPRO",
            "hcl tech": "HCLTECH",
            "hdfc bank": "HDFCBANK",
            "icici bank": "ICICIBANK",
            "sbi": "SBIN",
            "axis bank": "AXISBANK",
            "indigo": "INDIGO",
            "spicejet": "SPICEJET",
        }
        
        base_ticker = ticker_map.get(name_lower, name_lower.upper().replace(" ", ""))
        return f"{base_ticker}.NS"
    
    @staticmethod
    def _to_screener_slug(company_name: str) -> str:
        """Convert company name to Screener slug"""
        slug = company_name.lower()
        slug = slug.replace("limited", "ltd")
        slug = slug.replace(" ", "-")
        slug = re.sub(r'[^\w\-]', '', slug)
        return slug
    
    @staticmethod
    def _to_moneycontrol_slug(company_name: str) -> str:
        """Convert company name to Moneycontrol slug"""
        slug = company_name.lower()
        
        # Remove company suffixes
        slug = slug.replace("limited", "")
        slug = slug.replace("ltd", "")
        slug = slug.replace("pvt", "")
        slug = slug.replace("private", "")
        slug = slug.strip()
        
        # Special cases for known companies
        special_cases = {
            "reliance industries": "reliance-industries",
            "tata consultancy services": "tcs",
            "state bank of india": "state-bank-of-india",
            "hdfc bank": "hdfc-bank",
            "icici bank": "icici-bank",
            "infosys": "infosys",
            "wipro": "wipro"
        }
        
        if slug in special_cases:
            return special_cases[slug]
        
        # Default: replace spaces with hyphens
        slug = slug.replace(" ", "-")
        slug = re.sub(r'[^\w\-]', '', slug)
        
        # Remove trailing/leading hyphens
        slug = slug.strip('-')
        
        return slug


class PeriodParser:
    """Extract quarter and FY from query"""
    
    @staticmethod
    def parse_period(query: str) -> Optional[Dict[str, str]]:
        """
        Extract period from query
        
        Examples:
        - "Q3 FY2023" → {"quarter": "Q3", "fy": "2023"}
        - "FY2023 Q3" → {"quarter": "Q3", "fy": "2023"}
        - "third quarter 2023" → {"quarter": "Q3", "fy": "2023"}
        - "FY2022-23" → {"quarter": None, "fy": "2023"}
        
        Returns None if no period found
        """
        query_lower = query.lower()
        
        # Pattern 1: Q3 FY2023 or FY2023 Q3
        match = re.search(r'(q[1-4])\s*fy\s*(\d{2,4})', query_lower)
        if match:
            quarter = match.group(1).upper()
            fy = match.group(2)
            if len(fy) == 2:
                fy = "20" + fy
            return {"quarter": quarter, "fy": fy}
        
        # Pattern 1b: FY2023 Q3 (reversed order)
        match = re.search(r'fy\s*(\d{2,4})\s*(q[1-4])', query_lower)
        if match:
            fy = match.group(1)
            quarter = match.group(2).upper()
            if len(fy) == 2:
                fy = "20" + fy
            return {"quarter": quarter, "fy": fy}
        
        # Pattern 2: third quarter 2023
        quarter_map = {
            "first": "Q1", "1st": "Q1",
            "second": "Q2", "2nd": "Q2",
            "third": "Q3", "3rd": "Q3",
            "fourth": "Q4", "4th": "Q4"
        }
        
        for word, quarter_code in quarter_map.items():
            if word in query_lower and "quarter" in query_lower:
                year_match = re.search(r'\b(20\d{2}|\d{2})\b', query_lower)
                if year_match:
                    fy = year_match.group(1)
                    if len(fy) == 2:
                        fy = "20" + fy
                    return {"quarter": quarter_code, "fy": fy}
        
        # Pattern 3: FY2023 (annual only)
        match = re.search(r'fy\s*(\d{2,4})', query_lower)
        if match:
            fy = match.group(1)
            if len(fy) == 2:
                fy = "20" + fy
            # Check if there's a standalone Q1-Q4 nearby
            q_match = re.search(r'\bq[1-4]\b', query_lower)
            if q_match:
                return {"quarter": q_match.group(0).upper(), "fy": fy}
            return {"quarter": None, "fy": fy}
        
        return None


class ScreenerExtractor:
    """Extract annual fundamentals from Screener.in"""
    
    @staticmethod
    async def fetch_fundamentals(company_slug: str) -> Dict[str, Any]:
        """
        Fetch comprehensive fundamentals from Screener
        
        Data includes:
        - Valuation ratios (PE, PB, etc.)
        - Profitability metrics (ROE, ROCE)
        - Financial health indicators
        - Historical trends
        """
        url = f"https://www.screener.in/company/{company_slug}/consolidated/"
        
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers, timeout=15) as response:
                    if response.status != 200:
                        return {"error": f"HTTP {response.status}"}
                    
                    html = await response.text()
            
            if len(html) < 5000:
                return {"error": "Incomplete response"}
            
            soup = BeautifulSoup(html, "html.parser")
            
            data = {
                "source": "screener",
                "url": url,
                "data_type": "annual"
            }
            
            # Extract key metrics
            metrics = {
                "Market Cap": "market_cap",
                "Current Price": "price",
                "Stock P/E": "pe_ratio",
                "Book Value": "book_value",
                "Dividend Yield": "dividend_yield",
                "ROCE": "roce",
                "ROE": "roe",
                "Face Value": "face_value",
                "Debt to Equity": "debt_to_equity",
                "Price to Book": "pb_ratio",
                "EPS": "eps"
            }
            
            for label, key in metrics.items():
                value = ScreenerExtractor._extract_metric(soup, label)
                if value is not None:
                    data[key] = value
            
            return data
            
        except Exception as e:
            return {"error": str(e)}
    
    @staticmethod
    def _extract_metric(soup: BeautifulSoup, metric_name: str) -> Any:
        """Extract metric from Screener page"""
        try:
            metric_lower = metric_name.lower()
            
            for li in soup.find_all("li"):
                name_span = li.find("span", class_="name")
                value_span = li.find("span", class_="number")
                
                if not name_span or not value_span:
                    continue
                
                label = name_span.get_text(strip=True).lower()
                
                if metric_lower in label or label in metric_lower:
                    raw_value = value_span.get_text(strip=True)
                    return ScreenerExtractor._parse_value(raw_value)
            
            return None
            
        except Exception:
            return None
    
    @staticmethod
    def _parse_value(value_text: str) -> Any:
        """Parse value string"""
        value_text = value_text.replace(",", "").replace("₹", "").strip()
        
        if value_text.endswith("%"):
            try:
                return float(value_text.replace("%", "").strip())
            except:
                return value_text
        
        if value_text.endswith("Cr"):
            try:
                return float(value_text.replace("Cr", "").strip())
            except:
                return value_text
        
        try:
            return float(value_text)
        except:
            return value_text


class MoneycontrolExtractor:
    """Extract quarterly results and additional data from Moneycontrol"""
    
    @staticmethod
    async def fetch_quarterly(
        company_slug: str,
        period: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """
        Fetch quarterly results from Moneycontrol
        
        Args:
            company_slug: Company identifier
            period: {"quarter": "Q3", "fy": "2023"} or None for latest
        """
        print(f"            🔍 Moneycontrol slug: {company_slug}")
        print(f"            🔍 Looking for: {period}")
        
        # Try multiple URL patterns
        url_patterns = [
            f"https://www.moneycontrol.com/financials/{company_slug}/results/quarterly-results",
            f"https://www.moneycontrol.com/financials/{company_slug}bank/results/quarterly-results",
            f"https://www.moneycontrol.com/financials/{company_slug}/results/quarterly"
        ]
        
        for base_url in url_patterns:
            try:
                print(f"            🌐 Trying: {base_url}")
                
                response = requests.get(base_url, timeout=10, headers={
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
                })
                
                print(f"            📡 Status: {response.status_code}")
                
                if response.status_code != 200:
                    continue  # Try next URL pattern
                
                soup = BeautifulSoup(response.text, "html.parser")
                
                # Find results table (try multiple selectors)
                table = (
                    soup.find("table", {"class": "mctable1"}) or
                    soup.find("table", {"id": "results"}) or
                    soup.find("table", attrs={"class": lambda x: x and "table" in x.lower()})
                )
                
                if not table:
                    continue  # Try next URL pattern
                
                rows = table.find_all("tr")
                if len(rows) < 2:
                    continue
                
                # Extract headers (quarters)
                header_row = rows[0]
                quarters = []
                for th in header_row.find_all("th")[1:]:
                    text = th.text.strip()
                    if text:
                        quarters.append(text)
                
                if not quarters:
                    print(f"            ⚠️  No quarters found in table")
                    continue
                
                print(f"            📅 Available quarters: {quarters[:3]}")
                
                # Determine target column
                target_col_idx = None
                
                if period and period.get("quarter"):
                    # Find specific quarter
                    target_quarter = f"{period['quarter']} FY{period['fy'][-2:]}"
                    print(f"            🎯 Searching for: {target_quarter}")
                    
                    for idx, q in enumerate(quarters):
                        print(f"               Checking: {q}")
                        if target_quarter.lower() in q.lower():
                            target_col_idx = idx
                            print(f"            ✅ Found at index {idx}")
                            break
                    
                    if target_col_idx is None:
                        # Couldn't find exact quarter, try fuzzy match
                        q_num = period['quarter'][1]  # Extract number from Q3
                        fy_short = period['fy'][-2:]
                        
                        for idx, q in enumerate(quarters):
                            if q_num in q and fy_short in q:
                                target_col_idx = idx
                                break
                    
                    if target_col_idx is None:
                        return {
                            "error": f"Quarter {target_quarter} not found in available data",
                            "available_quarters": quarters,
                            "url_tried": base_url
                        }
                else:
                    # Use latest (first column)
                    target_col_idx = 0
                
                # Extract metrics
                metrics = {}
                
                for row in rows[1:]:
                    cols = row.find_all("td")
                    if len(cols) <= target_col_idx + 1:
                        continue
                    
                    metric_name = cols[0].text.strip().lower()
                    value_text = cols[target_col_idx + 1].text.strip()
                    
                    # Clean value text
                    value_text = value_text.replace(",", "").replace("₹", "").strip()
                    
                    try:
                        value = float(value_text)
                        
                        # Map metrics with multiple aliases
                        if any(k in metric_name for k in ["sales", "total income", "revenue", "income from operations"]):
                            metrics["revenue_crore"] = value
                        elif any(k in metric_name for k in ["operating profit", "ebit", "operating income"]):
                            metrics["operating_profit_crore"] = value
                        elif any(k in metric_name for k in ["net profit", "profit after tax", "pat"]):
                            metrics["net_profit_crore"] = value
                        elif "eps" in metric_name:
                            metrics["eps"] = value
                        elif any(k in metric_name for k in ["pbt", "profit before tax"]):
                            metrics["profit_before_tax_crore"] = value
                    
                    except (ValueError, TypeError):
                        continue
                
                if metrics:
                    return {
                        "source": "moneycontrol",
                        "period": quarters[target_col_idx] if target_col_idx < len(quarters) else "Latest",
                        "metrics": metrics,
                        "confidence": 0.95,
                        "url_used": base_url
                    }
                    
            except Exception as e:
                print(f"      Moneycontrol URL {base_url} failed: {e}")
                continue  # Try next URL pattern
        
        # All URL patterns failed
        return {
            "error": "Could not extract data from Moneycontrol",
            "urls_tried": url_patterns
        }


class FundamentalsWorker:
    """Enhanced Indian Fundamentals Worker with dual sources"""
    
    def __init__(self):
        self.resolver = CompanyResolver()
        self.period_parser = PeriodParser()
        self.screener = ScreenerExtractor()
        self.moneycontrol = MoneycontrolExtractor()
        
        # Try to import yfinance as fallback
        try:
            import yfinance as yf
            self.yf = yf
            self.has_yfinance = True
        except ImportError:
            self.yf = None
            self.has_yfinance = False
            print("      ℹ️  yfinance not available - using Screener/Moneycontrol only")

    async def fetch(self, intent_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Fetch fundamentals with dual-source coverage
        
        Priority:
        1. Screener for annual fundamentals and ratios
        2. Moneycontrol for quarterly results if period specified
        3. Merge both sources for comprehensive view
        """
        
        try:
            query = intent_data.get("query", "")
            entities = intent_data.get("entities", [])
            
            # CRITICAL: Filter only Indian companies
            indian_entities = [
                e for e in entities
                if e.get("region") == "IN" or 
                   e.get("ticker", "").endswith((".NS", ".BO"))
            ]
            
            if not indian_entities:
                return {
                    "status": "no_symbols",
                    "worker": "FUNDAMENTALS_IN",
                    "message": "No Indian companies detected in query",
                    "timestamp": datetime.now().isoformat()
                }
            
            # Parse period
            period = self.period_parser.parse_period(query)
            
            if period:
                print(f"      📅 Detected period: {period['quarter'] or 'Annual'} FY{period['fy']}")
            else:
                print(f"      📅 No period specified, fetching latest data")
            
            # Resolve companies
            companies = {}
            for entity in indian_entities:
                company_name = entity.get("company", "")
                if company_name:
                    resolved = self.resolver.resolve_company(company_name)
                    # Use the ticker from entity if resolution failed
                    ticker = resolved["ticker"] if resolved["ticker"] else entity.get("ticker", "")
                    if ticker:
                        companies[ticker] = resolved
                        # Ensure resolved dict has correct ticker
                        companies[ticker]["ticker"] = ticker
            
            if not companies:
                return {
                    "status": "no_companies",
                    "worker": "FUNDAMENTALS_IN",
                    "message": "Could not resolve company names",
                    "timestamp": datetime.now().isoformat()
                }
            
            print(f"      🏢 Resolved {len(companies)} Indian companies")
            
            # Debug: Show resolved companies
            for ticker, resolved in companies.items():
                print(f"         - {resolved['company']} → {ticker}")
            
            # Fetch data from both sources
            company_data = {}
            
            for ticker, resolved in companies.items():
                print(f"      📊 Fetching: {resolved['company']}")
                
                # Ensure ticker is not empty
                if not ticker or ticker == "":
                    print(f"         ⚠️  Empty ticker detected, using fallback")
                    ticker = resolved.get("ticker", "UNKNOWN")
                
                # Fetch Screener data (annual fundamentals)
                screener_data = await self.screener.fetch_fundamentals(
                    resolved["screener_slug"]
                )
                
                # Debug: Show what Screener returned
                if "error" in screener_data:
                    print(f"         ❌ Screener error: {screener_data['error']}")
                else:
                    print(f"         ✅ Screener: {len(screener_data)} fields")
                
                # Fetch Moneycontrol data (quarterly if period specified)
                moneycontrol_data = {}
                if period:
                    # Always try Moneycontrol if any period specified
                    print(f"         📅 Fetching quarterly data for {period}")
                    moneycontrol_data = await self.moneycontrol.fetch_quarterly(
                        resolved["moneycontrol_slug"],
                        period
                    )
                    
                    # Debug: Show what Moneycontrol returned
                    if "error" in moneycontrol_data:
                        print(f"         ❌ Moneycontrol error: {moneycontrol_data['error']}")
                    elif moneycontrol_data:
                        print(f"         ✅ Moneycontrol: {len(moneycontrol_data.get('metrics', {}))} metrics")
                
                # Merge data sources
                merged_data = {
                    "name": resolved["company"],
                    "ticker": ticker,
                }
                
                # Add Screener data
                if "error" not in screener_data:
                    merged_data.update(screener_data)
                else:
                    merged_data["screener_error"] = screener_data["error"]
                
                # Add or override with Moneycontrol quarterly data
                if moneycontrol_data and "error" not in moneycontrol_data:
                    merged_data["quarterly_results"] = moneycontrol_data["metrics"]
                    merged_data["period"] = moneycontrol_data["period"]
                    merged_data["data_type"] = "quarterly"
                elif moneycontrol_data and "error" in moneycontrol_data:
                    merged_data["moneycontrol_error"] = moneycontrol_data["error"]
                
                # Check if we got ANY data
                if len(merged_data) <= 2:  # Only name and ticker
                    # FALLBACK: Try yfinance as last resort
                    if self.has_yfinance:
                        print(f"         🔄 Trying yfinance fallback...")
                        yf_data = await self._fetch_yfinance_fallback(ticker)
                        if yf_data and "error" not in yf_data:
                            merged_data.update(yf_data)
                            merged_data["data_source"] = "yfinance_fallback"
                            print(f"         ✅ yfinance: {len(yf_data)} fields")
                        else:
                            merged_data["error"] = "No data available from any source"
                            print(f"         ⚠️  No data from any source for {ticker}")
                    else:
                        merged_data["error"] = "No data available from any source"
                        print(f"         ⚠️  No data from any source for {ticker}")
                
                company_data[ticker] = merged_data
            
            return {
                "status": "success",
                "worker": "FUNDAMENTALS_IN",
                "data": company_data,
                "period_requested": period,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            return {
                "status": "error",
                "worker": "FUNDAMENTALS_IN",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    async def _fetch_yfinance_fallback(self, ticker: str) -> Dict[str, Any]:
        """Fallback to yfinance if Screener and Moneycontrol fail"""
        
        if not self.has_yfinance:
            return {"error": "yfinance not available"}
        
        try:
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(
                None,
                self._yfinance_sync,
                ticker
            )
        except Exception as e:
            return {"error": str(e)}
    
    def _yfinance_sync(self, ticker: str) -> Dict[str, Any]:
        """Synchronous yfinance fetch"""
        
        try:
            t = self.yf.Ticker(ticker)
            info = t.info if hasattr(t, 'info') else {}
            
            if not info or len(info) < 5:
                return {"error": "Insufficient data from yfinance"}
            
            # Get price
            price = info.get("regularMarketPrice") or info.get("currentPrice")
            if not price:
                hist = t.history(period="1d")
                if not hist.empty:
                    price = hist['Close'].iloc[-1]
            
            data = {
                "price": round(float(price), 2) if price else None,
                "pe_ratio": self._safe_round(info.get("trailingPE"), 2),
                "pb_ratio": self._safe_round(info.get("priceToBook"), 2),
                "market_cap": self._format_market_cap_yf(info.get("marketCap")),
                "book_value": self._safe_round(info.get("bookValue"), 2),
                "roe": self._safe_round(info.get("returnOnEquity", 0) * 100, 2) if info.get("returnOnEquity") else None,
                "dividend_yield": self._safe_round(info.get("dividendYield", 0) * 100, 2) if info.get("dividendYield") else None,
                "eps": self._safe_round(info.get("trailingEps"), 2),
                "debt_to_equity": self._safe_round(info.get("debtToEquity"), 2),
            }
            
            # Filter out None values
            return {k: v for k, v in data.items() if v is not None}
            
        except Exception as e:
            return {"error": str(e)}
    
    def _safe_round(self, value, decimals):
        """Safely round a value"""
        try:
            if value is not None:
                return round(float(value), decimals)
        except:
            pass
        return None
    
    def _format_market_cap_yf(self, market_cap):
        """Format market cap"""
        try:
            if market_cap is None:
                return None
            
            mc = float(market_cap)
            
            # Convert to Crores (1 Crore = 10 Million)
            crores = mc / 10000000
            
            if crores >= 100000:
                return f"₹{crores/100000:.2f}L Cr"
            elif crores >= 1000:
                return f"₹{crores/1000:.2f}K Cr"
            else:
                return f"₹{crores:.2f} Cr"
        except:
            return None
            
            return {
                "status": "success",
                "worker": "FUNDAMENTALS_IN",
                "data": company_data,
                "period_requested": period,
                "timestamp": datetime.now().isoformat()
            }
            
