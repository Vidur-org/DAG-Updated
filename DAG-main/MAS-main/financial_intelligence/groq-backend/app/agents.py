from app.llm import openai_chat
from app.search import web_search, format_search_context

def needs_web_search(query: str) -> bool:
    """
    Determine if query needs web search using OpenAI
    """
    response = openai_chat([
        {
            "role": "system",
            "content": """You are a STRICT QUERY ROUTER for a financial intelligence system.

Your task is ONLY to decide whether answering the query requires external, verifiable data.

Respond with ONLY:
YES
or
NO

Reply YES if the query involves:
- Financial results, earnings, profits, revenues, margins, ratios
- Stock prices, indices, commodities, yields, interest rates
- Company fundamentals or quarterly / yearly performance
- Macroeconomic indicators (GDP, CPI, inflation, policy rates)
- News, events, announcements, or timelines
- Any question where NUMBERS must be FACTUALLY CORRECT
- Geopolitical events and their economic impact
- Currency analysis and exchange rates
- Sector-specific impacts and analysis
- Current market conditions or trends

Reply NO if the query involves:
- Conceptual explanations (e.g., "what is inflation")
- Financial theory or definitions
- Opinions, strategies, or hypothetical scenarios
- Coding, architecture, or system design questions

IMPORTANT RULES:
- If unsure, ALWAYS answer YES
- NEVER assume numbers from memory
- NEVER hallucinate financial data
- Geopolitical impact analysis ALWAYS requires web search
- Current economic conditions ALWAYS require web search
"""
        },
        {"role": "user", "content": query}
    ], temperature=0.0, max_tokens=10)
    
    return "YES" in response.upper()

def planner(query: str) -> dict:
    """
    Plan the query execution strategy
    Returns dict with type and search flag
    """
    needs_search = needs_web_search(query)
    
    return {
        "type": "web_search" if needs_search else "chat",
        "needs_search": needs_search,
        "query": query
    }

def web_search_agent(query: str) -> dict:
    """
    Agent that performs web search and synthesizes answer
    """
    # Perform web search
    search_results = web_search(query, max_results=5)
    
    if search_results.get("error"):
        return {
            "type": "error",
            "reply": f"Search error: {search_results['error']}",
            "sources": []
        }
    
    # Format context from search results
    context = format_search_context(search_results)
    
    # Generate answer using OpenAI with search context
    messages = [
        {
            "role": "system",
            "content": """You are WebGPT — a FINANCIAL FACT SYNTHESIS ENGINE.

Your responsibilities are STRICT:

1. Use ONLY the provided search results
2. NEVER invent, estimate, or assume numbers
3. NEVER use prior knowledge or memory
4. If exact figures are unavailable, explicitly state that
5. Prefer accuracy over completeness

FINANCIAL SAFETY RULES:
- Every numeric value must be directly supported by a source
- If multiple sources conflict, mention the discrepancy
- If dates or fiscal periods are unclear, do not guess
- Do NOT extrapolate trends unless explicitly stated in sources

STYLE GUIDELINES:
- Be concise and structured
- Use bullet points for financial metrics
- Clearly mention fiscal period (FY, Q, dates)
- Cite sources naturally (company filings, Reuters, Bloomberg, etc.)

If search data is insufficient:
Say clearly: "Exact financial figures are not available in the provided sources."
"""
        },
        {
            "role": "user",
            "content": f"Query: {query}\n\n{context}\n\nProvide a comprehensive answer based on these search results."
        }
    ]
    
    answer = openai_chat(messages, temperature=0.2, max_tokens=1500)
    
    # Extract source URLs
    sources = [
        {
            "title": result.get("title", ""),
            "url": result.get("url", ""),
            "snippet": result.get("content", "")[:200] + "..."
        }
        for result in search_results.get("results", [])
    ]
    
    return {
        "type": "web_search",
        "reply": answer,
        "sources": sources,
        "quick_answer": search_results.get("answer", "")
    }

def chat_agent(query: str) -> dict:
    """
    Agent for general conversation without web search
    """
    messages = [
        {
            "role": "system",
            "content": """You are a finance-aware AI assistant.

Guidelines:
- Do NOT fabricate or guess financial numbers
- Do NOT provide current prices, earnings, or statistics without verified data
- If a query likely requires real-world financial data, clearly recommend web search
- You may explain concepts, frameworks, and qualitative insights

Allowed:
- Definitions
- Financial concepts
- Strategic or educational explanations

Disallowed:
- Specific company financial figures
- Stock prices or ratios
- Recent events or announcements

When in doubt, explicitly say that external data is required.
"""
        },
        {"role": "user", "content": query}
    ]
    
    answer = openai_chat(messages, temperature=0.4, max_tokens=1500)
    
    return {
        "type": "chat",
        "reply": answer,
        "sources": []
    }

def route_query(query: str) -> dict:
    """
    Main routing function - decides and executes query strategy
    """
    # Plan the query
    plan = planner(query)
    
    # Route to appropriate agent
    if plan["needs_search"]:
        return web_search_agent(query)
    else:
        return chat_agent(query)