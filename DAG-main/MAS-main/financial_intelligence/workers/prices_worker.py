import yfinance as yf
from typing import Dict, Any, List
from datetime import datetime, timedelta
import asyncio


class PricesWorker:
    """Fetches market prices and historical data from Yahoo Finance"""
    
    def __init__(self):
        # Symbol mappings for Indian and global assets
        self.SYMBOL_MAP = {
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
            
            # Indian Stocks (NSE) - Large Cap
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
            "mrf": "MRF.NS",
            "balkrishna": "BALKRISIND.NS",
            
            # Indian Stocks (NSE) - IT Services
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
            
            # Indian Stocks (NSE) - Pharma
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
            
            # Indian Stocks (NSE) - Banking & Finance
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
            
            # Indian Stocks (NSE) - Energy & Oil
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
            
            # Indian Stocks (NSE) - Metals & Mining
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
            
            # Indian Stocks (NSE) - Cement & Construction
            "ultratech cement": "ULTRACEMCO.NS",
            "shree cement": "SHREECEM.NS",
            "ambuja cement": "AMBUJACEM.NS",
            "acc": "ACC.NS",
            "dalmia bharat": "DALMIABHA.NS",
            "j k cement": "JKCEMENT.NS",
            "india cements": "INDIACEM.NS",
            "ramco cements": "RAMCOCEM.NS",
            "the ramco cements": "RAMCOCEM.NS",
            
            # Indian Stocks (NSE) - Infrastructure
            "larsen & toubro": "LT.NS",
            "lt": "LT.NS",
            "adani ports": "ADANIPORTS.NS",
            "gvk power": "GVKPIL.NS",
            "irb infrastructure": "IRB.NS",
            "sadhbav engineering": "SAHHELI.NS",
            "ashoka buildcon": "ASHOKA.NS",
            "ncc": "NCC.NS",
            "simplex infra": "SIMPLEXINFRA.NS",
            "hcc": "HCC.NS",
            
            # Indian Stocks (NSE) - Consumer Durables
            "tata consumer": "TATACONSUM.NS",
            "godrej consumer": "GODREJCP.NS",
            "colgate": "COLPAL.NS",
            "dabur": "DABUR.NS",
            "emami": "EMAMI.NS",
            "jyothy labs": "JYOTHYLAB.NS",
            "himalaya": "HIMALAYA.NS",
            
            # Indian Stocks (NSE) - Telecom
            "vodafone idea": "IDEA.NS",
            "tata communications": "TATACOMM.NS",
            "tata teleservices": "TTML.NS",
            "rel communications": "RCOM.NS",
            "indus towers": "INDUSTOWER.NS",
            
            # Indian Stocks (NSE) - Media & Entertainment
            "zeel": "ZEEL.NS",
            "sun tv": "SUNTV.NS",
            "pvr": "PVR.NS",
            "inox": "INOXLEISUR.NS",
            "dish tv": "DISHTV.NS",
            "den networks": "DENNETHC.NS",
            "tv today": "TVTODAY.NS",
            "new delhi tv": "NDTV.NS",
            
            # Indian Stocks (NSE) - Retail
            "avenue supermarts": "AVENUESUPER.NS",
            "d mart": "AVENUESUPER.NS",
            "future retail": "FUTURERET.NS",
            "spencer": "SPENCERS.NS",
            "v2 retail": "V2RETAIL.NS",
            "tata retail": "TATACONSUM.NS",
            
            # Indian Stocks (NSE) - Other
            "tata chemicals": "TATACHEM.NS",
            "tata coffee": "TATACOFFEE.NS",
            "tata global": "TATAGLOBAL.NS",
            "tata steel bsl": "TATASTLBSL.NS",
            "tata sponge": "TATASPONGE.NS",
            "tata metaliks": "TATAMETALI.NS",
            
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
            
            # US Stocks - Tech Giants
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
            "nvidia": "NVDA",
            
            # US Stocks - Finance
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
            
            # US Stocks - Healthcare
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
            
            # US Stocks - Consumer
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
            
            # US Stocks - Energy
            "exxon mobil": "XOM",
            "chevron": "CVX",
            "conocophillips": "COP",
            "schlumberger": "SLB",
            "halliburton": "HAL",
            "bp": "BP",
            "shell": "SHEL",
            "total": "TTE",
            
            # US Stocks - Industrial
            "boeing": "BA",
            "airbus": "EADSY",
            "lockheed martin": "LMT",
            "general electric": "GE",
            "3m": "MMM",
            "caterpillar": "CAT",
            "honeywell": "HON",
            "united technologies": "RTX",
            "raytheon": "RTX",
            
            # Commodities
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
            
            # Cryptocurrencies (if supported)
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
            
            # Forex Major Pairs
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
            
            # Bonds
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
    
    async def fetch(self, intent_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Fetch price data for stocks/indices/commodities
        
        Args:
            intent_data: Contains query and detected symbols
            
        Returns:
            Dict with price data and historical trends
        """
        try:
            query = intent_data.get("query", "").lower()
            symbols = self._extract_symbols(query)
            
            if not symbols:
                return {
                    "status": "no_symbols",
                    "worker": "PRICES",
                    "message": "No tradeable symbols detected in query"
                }
            
            # Fetch data for all symbols
            results = {}
            for name, symbol in symbols.items():
                try:
                    data = await self._fetch_symbol_data(symbol, name)
                    results[name] = data
                except Exception as e:
                    results[name] = {"error": str(e)}
            
            return {
                "status": "success",
                "worker": "PRICES",
                "data": results,
                "timestamp": datetime.now().isoformat(),
                "symbols_fetched": list(results.keys())
            }
            
        except Exception as e:
            return {
                "status": "error",
                "worker": "PRICES",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    def _extract_symbols(self, query: str) -> Dict[str, str]:
        """Extract symbol identifiers from query"""
        detected = {}
        
        for name, symbol in self.SYMBOL_MAP.items():
            if name in query:
                detected[name] = symbol
        
        return detected
    
    async def _fetch_symbol_data(self, symbol: str, name: str) -> Dict[str, Any]:
        """Fetch data for a single symbol"""
        
        # Run in executor to avoid blocking
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None,
            self._fetch_symbol_sync,
            symbol,
            name
        )
    
    def _fetch_symbol_sync(self, symbol: str, name: str) -> Dict[str, Any]:
        """Synchronous fetch for a single symbol"""
        
        ticker = yf.Ticker(symbol)
        
        # Get current info
        info = ticker.info
        
        # Get historical data (last 3 months)
        end_date = datetime.now()
        start_date = end_date - timedelta(days=90)
        hist = ticker.history(start=start_date, end=end_date)
        
        if hist.empty:
            return {"error": "No historical data available"}
        
        # Calculate metrics
        current_price = hist['Close'].iloc[-1]
        prev_close = hist['Close'].iloc[-2] if len(hist) > 1 else current_price
        
        change = current_price - prev_close
        change_pct = (change / prev_close * 100) if prev_close != 0 else 0
        
        # 52-week high/low
        week_52_high = hist['High'].max()
        week_52_low = hist['Low'].min()
        
        # Volatility (standard deviation of daily returns)
        returns = hist['Close'].pct_change().dropna()
        volatility = returns.std() * 100  # As percentage
        
        # Volume analysis
        avg_volume = hist['Volume'].mean()
        current_volume = hist['Volume'].iloc[-1]
        
        return {
            "name": name,
            "symbol": symbol,
            "current_price": round(float(current_price), 2),
            "previous_close": round(float(prev_close), 2),
            "change": round(float(change), 2),
            "change_pct": round(float(change_pct), 2),
            "52_week_high": round(float(week_52_high), 2),
            "52_week_low": round(float(week_52_low), 2),
            "volatility": round(float(volatility), 2),
            "avg_volume": int(avg_volume),
            "current_volume": int(current_volume),
            "currency": info.get("currency", "USD"),
            "market": info.get("market", "Unknown"),
            "data_points": len(hist)
        }