"""
Enhanced US Fundamentals Worker

Key improvements:
1. Strict region filtering (only US companies)
2. Better ticker detection
3. Comprehensive error handling
4. Quarterly data support via yfinance
"""
import asyncio
from typing import Dict, Any, List
from datetime import datetime
import re


class USFundamentalsWorker:
    """Fetch US company fundamentals using yfinance"""

    def __init__(self):
        # Common US company name to ticker mappings
        self.name_to_ticker = {
            # Tech Giants
            "apple": "AAPL",
            "microsoft": "MSFT",
            "google": "GOOGL",
            "alphabet": "GOOGL",
            "amazon": "AMZN",
            "facebook": "META",
            "meta": "META",
            "tesla": "TSLA",
            "nvidia": "NVDA",
            "netflix": "NFLX",
            "adobe": "ADBE",
            "salesforce": "CRM",
            "oracle": "ORCL",
            "intel": "INTC",
            "amd": "AMD",
            
            # Finance
            "jpmorgan": "JPM",
            "jp morgan": "JPM",
            "bank of america": "BAC",
            "wells fargo": "WFC",
            "goldman sachs": "GS",
            "morgan stanley": "MS",
            "visa": "V",
            "mastercard": "MA",
            
            # Consumer
            "walmart": "WMT",
            "costco": "COST",
            "coca cola": "KO",
            "pepsi": "PEP",
            "mcdonalds": "MCD",
            "starbucks": "SBUX",
            
            # Healthcare
            "johnson & johnson": "JNJ",
            "pfizer": "PFE",
            "moderna": "MRNA",
            
            # Other
            "boeing": "BA",
            "general electric": "GE",
            "exxon": "XOM",
            "chevron": "CVX"
        }
    
    def _is_us_ticker(self, ticker: str) -> bool:
        """Check if ticker is US-based"""
        # Exclude Indian tickers
        if ticker.endswith((".NS", ".BO")):
            return False
        
        # Exclude other non-US suffixes
        non_us_suffixes = [".L", ".HK", ".T", ".SS", ".SZ"]
        if any(ticker.endswith(suffix) for suffix in non_us_suffixes):
            return False
        
        # US tickers are typically 1-5 letters with no suffix
        clean_ticker = ticker.split('.')[0].upper()
        return 1 <= len(clean_ticker) <= 5 and clean_ticker.isalpha()
    
    def _is_us_company(self, company_name: str) -> bool:
        """Check if company name suggests US company"""
        name_lower = company_name.lower()
        
        # Indian company indicators
        indian_indicators = [
            "ltd", "limited", "pvt", "private",
            "industries", "enterprises",
            "reliance", "tata", "infosys", "wipro",
            "hdfc", "icici", "sbi", "axis"
        ]
        
        # If company name has Indian indicators, it's not US
        if any(ind in name_lower for ind in indian_indicators):
            return False
        
        # US company indicators
        us_indicators = [
            "inc", "corp", "corporation",
            "apple", "microsoft", "google", "amazon",
            "tesla", "meta", "netflix"
        ]
        
        return any(ind in name_lower for ind in us_indicators)

    async def fetch(self, intent_data: Dict[str, Any]) -> Dict[str, Any]:
        """Fetch US fundamentals with strict region filtering"""
        
        try:
            # Check if yfinance is available
            try:
                import yfinance as yf
            except ImportError:
                return {
                    "status": "error",
                    "worker": "FUNDAMENTALS_US",
                    "error": "yfinance not installed. Run: pip install yfinance",
                    "timestamp": datetime.now().isoformat()
                }
            
            query = intent_data.get("query", "").lower()
            entities = intent_data.get("entities", [])
            
            # CRITICAL: Filter only US companies
            us_entities = []
            for entity in entities:
                ticker = entity.get("ticker", "")
                company = entity.get("company", "")
                region = entity.get("region", "")
                
                # Strict filtering
                if region == "US" and self._is_us_ticker(ticker):
                    us_entities.append(entity)
                elif self._is_us_ticker(ticker) and not ticker.endswith((".NS", ".BO")):
                    # Ticker looks US, verify company name
                    if self._is_us_company(company):
                        us_entities.append(entity)
            
            if not us_entities:
                # Also check query for US company names
                tickers = []
                for name, ticker in self.name_to_ticker.items():
                    if name in query and ticker not in [e.get("ticker") for e in us_entities]:
                        tickers.append(ticker)
                        us_entities.append({
                            "company": name.title(),
                            "ticker": ticker,
                            "region": "US"
                        })
            
            if not us_entities:
                return {
                    "status": "no_symbols",
                    "worker": "FUNDAMENTALS_US",
                    "message": "No US companies detected in query",
                    "timestamp": datetime.now().isoformat()
                }
            
            print(f"      🇺🇸 Found {len(us_entities)} US companies")
            
            # Extract tickers
            tickers = []
            for entity in us_entities:
                ticker = entity.get("ticker", "")
                # Clean ticker
                clean_ticker = ticker.split('.')[0].upper()
                if clean_ticker and clean_ticker not in tickers:
                    tickers.append(clean_ticker)
            
            # Fetch data concurrently
            async def fetch_ticker(ticker):
                loop = asyncio.get_running_loop()
                return await loop.run_in_executor(
                    None, 
                    self._fetch_sync, 
                    ticker, 
                    yf
                )

            tasks = [fetch_ticker(t) for t in tickers]
            results = await asyncio.gather(*tasks, return_exceptions=True)

            # Process results
            data = {}
            for ticker, result in zip(tickers, results):
                if isinstance(result, Exception):
                    data[ticker] = {"error": str(result)}
                else:
                    data[ticker] = result

            return {
                "status": "success",
                "worker": "FUNDAMENTALS_US",
                "data": data,
                "timestamp": datetime.now().isoformat()
            }

        except Exception as e:
            return {
                "status": "error",
                "worker": "FUNDAMENTALS_US",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }

    def _fetch_sync(self, ticker: str, yf) -> Dict[str, Any]:
        """Fetch data synchronously using yfinance"""
        
        try:
            t = yf.Ticker(ticker)
            info = t.info if hasattr(t, 'info') else {}

            # Verify this is actually a US company
            if info:
                country = info.get("country", "")
                if country and country != "United States":
                    return {
                        "error": f"Company is from {country}, not United States",
                        "skipped": True
                    }
            
            # Check if we got valid data
            if not info or 'regularMarketPrice' not in info:
                # Try fetching history as fallback
                hist = t.history(period="1d")
                if not hist.empty:
                    price = hist['Close'].iloc[-1]
                else:
                    return {"error": "No data available"}
            else:
                price = info.get("regularMarketPrice")

            # Extract comprehensive fundamentals
            data = {
                "ticker": ticker,
                "name": info.get("shortName") or info.get("longName") or ticker,
                "source": "yfinance",
                
                # Price data
                "price": self._safe_round(price, 2) if price else None,
                
                # Valuation ratios
                "pe_ratio": self._safe_round(info.get("trailingPE"), 2),
                "forward_pe": self._safe_round(info.get("forwardPE"), 2),
                "pb_ratio": self._safe_round(info.get("priceToBook"), 2),
                "ps_ratio": self._safe_round(info.get("priceToSalesTrailing12Months"), 2),
                
                # Profitability
                "roe": self._safe_round(info.get("returnOnEquity", 0) * 100, 2) if info.get("returnOnEquity") else None,
                "roa": self._safe_round(info.get("returnOnAssets", 0) * 100, 2) if info.get("returnOnAssets") else None,
                "profit_margin": self._safe_round(info.get("profitMargins", 0) * 100, 2) if info.get("profitMargins") else None,
                
                # Financial health
                "market_cap": self._format_market_cap(info.get("marketCap")),
                "book_value": self._safe_round(info.get("bookValue"), 2),
                "debt_to_equity": self._safe_round(info.get("debtToEquity"), 2),
                "current_ratio": self._safe_round(info.get("currentRatio"), 2),
                
                # Dividends
                "dividend_yield": self._safe_round(info.get("dividendYield", 0) * 100, 2) if info.get("dividendYield") else None,
                
                # Earnings
                "eps": self._safe_round(info.get("trailingEps"), 2),
                "revenue_ttm": self._format_large_number(info.get("totalRevenue")),
                "earnings_ttm": self._format_large_number(info.get("ebitda")),
                
                # Growth
                "revenue_growth": self._safe_round(info.get("revenueGrowth", 0) * 100, 2) if info.get("revenueGrowth") else None,
                "earnings_growth": self._safe_round(info.get("earningsGrowth", 0) * 100, 2) if info.get("earningsGrowth") else None,
            }

            return data

        except Exception as e:
            return {"error": f"Failed to fetch {ticker}: {str(e)}"}

    def _safe_round(self, value, decimals):
        """Safely round a value"""
        try:
            if value is not None:
                return round(float(value), decimals)
        except:
            pass
        return None

    def _format_market_cap(self, market_cap):
        """Format market cap in readable form"""
        try:
            if market_cap is None:
                return None
            
            mc = float(market_cap)
            
            if mc >= 1e12:
                return f"${mc/1e12:.2f}T"
            elif mc >= 1e9:
                return f"${mc/1e9:.2f}B"
            elif mc >= 1e6:
                return f"${mc/1e6:.2f}M"
            else:
                return f"${mc:.0f}"
        except:
            return None
    
    def _format_large_number(self, value):
        """Format large numbers"""
        try:
            if value is None:
                return None
            
            v = float(value)
            
            if v >= 1e9:
                return f"${v/1e9:.2f}B"
            elif v >= 1e6:
                return f"${v/1e6:.2f}M"
            else:
                return f"${v:.0f}"
        except:
            return None