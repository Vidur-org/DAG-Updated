"""
make a web agent, as of now provide dummy output, use pydantic, Beautiful soup, requests
"""
from typing import List, Optional,Dict
from datetime import datetime
from node import SearchResult
import re
import math
from typing import List, Optional, Dict, Any
from dataclasses import dataclass
from datetime import datetime
import requests
from bs4 import BeautifulSoup
import yfinance as yf
import pandas as pd
from pydantic import BaseModel, Field
import pandas as pd
from datetime import datetime
import requests


class QuarterFundamentals(BaseModel):
    as_of_date: datetime = Field(..., description="Quarter end date")
    total_revenue: Optional[float] = None
    gross_profit: Optional[float] = None
    operating_income: Optional[float] = None
    net_income: Optional[float] = None
    operating_cash_flow: Optional[float] = None
    free_cash_flow: Optional[float] = None
    total_assets: Optional[float] = None
    total_liabilities: Optional[float] = None
    total_equity: Optional[float] = None
    raw: Dict[str, Any] = Field(default_factory=dict)


class StockFundamentals(BaseModel):
    symbol: str                      # NSE symbol, e.g. RELIANCE
    yahoo_symbol: str                # Yahoo symbol, e.g. RELIANCE.NS
    company_name: Optional[str] = None
    currency: Optional[str] = None
    quarters: List[QuarterFundamentals]


class YahooFinanceAgent:
    def __init__(self):
        self.name = "YahooFinanceAgent"

    async def get_fundamentals_nse(
        self,
        nse_symbol: str,
        num_quarters: int = 8
    ) -> StockFundamentals:
        yahoo_symbol = f"{nse_symbol}.NS"
        ticker = yf.Ticker(yahoo_symbol)

        # ❗ FIXED: no "or DataFrame()" on a DataFrame
        q_income = ticker.quarterly_income_stmt
        if q_income is None:
            q_income = pd.DataFrame()

        q_balance = ticker.quarterly_balance_sheet
        if q_balance is None:
            q_balance = pd.DataFrame()

        q_cash = ticker.quarterly_cashflow
        if q_cash is None:
            q_cash = pd.DataFrame()

        # Take last `num_quarters` columns (most recent first)
        def last_n_cols(df: pd.DataFrame) -> pd.DataFrame:
            if df.empty:
                return df
            # DataFrames from yfinance usually have columns newest→oldest already
            return df.iloc[:, :num_quarters]

        q_income = last_n_cols(q_income)
        q_balance = last_n_cols(q_balance)
        q_cash = last_n_cols(q_cash)

        quarters: List[QuarterFundamentals] = []

        # Collect all quarter columns that appear in any of the three tables
        all_cols = []
        for df in (q_income, q_balance, q_cash):
            if not df.empty:
                all_cols.extend(list(df.columns))

        # Deduplicate while preserving order
        seen = set()
        ordered_cols = []
        for c in all_cols:
            if c not in seen:
                seen.add(c)
                ordered_cols.append(c)

        for col in ordered_cols[:num_quarters]:
            # yfinance columns are usually like Timestamp or str
            as_of_date = pd.to_datetime(col).to_pydatetime() if not isinstance(col, datetime) else col

            def get_metric(df: pd.DataFrame, label: str) -> Optional[float]:
                if df.empty:
                    return None
                if label not in df.index or col not in df.columns:
                    return None
                val = df.at[label, col]
                if pd.isna(val):
                    return None
                return float(val)

            q = QuarterFundamentals(
                as_of_date=as_of_date,
                total_revenue=get_metric(q_income, "Total Revenue")
                              or get_metric(q_income, "TotalRevenue"),
                gross_profit=get_metric(q_income, "Gross Profit")
                             or get_metric(q_income, "GrossProfit"),
                operating_income=get_metric(q_income, "Operating Income")
                                 or get_metric(q_income, "OperatingIncome"),
                net_income=get_metric(q_income, "Net Income")
                           or get_metric(q_income, "NetIncome"),
                operating_cash_flow=get_metric(q_cash, "Total Cash From Operating Activities")
                                     or get_metric(q_cash, "TotalCashFromOperatingActivities"),
                free_cash_flow=get_metric(q_cash, "Free Cash Flow")
                               or get_metric(q_cash, "FreeCashFlow"),
                total_assets=get_metric(q_balance, "Total Assets")
                              or get_metric(q_balance, "TotalAssets"),
                total_liabilities=get_metric(q_balance, "Total Liabilities Net Minority Interest")
                                   or get_metric(q_balance, "TotalLiab"),
                total_equity=get_metric(q_balance, "Total Stockholder Equity")
                             or get_metric(q_balance, "TotalStockholderEquity"),
                raw={
                    "income": q_income[col].to_dict() if (not q_income.empty and col in q_income.columns) else {},
                    "balance": q_balance[col].to_dict() if (not q_balance.empty and col in q_balance.columns) else {},
                    "cashflow": q_cash[col].to_dict() if (not q_cash.empty and col in q_cash.columns) else {},
                }
            )
            quarters.append(q)

        # Get company name with BeautifulSoup (optional sugar)
        company_name = None
        try:
            yahoo_url = f"https://finance.yahoo.com/quote/{yahoo_symbol}"
            resp = requests.get(yahoo_url, timeout=5)
            if resp.ok:
                soup = BeautifulSoup(resp.text, "html.parser")
                h1 = soup.find("h1")
                if h1:
                    company_name = h1.get_text(strip=True)
        except Exception:
            pass

        info = ticker.info or {}
        currency = info.get("currency")

        return StockFundamentals(
            symbol=nse_symbol,
            yahoo_symbol=yahoo_symbol,
            company_name=company_name,
            currency=currency,
            quarters=quarters
        )

    async def search(self, queries: List[str]) -> Dict[str, List[SearchResult]]:
        """
        For each NSE symbol in `queries`, fetch past 8 quarters of fundamentals
        and wrap a summary into SearchResult (dummy-ish but structured).
        """
        print(f"  [{self.name}] Fetching fundamentals for: {queries}")
        results: Dict[str, List[SearchResult]] = {}

        for symbol in queries:
            try:
                fundamentals = await self.get_fundamentals_nse(symbol, num_quarters=8)

                # Small text summary for SearchResult.snippet
                lines = [
                    f"Symbol: {fundamentals.symbol} ({fundamentals.yahoo_symbol})",
                    f"Company: {fundamentals.company_name or 'N/A'}",
                    f"Currency: {fundamentals.currency or 'N/A'}",
                    f"Quarters available: {len(fundamentals.quarters)}",
                ]
                if fundamentals.quarters:
                    latest = fundamentals.quarters[0]
                    lines.append(
                        f"Latest quarter ({latest.as_of_date.date()}): "
                        f"Revenue={latest.total_revenue}, NetIncome={latest.net_income}"
                    )

                snippet = "\n".join(lines)

                # You could stash the full Pydantic object in a custom field on SearchResult
                # or serialize it as JSON somewhere else in your pipeline.
                results[symbol] = [
                    SearchResult(
                        title=f"Fundamentals for {symbol} (last {len(fundamentals.quarters)} quarters)",
                        link=f"https://finance.yahoo.com/quote/{fundamentals.yahoo_symbol}/financials",
                        snippet=snippet,
                    )
                ]

            except Exception as e:
                # Fallback dummy result if something fails
                results[symbol] = [
                    SearchResult(
                        title=f"Error fetching fundamentals for '{symbol}'",
                        link="",
                        snippet=str(e),
                    )
                ]

        return results



class BM25Agent:
    def __init__(self):
        self.name = "BM25Agent"
        self.corpus: List[str] = []
        self.tokenized_corpus: List[List[str]] = []
        self.doc_lengths: List[int] = []
        self.avg_doc_len: float = 0
        self.doc_freqs: List[Dict[str, int]] = []
        self.idf: Dict[str, float] = {}
        
        # BM25 params
        self.k1 = 1.5
        self.b = 0.75

    def ingest(self, documents: List[str]):
        """Ingests raw text documents and builds the index."""
        self.corpus = documents
        self.tokenized_corpus = [self._tokenize(doc) for doc in documents]
        self.doc_lengths = [len(doc) for doc in self.tokenized_corpus]
        self.avg_doc_len = sum(self.doc_lengths) / len(documents) if documents else 0
        
        # Calculate Term Frequencies per doc
        self.doc_freqs = []
        for tokens in self.tokenized_corpus:
            freq = {}
            for token in tokens:
                freq[token] = freq.get(token, 0) + 1
            self.doc_freqs.append(freq)
            
        self._compute_idf()
        print(f"  [{self.name}] Ingested {len(documents)} documents.")

    def _tokenize(self, text: str) -> List[str]:
        # Simple whitespace tokenization + lowercasing
        return re.findall(r'\w+', text.lower())

    def _compute_idf(self):
        """Inverse Document Frequency"""
        idf = {}
        all_words = set(w for doc in self.tokenized_corpus for w in doc)
        N = len(self.corpus)
        
        for word in all_words:
            # Count how many docs contain this word
            n_q = sum(1 for doc in self.tokenized_corpus if word in doc)
            # Standard BM25 IDF formula
            idf[word] = math.log(((N - n_q + 0.5) / (n_q + 0.5)) + 1)
        self.idf = idf
    def search(self, query: str, top_k=3) -> List[SearchResult]:
        query_tokens = self._tokenize(query)
        scores = []

        for idx, doc_tokens in enumerate(self.tokenized_corpus):
            score = 0
            doc_len = self.doc_lengths[idx]
            
            for token in query_tokens:
                if token not in self.doc_freqs[idx]:
                    continue
                
                f = self.doc_freqs[idx][token]
                idf = self.idf.get(token, 0)
                
                numerator = idf * f * (self.k1 + 1)
                denominator = f + self.k1 * (1 - self.b + self.b * (doc_len / self.avg_doc_len))
                score += numerator / denominator
            
            scores.append((idx, score))

        # Sort by score descending
        scores.sort(key=lambda x: x[1], reverse=True)
        
        results = []
        for idx, score in scores[:top_k]:
            if score > 0:  # Only return relevant docs
                doc_text = self.corpus[idx]
                snippet = f"(BM25 score={score:.4f})\n" + doc_text[:200] + "..."
                results.append(
                    SearchResult(
                        title=f"Document {idx+1}",
                        link="",                  # no real link; keep empty
                        snippet=snippet,
                        score=round(score, 4),    # ✅ populate score field
                        content=doc_text          # ✅ store full doc text
                    )
                )
        if results or len(results) > 0:
            return results
        else:
            return None


    

if __name__ == "__main__":

    import asyncio

    agent = YahooFinanceAgent()

    async def main():
        # Example: RELIANCE, TCS, HDFCBANK etc.
        res = await agent.search(["RELIANCE", "TCS"])
        for symbol, items in res.items():
            print("\n=== ", symbol, " ===")
            for item in items:
                print(item.title)
                print(item.snippet)
                print(item.link)

    asyncio.run(main())

    print("\n--- Running BM25 Search ---")
    bm25 = BM25Agent()
    
    # Real text data
    docs = [
        "Tata Motors Group (Tata Motors) is a $37 billion organization. It is a leading global automobile manufacturing company.",
        "Tesla designs and manufactures electric vehicles (cars and trucks), battery energy storage from home to grid-scale, solar panels and solar roof tiles.",
        "Revenue for the automotive sector has increased significantly over the last 8 quarters due to high demand.",
        "The BM25 algorithm is a ranking function used by search engines to estimate the relevance of documents to a given search query."
    ]
    
    bm25.ingest(docs)
    query = "automotive revenue increase"
    rankings = bm25.search(query)
    
    for rank in rankings:
        print(f"Doc: {rank.title} | Score: {rank.score} | Preview: {rank.content}")
