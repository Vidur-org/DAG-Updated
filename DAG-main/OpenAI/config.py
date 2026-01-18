CONFIG = {
   'STOCK' : 'RELIANCE',
    'MAX_LEVELS': 5,
    'MAX_CHILDREN': 1,
    'INVESTMENT_WINDOW': 'October 2024 to December 2024',
}

SUMMARY_PROMPT = f"""
Should I invest in {CONFIG['STOCK']} for a period of {CONFIG['INVESTMENT_WINDOW']}? Provide a detailed analysis considering various factors such as market trends, company performance, and economic indicators. Conclude with a clear recommendation on whether to invest or not.
"""

FIRST_LEVEL_QUESTIONS_PROMPT = {
    "Fundamental_Analysis": f"""
Perform a deep fundamental analysis of {CONFIG["STOCK"]}. 

Your analysis must include:

1. **Financial Health & Forensic Review**
   - Detect margin stability, quality of earnings, and cash flow durability.
   - Identify hidden red flags, accounting anomalies, and structural changes across the last 8 quarters.
   - Compare performance to industry benchmarks.

2. **Forward-Looking Growth Scenarios (Base, Bull, Bear)**
   - Predict revenue, margin, and free-cash-flow evolution over the next {CONFIG["INVESTMENT_WINDOW"]}.
   - For each scenario, identify early **signals or leading indicators** that would confirm or invalidate the scenario.

3. **DCF Valuation**
   - Build a DCF model with clear assumptions:
       • revenue growth  
       • EBIT margins  
       • discount rate (WACC)  
       • terminal growth  
   - Explain the rationale behind each assumption.
   - Provide a valuation range and intrinsic value per share.

4. **Adversarial Cross-Verification**
   - Compare your conclusions with popular analyst/broker reports.
   - Identify mistakes, unjustified assumptions, or biases in those external reports.
   - Provide evidence-backed corrections.

5. **Investment Implications**
   - Assess whether the current stock price is above or below intrinsic value.
   - Identify events or conditions that would cause a major valuation reset.

Keep internal chain-of-thought hidden unless explicitly requested.
""",

    "Technical_Analysis": f"""
Perform a predictive technical analysis of {CONFIG["STOCK"]}.

Your analysis must include:

1. **Market Structure Insight**
   - Long-term vs short-term trend regimes.
   - Liquidity pockets, volume clusters, support/resistance zones.
   - Trend exhaustion or continuation signals.

2. **Future Price Path Scenarios**
   - Predict Base, Bull, and Bear paths.
   - For each path list the specific **signals** that would confirm or invalidate it:
       • breakout strength  
       • volatility expansion  
       • RSI regime shift  
       • moving average crossovers  
       • supply/demand imbalance  

3. **Risk Dynamics**
   - Identify where large stop-loss clusters may be located.
   - Highlight vulnerability to whipsaws, false breakouts, and mean-reversion pressure.

4. **Confluence Analysis**
   - Combine 3–5 indicators and identify where they agree or conflict.
   - Evaluate contradictions in existing public technical reports and explain which conclusions are flawed.

5. **Trading & Investment Interpretation**
   - Predict likely institutional and retail participant reactions.
   - Provide critical invalidation levels.

""",

    "Risk_Assessment": f"""
Perform a comprehensive risk assessment of {CONFIG["STOCK"]}.

1. **Categorize Risks**
   - Market, operational, governance, liquidity, macro, regulatory, geopolitical.
   - Identify non-obvious and second-order risks that may not be priced in.

2. **Tree-of-Risks Scenario Modeling**
   - Construct a Tree-of-Thought risk model:
       • 3–5 major risk scenarios  
       • their sub-risks  
       • cascading consequences  
   - Assign subjective probability ranges.

3. **Forward Risk Signals**
   - Identify leading indicators that reflect rising or falling risk levels.
   - Outline what signal combinations indicate the risk regime is changing.

4. **Peer & Sector Benchmarking**
   - Compare risk exposure vs competitors.

5. **Adversarial Review of External Risk Reports**
   - Identify overlooked risks or flawed claims in mainstream risk commentary.

""",

    "Legal_and_Regulatory_Factors": f"""
Analyze the legal and regulatory environment surrounding {CONFIG["STOCK"]}.

1. **Current Compliance Position**
   - Identify any vulnerabilities, pending litigation, or compliance gaps.

2. **Predictive Regulatory Outlook**
   - Forecast 3–4 possible regulatory futures:
       • Bull  
       • Base  
       • Bear  
       • Black Swan (low-probability, high-impact)  

3. **Regulatory Signals to Monitor**
   - Government statements, draft bills, sector policy changes, compliance audit trends.

4. **Impact Modeling**
   - Assess how regulatory changes might affect revenue, costs, margins, and valuation.

5. **Audit of External Reports**
   - Identify inaccuracies or missing considerations in analyst/legal outlook reports.

""",

    "Macroeconomic_Factors": f"""
Evaluate macroeconomic factors affecting {CONFIG["STOCK"]}.

1. **Macro Driver Analysis**
   - GDP growth, inflation, interest rates, currency effects, sector macro cycles.
   - Identify correlations to input costs, demand cycles, and export risks.

2. **Macro Regime Forecasting**
   - Predict future macro regimes (expansion, tightening, stagflation, recession).
   - Assign probability ranges.

3. **Macro-Signal Tracking**
   - Identify leading indicators relevant to the stock:
       • bond yields  
       • PMIs  
       • commodity prices  
       • FX volatility  
       • central bank policy  

4. **Sensitivity Analysis**
   - Show how {CONFIG["STOCK"]}'s performance changes across macro shocks.
   - Compare sensitivity vs peers.

5. **External Report Critique**
   - Identify flawed assumptions or ignored risks in analyst macro reports.

"""
}


FIRST_LEVEL_QUESTIONS  = FIRST_LEVEL_QUESTIONS_PROMPT.values()
