# Quick Start Guide: MAS-Powered Tree System

## 🎯 What This System Does

1. **MAS Phase**: Gathers comprehensive financial data (news, fundamentals, prices, web research)
2. **Tree Phase**: Builds hierarchical reasoning structure analyzing the MAS data
3. **Output**: Investment decision (LONG/SHORT/NEUTRAL) with confidence and detailed analysis

## 📦 Prerequisites

```bash
# Install dependencies for both systems
pip install openai pydantic tavily-python yfinance beautifulsoup4 requests pandas
pip install groq feedparser newspaper3k aiohttp structlog tenacity sentence-transformers
```

## ⚙️ Configuration

### 1. Set API Keys (in .env or environment)
```bash
OPENAI_API_KEY=your_openai_key
GROQ_API_KEY=your_groq_key  # Optional for MAS fallback
```

### 2. Edit config.py
```python
CONFIG = {
    'STOCK': 'TATAMOTORS',          # Change to your stock
    'MAX_LEVELS': 4,                 # Tree depth (3-5 recommended)
    'MAX_CHILDREN': 4,               # Children per node
    'INVESTMENT_WINDOW': '3 month'   # Analysis timeframe
}
```

### 3. Ensure MAS data files exist
- `../MAS-main/merged_sorted_embeddings.json` (news database)
- `../MAS-main/merged_nifty50.json` (fundamentals database)

## 🚀 Running the System

### Option 1: Full Analysis
```bash
cd OpenAI
python tree_orchestrator_main.py
```

This will:
1. Call MAS to gather data for your stock
2. Build tree structure (typically 64+ nodes)
3. Generate analysis through backpropagation
4. Create investment decision
5. Save `execution_report.json`
6. Prompt for interactive editing

### Option 2: Test Integration First
```bash
cd OpenAI
python test_mas_integration.py
```

This runs a quick test to verify MAS-Tree integration without full tree building.

## 📊 Understanding the Output

### 1. output.json (MAS Data)
Location: `../MAS-main/output.json`

Contains:
- Raw agent results (news, fundamentals, internet research)
- Citations and sources
- MAS synthesis report

### 2. execution_report.json (Tree Analysis)
Location: `./execution_report.json`

Contains:
```json
{
  "final_investment_decision": {
    "position": "long|short|neutral",
    "confidence_level": 0.0-1.0,
    "detailed_analysis": "..."
  },
  "execution_stats": {
    "total_nodes": 64,
    "llm_calls": 128,
    "bm25_hits": 45,
    "internet_searches": 0
  },
  "tree_structure": {...},
  "all_nodes_details": {...}
}
```

## 🔍 Interpreting Results

### Investment Position
- **LONG**: Buy recommendation
- **SHORT**: Sell/short recommendation  
- **NEUTRAL**: Hold or no clear position

### Confidence Level
- **0.7-1.0**: High confidence
- **0.5-0.7**: Moderate confidence
- **0.0-0.5**: Low confidence

### Tree Structure
Navigate through `tree_structure` to see:
- How the question was decomposed
- What sub-analyses were performed
- How conclusions were built bottom-up

## 🛠️ Interactive Editing

After initial run, the system prompts:
```
Do you want to edit any node? (yes/no):
```

If you choose "yes":
1. View all nodes and their questions
2. Select a node to edit
3. Provide new question
4. System regenerates subtree and updates analysis
5. Saves as `execution_report_edited_1.json`, etc.

## 📈 Example Workflow

```bash
# 1. Configure your stock
# Edit config.py: CONFIG['STOCK'] = 'RELIANCE'

# 2. Run analysis
python tree_orchestrator_main.py

# 3. System output shows:
🚀 CALLING MAS SYSTEM FOR DATA GATHERING
📋 Step 1: Planning tasks...
✅ Plan created: 3 tasks
🔧 Step 2: Executing tasks...
✅ Execution complete: 3 results
📝 Step 3: Generating synthesis...
✅ MAS output saved

📚 Indexing MAS data into BM25...
✅ BM25 indexed with 15 documents

🌳 Building tree structure...
[Tree building progress...]

🔙 STARTING BACKPROPAGATION
[Answer generation progress...]

🎯 FINAL INVESTMENT DECISION:
Position: LONG
Confidence: 0.72
Analysis: Based on strong fundamentals...

# 4. Check outputs
📁 execution_report.json
📁 ../MAS-main/output.json
```

## 🎛️ Customization

### Adjust Tree Depth
```python
# Shallow tree (faster, less detailed)
CONFIG['MAX_LEVELS'] = 3
CONFIG['MAX_CHILDREN'] = 2

# Deep tree (slower, more detailed)
CONFIG['MAX_LEVELS'] = 5
CONFIG['MAX_CHILDREN'] = 5
```

### Modify First-Level Questions
Edit `config.py` → `FIRST_LEVEL_QUESTIONS`:
```python
FIRST_LEVEL_QUESTIONS = {
    "Fundamental_Analysis": "Your custom prompt...",
    "Technical_Analysis": "Your custom prompt...",
    "Risk_Assessment": "Your custom prompt..."
}
```

## 🐛 Troubleshooting

### "Module not found: router.planner"
- Ensure MAS-main is in parent directory
- Check sys.path includes MAS-main

### "No such file: merged_sorted_embeddings.json"
- Download from Google Drive link in MAS README
- Place in MAS-main directory

### "OpenAI API key not set"
- Set OPENAI_API_KEY environment variable
- Or add to .env file

### MAS execution fails
- Check MAS system works independently first
- Run: `cd ../MAS-main && python main.py`

### High API costs
- Reduce MAX_LEVELS (fewer nodes = fewer LLM calls)
- Reduce MAX_CHILDREN (narrower tree)
- Use GPT-3.5-turbo instead of GPT-4

## 📊 Performance Expectations

| Configuration | Nodes | LLM Calls | Time | Cost |
|--------------|-------|-----------|------|------|
| Quick (3 levels, 2 children) | ~15 | ~30 | 1 min | $0.15 |
| Standard (4 levels, 4 children) | ~64 | ~128 | 3 min | $0.60 |
| Deep (5 levels, 5 children) | ~625 | ~1250 | 15 min | $6.00 |

*Costs based on GPT-4o-mini pricing (~$0.005 per call)*

## 🎓 Learning the System

To understand the decision-making:

1. Open `execution_report.json`
2. Navigate to `tree_structure`
3. Follow path: Root → Level 1 → Level 2 → Leaves
4. Check `all_nodes_details` for full context per node
5. See `execution_log` for chronological operations

## 💡 Tips for Best Results

1. **Use clear stock symbols**: 'RELIANCE' not 'Reliance Industries'
2. **Reasonable timeframes**: 1-6 months (not 10 years)
3. **Let MAS complete**: Don't interrupt data gathering phase
4. **Review both outputs**: MAS data + Tree analysis
5. **Edit intelligently**: Refine specific sub-questions for better insights

---

**Need Help?**
- Check README_MAS_INTEGRATION.md for technical details
- Review execution_log in output for debugging
- Test with test_mas_integration.py first
