"""Entity Resolution Layer

Deterministically extracts and resolves entities from queries.
Separates concerns: planner does intent, resolver does entities.
"""
import re
from typing import List, Dict
from financial_intelligence.utils.company_lookup import find_companies_in_text


class EntityResolver:
    """Resolves companies, tickers, and other entities from queries"""
    
    def __init__(self):
        # Indian stock mappings
        self.indian_companies = {
            # Large Cap
            "reliance": "RELIANCE.NS",
            "tcs": "TCS.NS",
            "infosys": "INFY.NS",
            "hdfc bank": "HDFCBANK.NS",
            "icici bank": "ICICIBANK.NS",
            "sbi": "SBIN.NS",
            "itc": "ITC.NS",
            "wipro": "WIPRO.NS",
            "bharti airtel": "BHARTIARTL.NS",
            "mrf": "MRF.NS",
            "hdfc": "HDFC.NS",
            "kotak bank": "KOTAKBANK.NS",
            "axis bank": "AXISBANK.NS",
            "hindustan unilever": "HINDUNILVR.NS",
            "nestle": "NESTLEIND.NS",
            "asian paints": "ASIANPAINT.NS",
            "britannia": "BRITANNIA.NS",
            "maruti": "MARUTI.NS",
            "tata motors": "TATAMOTORS.NS",
            "mahindra": "M&M.NS",
            "hero motocorp": "HEROMOTOCO.NS",
            "bajaj auto": "BAJAJ-AUTO.NS",
            "tvs motor": "TVSMOTOR.NS",
            "eicher motors": "EICHERMOT.NS",
            "ashok leyland": "ASHOKLEY.NS",
            "apollo tyres": "APOLLOTYRE.NS",
            "ceat": "CEATLTD.NS",
            "balkrishna": "BALKRISIND.NS",
            
            # IT Services
            "hcl tech": "HCLTECH.NS",
            "tech mahindra": "TECHM.NS",
            "mindtree": "MINDTREE.NS",
            "lti": "LTI.NS",
            "hexaware": "HEXAWARE.NS",
            "persistent": "PERSISTENT.NS",
            "mphasis": "MPHASIS.NS",
            "coforge": "COFORGE.NS",
            "tata elxsi": "TATAELXSI.NS",
            "sonata software": "SONATSOFTW.NS",
            "polaris": "POLARIS.NS",
            "infibeam": "INFIBEAM.NS",
            
            # Pharma
            "sun pharma": "SUNPHARMA.NS",
            "dr reddy": "DRREDDY.NS",
            "cipla": "CIPLA.NS",
            "lupin": "LUPIN.NS",
            "aurobindo pharma": "AUROPHARMA.NS",
            "divis labs": "DIVISLAB.NS",
            "torrent pharma": "TORNTPHARM.NS",
            "alkem labs": "ALKEM.NS",
            "mankind pharma": "MANKIND.NS",
            "glenmark": "GLENSMARK.NS",
            
            # Banking & Finance
            "bajaj finance": "BAJFINANCE.NS",
            "bajaj finserv": "BAJAJFINSV.NS",
            "cholamandalam": "CHOLAHLDNG.NS",
            "shriram finance": "SRF.NS",
            "mahindra finance": "MAHINDRAFIN.NS",
            "l&t finance": "L&TFH.NS",
            "muthoot finance": "MUTHOOTFIN.NS",
            "manappuram": "MANAPPURAM.NS",
            "cholamandalam investment": "CHOLAINVEST.NS",
            "idf first": "IDFCFIRSTB.NS",
            "rbl bank": "RBLBANK.NS",
            "federal bank": "FEDERALBNK.NS",
            "indusind bank": "INDUSINDBK.NS",
            "yes bank": "YESBANK.NS",
            "bandhan bank": "BANDHANBNK.NS",
            "dhanlaxmi bank": "DHANBANK.NS",
            "uco bank": "UCOBANK.NS",
            "central bank": "CENTRALBK.NS",
            "punjab bank": "PUNJABBANK.NS",
            "indian bank": "INDIANB.NS",
            "union bank": "UNIONBANK.NS",
            "canara bank": "CANBK.NS",
            "bank of baroda": "BANKBARODA.NS",
            "bank of india": "BANKINDIA.NS",
            
            # Energy & Oil
            "ongc": "ONGC.NS",
            "oil india": "OILINDIA.NS",
            "gail": "GAIL.NS",
            "bpcl": "BPCL.NS",
            "hpcl": "HINDPETRO.NS",
            "ioc": "IOC.NS",
            "reliiance power": "RPOWER.NS",
            "tata power": "TATAPOWER.NS",
            "ntpc": "NTPC.NS",
            "power grid": "POWERGRID.NS",
            "nhpc": "NHPC.NS",
            "sjvn": "SJVN.NS",
            "thermal power": "THERPOWER.NS",
            
            # Metals & Mining
            "tata steel": "TATASTEEL.NS",
            "jsw steel": "JSWSTEEL.NS",
            "sail": "SAIL.NS",
            "hindalco": "HINDALCO.NS",
            "vedanta": "VEDL.NS",
            "coal india": "COALINDIA.NS",
            "nmdc": "NMDC.NS",
            "moil": "MOIL.NS",
            "hindustan copper": "HINDCOPPER.NS",
            "hindustan zinc": "HINDZINC.NS",
            "national aluminium": "NATIONALUM.NS",
            "jindal steel": "JINDALSTEL.NS",
            "jindal steel & power": "JINDALSTEL.NS",
            
            # Cement & Construction
            "ultratech cement": "ULTRACEMCO.NS",
            "shree cement": "SHREECEM.NS",
            "ambuja cement": "AMBUJACEM.NS",
            "acc": "ACC.NS",
            "dalmia bharat": "DALMIABHA.NS",
            "j k cement": "JKCEMENT.NS",
            "india cements": "INDIACEM.NS",
            "ramco cements": "RAMCOCEM.NS",
            "the ramco cements": "RAMCOCEM.NS",
            
            # Infrastructure
            "larsen & toubro": "LT.NS",
            "lt": "LT.NS",
            "adani ports": "ADANIPORTS.NS",
            "adani enterprises": "ADANIENT.NS",
            "adani power": "ADANIPOWER.NS",
            "adani green": "ADANIGREEN.NS",
            "adani total gas": "ATGL.NS",
            "adani transmission": "ADANITRANS.NS",
            "adani wilmar": "AWL.NS",
            "gvk power": "GVKPIL.NS",
            "irb infrastructure": "IRB.NS",
            "sadhbav engineering": "SAHHELI.NS",
            "ashoka buildcon": "ASHOKA.NS",
            "ncc": "NCC.NS",
            "simplex infra": "SIMPLEXINFRA.NS",
            "hcc": "HCC.NS",
            
            # Consumer Durables
            "tata consumer": "TATACONSUM.NS",
            "godrej consumer": "GODREJCP.NS",
            "colgate": "COLPAL.NS",
            "dabur": "DABUR.NS",
            "emami": "EMAMI.NS",
            "jyothy labs": "JYOTHYLAB.NS",
            "himalaya": "HIMALAYA.NS",
            
            # Telecom
            "vodafone idea": "IDEA.NS",
            "tata communications": "TATACOMM.NS",
            "tata teleservices": "TTML.NS",
            "rel communications": "RCOM.NS",
            "indus towers": "INDUSTOWER.NS",
            
            # Media & Entertainment
            "zeel": "ZEEL.NS",
            "sun tv": "SUNTV.NS",
            "pvr": "PVR.NS",
            "inox": "INOXLEISUR.NS",
            "dish tv": "DISHTV.NS",
            "den networks": "DENNETHC.NS",
            "tv today": "TVTODAY.NS",
            "new delhi tv": "NDTV.NS",
            
            # Retail
            "avenue supermarts": "AVENUESUPER.NS",
            "d mart": "AVENUESUPER.NS",
            "future retail": "FUTURERET.NS",
            "spencer": "SPENCERS.NS",
            "v2 retail": "V2RETAIL.NS",
            "tata retail": "TATACONSUM.NS",
            
            # Other
            "tata chemicals": "TATACHEM.NS",
            "tata coffee": "TATACOFFEE.NS",
            "tata global": "TATAGLOBAL.NS",
            "tata steel bsl": "TATASTLBSL.NS",
            "tata sponge": "TATASPONGE.NS",
            "tata metaliks": "TATAMETALI.NS",
        }
        
        # US stock mappings
        self.us_companies = {
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
            "qualcomm": "QCOM",
            "broadcom": "AVGO",
            "texas instruments": "TXN",
            "micron": "MU",
            "applied materials": "AMAT",
            
            # Finance
            "berkshire hathaway": "BRK-A",
            "jpmorgan": "JPM",
            "bank of america": "BAC",
            "wells fargo": "WFC",
            "goldman sachs": "GS",
            "morgan stanley": "MS",
            "citi": "C",
            "american express": "AXP",
            "blackrock": "BLK",
            "visa": "V",
            "mastercard": "MA",
            "paypal": "PYPL",
            "square": "SQ",
            "coinbase": "COIN",
            
            # Healthcare
            "johnson & johnson": "JNJ",
            "pfizer": "PFE",
            "moderna": "MRNA",
            "abbott": "ABT",
            "merck": "MRK",
            "eli lilly": "LLY",
            "bristol myers": "BMY",
            "abbvie": "ABBV",
            "amgen": "AMGN",
            "gilead": "GILD",
            "biogen": "BIIB",
            "regeneron": "REGN",
            
            # Consumer
            "procter & gamble": "PG",
            "coca cola": "KO",
            "pepsi": "PEP",
            "walmart": "WMT",
            "costco": "COST",
            "home depot": "HD",
            "lowe's": "LOW",
            "target": "TGT",
            "mcdonald's": "MCD",
            "starbucks": "SBUX",
            "nike": "NKE",
            "lululemon": "LULU",
            "under armour": "UAA",
            
            # Energy
            "exxon mobil": "XOM",
            "chevron": "CVX",
            "conocophillips": "COP",
            "schlumberger": "SLB",
            "halliburton": "HAL",
            "bp": "BP",
            "shell": "SHEL",
            "total": "TTE",
            
            # Industrial
            "boeing": "BA",
            "airbus": "EADSY",
            "lockheed martin": "LMT",
            "general electric": "GE",
            "3m": "MMM",
            "caterpillar": "CAT",
            "honeywell": "HON",
            "united technologies": "RTX",
            "raytheon": "RTX",
        }
        
        # Index mappings
        self.indices = {
            # Indian Indices
            "nifty": "^NSEI",
            "nifty 50": "^NSEI",
            "sensex": "^BSESN",
            "bank nifty": "^NSEBANK",
            "nifty it": "^NSEIIT",
            "nifty pharma": "^CNXPHARMA",
            "nifty fmcg": "^CNXFMCG",
            "nifty auto": "^CNXAUTO",
            "nifty metal": "^CNXMETAL",
            "nifty energy": "^CNXENERGY",
            "nifty psu bank": "^NSEBANK",
            "nifty pvt bank": "^NSEBANK",
            "nifty realty": "^CNXREALTY",
            "nifty midsel 50": "^NSEMID50",
            "nifty next 50": "^NSMIDCP",
            "nifty smallcap 100": "^NSMALLCAP100",
            "nifty smallcap 250": "^NSMALLCAP250",
            
            # Global Indices
            "s&p 500": "^GSPC",
            "sp 500": "^GSPC",
            "dow jones": "^DJI",
            "dow": "^DJI",
            "nasdaq": "^IXIC",
            "nasdaq composite": "^IXIC",
            "ftse 100": "^FTSE",
            "ftse": "^FTSE",
            "dax": "^GDAXI",
            "hang seng": "^HSI",
            "hong kong": "^HSI",
            "nikkei": "^N225",
            "nikkei 225": "^N225",
            "shanghai composite": "000001.SS",
            "china": "000001.SS",
            "tsx": "^GSPTSE",
            "s&p tsx": "^GSPTSE",
            "euro stoxx 50": "^STOXX50E",
            "cac 40": "^FCHI",
            "ftse mib": "^FTSEMIB.MI",
            "ibex 35": "^IBEX",
            "aord": "^AORD",
            "all ordinaries": "^AORD",
            "asx 200": "^AXJO",
        }
        
        # Commodities
        self.commodities = {
            "crude oil": "CL=F",
            "oil": "CL=F",
            "wti": "CL=F",
            "brent": "BZ=F",
            "gold": "GC=F",
            "silver": "SI=F",
            "copper": "HG=F",
            "platinum": "PL=F",
            "palladium": "PA=F",
            "natural gas": "NG=F",
            "gas": "NG=F",
            "gasoline": "RB=F",
            "heating oil": "HO=F",
            "corn": "ZC=F",
            "wheat": "ZW=F",
            "soybeans": "ZS=F",
            "coffee": "KC=F",
            "sugar": "SB=F",
            "cotton": "CT=F",
            "cocoa": "CC=F",
            "lumber": "LBS=F",
            "orange juice": "OJ=F",
            "live cattle": "LE=F",
            "lean hogs": "HE=F",
        }
        
        # Cryptocurrencies
        self.crypto = {
            "bitcoin": "BTC-USD",
            "btc": "BTC-USD",
            "ethereum": "ETH-USD",
            "eth": "ETH-USD",
            "ripple": "XRP-USD",
            "xrp": "XRP-USD",
            "litecoin": "LTC-USD",
            "ltc": "LTC-USD",
            "cardano": "ADA-USD",
            "ada": "ADA-USD",
            "solana": "SOL-USD",
            "sol": "SOL-USD",
            "dogecoin": "DOGE-USD",
            "doge": "DOGE-USD",
        }
        
        # Forex
        self.forex = {
            "eur/usd": "EURUSD=X",
            "euro": "EURUSD=X",
            "gbp/usd": "GBPUSD=X",
            "british pound": "GBPUSD=X",
            "usd/jpy": "USDJPY=X",
            "japanese yen": "USDJPY=X",
            "usd/chf": "USDCHF=X",
            "swiss franc": "USDCHF=X",
            "aud/usd": "AUDUSD=X",
            "australian dollar": "AUDUSD=X",
            "usd/cad": "USDCAD=X",
            "canadian dollar": "USDCAD=X",
            "nzd/usd": "NZDUSD=X",
            "new zealand dollar": "NZDUSD=X",
        }
        
        # Bonds
        self.bonds = {
            "10 year treasury": "^TNX",
            "us 10y": "^TNX",
            "30 year treasury": "^TYX",
            "us 30y": "^TYX",
            "2 year treasury": "^FVX",
            "us 2y": "^FVX",
            "5 year treasury": "^FVX",
            "us 5y": "^FVX",
            "vix": "^VIX",
            "volatility index": "^VIX",
        }
    
    def resolve(self, query: str) -> List[Dict[str, str]]:
        """
        Resolve entities from query
        
        Returns:
            List of dicts with keys: company, ticker, type, region
        """
        query_lower = query.lower()
        entities = []
        
        # 1. PRIORITY: Extract explicit ticker patterns
        # Patterns like "ticker NSE: ADANIENT" or "BSE:ADANIENT" or "ADANIENT.NS"
        
        # Pattern 1: "NSE: SYMBOL" or "BSE: SYMBOL"
        ticker_patterns = [
            r'(?:NSE|BSE)\s*:\s*([A-Z0-9]+)',  # NSE: ADANIENT
            r'ticker\s+(?:NSE|BSE)\s*:\s*([A-Z0-9]+)',  # ticker NSE: ADANIENT
            r'\b([A-Z0-9]{3,})\.NS\b',  # ADANIENT.NS
            r'\b([A-Z0-9]{3,})\.BO\b',  # ADANIENT.BO
        ]
        
        for pattern in ticker_patterns:
            matches = re.findall(pattern, query)
            for match in matches:
                ticker = match.upper()
                # Add .NS suffix if not present
                if not ticker.endswith(('.NS', '.BO')):
                    ticker_with_suffix = f"{ticker}.NS"
                else:
                    ticker_with_suffix = ticker
                
                # Try to find company name from context
                company_name = self._extract_company_name(query, ticker)
                
                entities.append({
                    "company": company_name or ticker,
                    "ticker": ticker_with_suffix,
                    "type": "stock",
                    "region": "IN"
                })
        
        if entities:
            return self._deduplicate_entities(entities)
        
        # 2. Try CSV-backed lookup
        csv_results = find_companies_in_text(query)
        if csv_results:
            for result in csv_results:
                entities.append({
                    "company": result['name'],
                    "ticker": result['ticker'],
                    "type": "stock",
                    "region": self._detect_region(result['ticker'])
                })
            return self._deduplicate_entities(entities)
        
        # 3. Check known company mappings
        for name, ticker in self.indian_companies.items():
            if name in query_lower:
                entities.append({
                    "company": name.title(),
                    "ticker": ticker,
                    "type": "stock",
                    "region": "IN"
                })
        
        for name, ticker in self.us_companies.items():
            if name in query_lower:
                entities.append({
                    "company": name.title(),
                    "ticker": ticker,
                    "type": "stock",
                    "region": "US"
                })
        
        # ... (keep rest of your existing logic for indices, commodities, etc.)
        
        return self._deduplicate_entities(entities)
    
    def _extract_company_name(self, query: str, ticker: str) -> str:
        """
        Extract company name from query context
        
        Examples:
        "News analysis for Adani Enterprises Limited - ticker NSE: ADANIENT"
        -> Extract "Adani Enterprises Limited"
        """
        # Pattern: "for <COMPANY NAME> - ticker"
        pattern1 = r'for\s+([A-Za-z\s&\.]+?)\s*[-–]\s*ticker'
        match = re.search(pattern1, query, re.IGNORECASE)
        if match:
            return match.group(1).strip().title()
        
        # Pattern: "<COMPANY NAME> - ticker NSE:"
        pattern2 = r'([A-Za-z\s&\.]+?)\s*[-–]\s*ticker\s+(?:NSE|BSE)'
        match = re.search(pattern2, query, re.IGNORECASE)
        if match:
            return match.group(1).strip().title()
        
        # Pattern: Look for capitalized words before ticker mention
        words_before_ticker = query.split('ticker')[0] if 'ticker' in query.lower() else query
        capitalized = re.findall(r'\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*(?:\s+Limited)?)\b', words_before_ticker)
        if capitalized:
            # Take the longest match (likely full company name)
            return max(capitalized, key=len)
        
        return ticker
    
    def _deduplicate_entities(self, entities: List[Dict]) -> List[Dict]:
        """Remove duplicate entities based on ticker"""
        seen = set()
        unique = []
        for e in entities:
            key = e["ticker"]
            if key not in seen:
                seen.add(key)
                unique.append(e)
        return unique
    
    def _detect_region(self, ticker: str) -> str:
        """Detect region from ticker suffix"""
        if ticker.endswith('.NS') or ticker.endswith('.BO'):
            return 'IN'
        elif ticker.startswith('^'):
            if 'NSE' in ticker or 'BSE' in ticker:
                return 'IN'
            return 'US'
        else:
            return 'US'


# Singleton instance
_resolver = EntityResolver()

def resolve_entities(query: str) -> List[Dict[str, str]]:
    """Convenience function to resolve entities"""
    return _resolver.resolve(query)