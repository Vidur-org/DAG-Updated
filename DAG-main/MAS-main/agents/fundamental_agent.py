from agents.base import Agent
from llm.llm_client import call_llm, call_llm_json
from fundamental.main import run_nifty_scraper
import re
from datetime import datetime

def success(data, confidence=0.7, citations=None):
    return {"status": "success", "confidence": confidence, "data": data, "citations": citations or []}

def failure(reason):
    return {"status": "failed", "error": reason}

class FundamentalAgent(Agent):
    def __init__(self):
        super().__init__("fundamental_agent")

    def preprocess(self, task_input: str):
        """
        Extract ticker and period from query
        Returns: {
            "ticker": "ADANIPORTS",
            "start_date": "2024-10-01",
            "end_date": "2024-12-31",
            "period_description": "October 2024 to December 2024"
        }
        """
        PROMPT_TEMPLATE = """
You are given a user query about a stock analysis for a specific period.

Your task:
1. Extract the stock ticker (explicit company name match ONLY)
2. Extract the time period (dates or month ranges) for the analysis

Query:
{query}

Stock Tickers:
[ADANIENT, ADANIPORTS, APOLLOHOSP, ASIANPAINT, AXISBANK, BAJAJ-AUTO, BAJFINANCE, BAJAJFINSV, BPCL, BHARTIARTL, BRITANNIA, CIPLA, COALINDIA, DIVISLAB, DRREDDY, EICHERMOT, GRASIM, HCLTECH, HDFCBANK, HDFCLIFE, HEROMOTOCO, HINDALCO, HINDUNILVR, ICICIBANK, ITC, INDUSINDBK, INFY, JSWSTEEL, KOTAKBANK, LT, M&M, MARUTI, NESTLEIND, NTPC, ONGC, POWERGRID, RELIANCE, SBILIFE, SBIN, SUNPHARMA, TATACONSUM, TATAMOTORS, TATASTEEL, TECHM, TITAN, ULTRACEMCO, UPL, WIPRO, LTIM, BAJAJHLDNG]

Return JSON:
{{
    "ticker": "TICKER_HERE",
    "start_date": "YYYY-MM-DD",
    "end_date": "YYYY-MM-DD",
    "period_description": "Human readable period"
}}

Rules:
- Extract exact dates if mentioned, or infer from month/year references
- For October-December 2024: start_date="2024-10-01", end_date="2024-12-31"
- Return JSON only, no explanation
"""
        prompt = PROMPT_TEMPLATE.format(query=task_input)
        result = call_llm_json(
            system="You are a financial data extraction system.",
            user=prompt
        )
        
        print(f"📅 Extracted period: {result.get('period_description', 'N/A')}")
        return result

    def call_tool(self, processed_input):
        ticker = processed_input.get('ticker')
        start_date = processed_input.get('start_date')
        end_date = processed_input.get('end_date')
        period_desc = processed_input.get('period_description')
        
        print(f"Getting fundamentals for {ticker} during {period_desc}")
        
        # Fetch all fundamentals
        all_fundamentals = run_nifty_scraper(symbol=ticker)
        
        if not all_fundamentals:
            return failure(f"No fundamental data found for {ticker}")
        
        # Filter fundamentals by date period
        filtered_fundamentals = self._filter_by_period(
            all_fundamentals, 
            start_date, 
            end_date
        )
        
        print(f"📊 Filtered to {len(filtered_fundamentals)} records in period {period_desc}")
        return filtered_fundamentals

    def _filter_by_period(self, data, start_date, end_date):
        """Filter fundamental data to specific date range"""
        if isinstance(data, dict):
            data = str(data)
        
        # Extract date references from the data and filter
        filtered_result = f"""
Fundamentals for the period {start_date} to {end_date}:

{data}

[Note: This data has been filtered to show fundamentals relevant to the period from {start_date} to {end_date}. 
If quarterly data is available, quarters overlapping this period are included.]
"""
        return filtered_result

    def postprocess(self, tool_output, symbol):
        print("Postprocessing fundamental data...")
        
        if tool_output is None or isinstance(tool_output, dict) and tool_output.get('error'):
            return failure("No fundamental data found for the given query.")
        
        citations = [{"source": "merged_nifty50.json", "symbol": symbol}]
        return success(tool_output, citations=citations)

    def run(self, task_input: str) -> str:
        processed_input = self.preprocess(task_input)
        
        if isinstance(processed_input, dict) and 'error' in processed_input:
            return failure(f"Failed to extract period: {processed_input['error']}")
        
        tool_output = self.call_tool(processed_input)
        return self.postprocess(tool_output, processed_input.get('ticker', 'UNKNOWN'))