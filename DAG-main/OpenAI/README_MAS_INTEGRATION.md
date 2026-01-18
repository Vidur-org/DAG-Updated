# Tree-of-Thought System with MAS Integration

## 🎯 Overview

This system combines the **Multi-Agent System (MAS)** for comprehensive data gathering with the **Tree-of-Thought (ToT)** reasoning framework for deep structured analysis.

## 🔄 Architecture Flow

```
User Query
    ↓
┌─────────────────────────────────────┐
│  Tree Orchestrator (OpenAI)         │
│  - Receives investment question     │
│  - Passes to MAS for data gathering │
└─────────────────────────────────────┘
    ↓
┌─────────────────────────────────────┐
│  MAS System (MAS-main)              │
│  1. Router/Planner                  │
│  2. Execute Agents:                 │
│     - NewsAgent                     │
│     - FundamentalAgent              │
│     - InternetAgent                 │
│  3. Generate synthesis report       │
│  4. Save output.json                │
└─────────────────────────────────────┘
    ↓
┌─────────────────────────────────────┐
│  Tree Orchestrator (Analysis Phase) │
│  1. Load MAS output.json            │
│  2. Index data into BM25 cache      │
│  3. Build Tree Structure (BFS)      │
│  4. Generate child questions        │
│  5. Analyze MAS data hierarchically │
│  6. Backpropagate answers           │
│  7. Generate investment decision    │
│  8. Save execution_report.json      │
└─────────────────────────────────────┘
    ↓
Final Output:
  - execution_report.json (Tree analysis)
  - output.json (MAS raw data)
```

## 🚀 Key Changes from Original

### Before (Original Tree System)
```python
# Direct data fetching
base_context = internet_agent(query)
fundamentals = yahoo_finance_agent.get_fundamentals_nse(stock)
```

### After (MAS Integration)
```python
# MAS handles all data gathering
mas_data = await fetch_mas_data(query)
# Tree analyzes the MAS output
mas_context = format_mas_output(mas_data)
```

## 📋 What MAS Provides

The MAS system executes and returns:

1. **Agent Results**:
   - NewsAgent: Recent news articles with sentiment
   - FundamentalAgent: Company financials from Nifty50 data
   - InternetAgent: Comprehensive web research via financial_intelligence

2. **Structured Data**:
   ```json
   {
     "query": "Should I invest in ADANIENSOL...",
     "timestamp": "20260106_120000",
     "results": {
       "task_1": {
         "agent": "news_agent",
         "output": {
           "status": "success",
           "data": [...],
           "citations": [...]
         }
       },
       "task_2": {...}
     },
     "final_report": "Comprehensive synthesis..."
   }
   ```

3. **Synthesis Report**: GPT-4o-mini generated comprehensive analysis

## 🌳 What Tree System Does

With MAS data as foundation, the Tree system:

1. **Indexes Data**: Loads all MAS results into BM25 cache for fast retrieval
2. **Builds Hierarchy**: Creates question decomposition tree
3. **Context Enrichment**: Each node inherits parent context + retrieves relevant MAS data
4. **Structured Reasoning**: Breaks down investment question into:
   - Level 1: Fundamental Analysis, Technical Analysis, Risk Assessment
   - Level 2: Sub-analyses (Financial Health, Valuation, etc.)
   - Level 3+: Granular questions (Cash Flow Quality, DCF Models, etc.)
5. **Bottom-Up Synthesis**: Aggregates leaf answers → parent answers → root decision
6. **Investment Decision**: Final output with LONG/SHORT/NEUTRAL + confidence

## 🔧 Configuration

### config.py
```python
CONFIG = {
    'STOCK': 'ADANIENSOL',      # Stock to analyze
    'MAX_LEVELS': 4,             # Tree depth (3-5 recommended)
    'MAX_CHILDREN': 4,           # Children per node
    'INVESTMENT_WINDOW': '3 month'
}
```

### Environment Variables
Ensure both systems have access to:
```bash
OPENAI_API_KEY=your_key    # For both MAS and Tree
GROQ_API_KEY=your_key      # For MAS (optional fallback)
TAVILY_API_KEY=your_key    # Not used (MAS handles searches)
```

## 📊 Execution Stats

Typical run for MAX_LEVELS=4, MAX_CHILDREN=4:

**MAS Phase:**
- 3 agents executed
- 5-10 tasks completed
- 1 synthesis report generated
- Time: 30-60 seconds

**Tree Phase:**
- 64 nodes created
- 100+ LLM calls
- 60-70% BM25 cache hits (after indexing MAS data)
- 0 new internet searches (all from MAS)
- Time: 2-3 minutes

**Total Cost:** ~$0.50-1.00 (primarily LLM calls, no additional search API costs)

## 🎯 Benefits of Integration

1. **Comprehensive Data**: MAS gathers from multiple sources (news, fundamentals, internet)
2. **No Redundancy**: Tree doesn't repeat searches, analyzes existing data
3. **Cost Efficiency**: Single MAS run + Tree analysis (no per-node searches)
4. **Structured Reasoning**: Tree organizes MAS insights hierarchically
5. **Audit Trail**: Both output.json (data) and execution_report.json (analysis)
6. **Best of Both**: MAS breadth + Tree depth

## 🔍 Example Output Structure

### MAS output.json
```json
{
  "query": "Should I invest in ADANIENSOL for 3 months?",
  "results": {
    "task_1": {
      "agent": "news_agent",
      "output": {
        "data": "Recent news shows ADANIENSOL...",
        "citations": [{"url": "..."}]
      }
    },
    "task_2": {
      "agent": "fundamental_agent",
      "output": {
        "data": "Financial metrics: Revenue=..., PE=...",
        "citations": [...]
      }
    }
  },
  "final_report": "## Investment Analysis\n..."
}
```

### Tree execution_report.json
```json
{
  "final_investment_decision": {
    "position": "long",
    "confidence_level": 0.72,
    "detailed_analysis": "Based on the MAS data analysis..."
  },
  "tree_structure": {
    "node_0": {
      "question": "Should I invest...",
      "children": {
        "node_1": "Fundamental Analysis",
        "node_2": "Technical Analysis",
        "node_3": "Risk Assessment"
      }
    }
  },
  "all_nodes_details": {...}
}
```

## 🚀 Running the Integrated System

```bash
cd OpenAI
python tree_orchestrator_main.py
```

The system will:
1. ✅ Call MAS for data gathering
2. ✅ Generate output.json
3. ✅ Index MAS data into BM25
4. ✅ Build tree structure
5. ✅ Generate analysis
6. ✅ Create execution_report.json
7. ✅ Prompt for interactive editing (optional)

## 📝 Interactive Editing

After initial analysis, you can:
- Edit any node's question
- System regenerates subtree using MAS data
- Saves updated analysis as `execution_report_edited_N.json`

## 🔑 Key Files Modified

- `tree_orchestrator_main.py`: Added `fetch_mas_data()` method
- Removed direct internet/finance agent calls
- All context now derived from MAS output
- BM25 cache populated with MAS data

## 💡 Use Cases

1. **Deep Investment Analysis**: Single stock comprehensive due diligence
2. **Research Verification**: Validate analyst reports using structured reasoning
3. **Scenario Analysis**: Edit nodes to explore alternative hypotheses
4. **Educational**: Understand systematic investment decision-making

## ⚠️ Notes

- MAS must be in parent directory: `../MAS-main/`
- Requires all MAS dependencies installed
- Both systems share OpenAI API key
- Tree analysis is deterministic given same MAS output
- Can run Tree multiple times on same output.json without re-fetching data

---

**Integration Date**: January 6, 2026  
**Version**: 2.0 (MAS-Powered)
