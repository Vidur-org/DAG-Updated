# OpenAI Financial Decision Tree System

## Overview
This module implements an advanced, multi-agent financial analysis and decision support system. It leverages LLMs, MAS (Multi-Agent System) data, internet research, and a hierarchical question/answer tree to provide robust, evidence-based investment recommendations for a given company and period.

## Key Components

### 1. Tree Orchestrator (`tree_orchestrator_main.py`)
- **Purpose:** Builds a multi-level decision tree for investment analysis.
- **Features:**
  - Propagates constant context (company, period) to every node.
  - Integrates MAS agent data, internet research, and LLM-generated reasoning.
  - Deduplicates and combines similar nodes, creating summary nodes when needed.
  - Enforces unique, non-overlapping child questions at each node.
  - Uses BM25 for context retrieval and relevance ranking.
  - Evidence gating and confidence kill-switch: Reduces confidence if evidence is weak, contradictory, or missing.
  - Interactive node editing and subtree regeneration.
  - Generates a comprehensive execution report with all reasoning, answers, and citations.

### 2. MAS Integration
- **MAS Agents:**
  - `fundamental_agent`, `news_agent`, `internet_agent`, etc. (see MAS-main)
  - Each agent extracts data for the specified period only.
  - MAS output is synthesized into a consolidated context and specialized reports for each level-1 question.

### 3. Internet Agent
- **Purpose:** Supplements MAS data with up-to-date internet research and citations at every node.
- **Features:**
  - Summarizes queries if too long for the Tavily API.
  - Always provides fallback content if search fails.
  - Citations and URLs are tracked and included in the report.

### 4. LLM Service
- **Purpose:** Generates child questions, answers, and specialized context using OpenAI or Groq models.
- **Features:**
  - Prompts enforce uniqueness, clarity, and context propagation.
  - Summarizes or combines similar questions at each level.
  - Handles missing or insufficient MAS/internet data gracefully.

### 5. BM25 Context Retrieval
- **Purpose:** Ranks and retrieves the most relevant context for each node/question.
- **Features:**
  - Used for both MAS and internet data.
  - Ensures each node's context is as focused and relevant as possible.

### 6. Evidence Gate & Confidence Kill-Switch
- **Purpose:** Ensures recommendations are only made when sufficient, non-contradictory evidence is present.
- **Features:**
  - If too few vendor nodes or citations, or if contradictions are detected, confidence is reduced or synthesis is suppressed.
  - All reasons for confidence reduction are logged and included in the final report.

### 7. Interactive Editing
- **Purpose:** Allows users to edit any node/question and regenerate its subtree and all affected answers.
- **Features:**
  - Supports full tree regeneration and answer propagation.
  - All edits are tracked and saved with incremented report versions.

### 8. Output & Reporting
- **Comprehensive execution report** (`execution_report.json`):
  - Full tree structure, all node details, answers, reasoning, citations, and internet research.
  - Evidence anchors, DCF snapshot, risk compartment, technical analysis, and more.
  - Confidence rationale and evidence gate status.
  - All URLs and data sources used.

## Workflow

1. **Initialization:**
   - User specifies company and period.
   - Orchestrator initializes with constant context.

2. **MAS Data Gathering:**
   - MAS agents extract all relevant data for the specified period.
   - Output is synthesized into a consolidated context and 5 specialized reports (one per level-1 question).

3. **Tree Construction:**
   - Root node is created with the main investment question.
   - For each node:
     - Context is selected (specialized or inherited).
     - Internet research is fetched and appended.
     - LLM generates unique, non-overlapping child questions.
     - Similar/overlapping questions are combined into summary nodes.
     - Deduplication and aliasing prevent redundant nodes.

4. **Answer Generation:**
   - For leaf nodes, LLM generates direct answers.
   - For internal nodes, answers are synthesized from child answers.
   - All answers include MAS and internet citations.

5. **Evidence Gating & Confidence Adjustment:**
   - If evidence is insufficient or contradictory, confidence is reduced or synthesis is suppressed.
   - All reasons are logged in the final report.

6. **Reporting:**
   - Full execution report is generated, including all nodes, answers, reasoning, citations, and confidence rationale.
   - Interactive editing allows for node/question changes and subtree regeneration.

---

## Full Data Workflow & System Capabilities

### 1. Data Flow Overview
- **User Input:**
  - Specify the target company and investment period.
- **MAS Data Extraction:**
  - MAS agents (fundamental, news, internet, etc.) extract all relevant data for the specified period.
  - Data is filtered, cleaned, and synthesized into a consolidated context and 5 specialized reports (one for each level-1 question in the tree).
- **Tree Construction:**
  - The orchestrator creates a root node with the main investment question.
  - For each node:
    - Context is selected (specialized for level-1, inherited for deeper nodes).
    - Internet research is fetched and appended to the context.
    - The LLM generates unique, non-overlapping child questions.
    - **Node Deduplication:**
      - If a new question is similar to an existing node at the same level, it is deduplicated (aliased) to avoid redundancy.
      - If multiple child questions are similar/overlapping, they are combined into a summary node at the next level, and both original nodes reference this summary node.
    - All context, reasoning, and citations are tracked at every node.
- **Answer Generation:**
  - For leaf nodes, the LLM generates a direct answer using all available context (MAS, internet, prior reasoning).
  - For internal nodes, answers are synthesized from child answers, ensuring logical consistency and evidence-based reasoning.
- **Evidence Gating & Confidence Adjustment:**
  - The system checks for sufficient evidence (vendor nodes, citations, lack of contradictions, provenance coverage).
  - If evidence is weak or missing, the confidence in the final recommendation is reduced or the synthesis is suppressed.
  - All reasons for confidence reduction are logged and included in the final report.
- **Reporting:**
  - The entire tree, all nodes, answers, reasoning, citations, and confidence rationale are saved in `execution_report.json`.
  - All URLs, MAS data, internet research, and evidence anchors are included for transparency.
  - Interactive editing allows users to modify any node/question and regenerate the affected subtree and answers.

### 2. LLM Capabilities
- **Child Question Generation:**
  - Ensures all child questions are unique, non-overlapping, and clearly defined.
  - Propagates constant context (company, period) to every node and prompt.
  - Can summarize or combine similar questions into a single summary node.
- **Answer Synthesis:**
  - Synthesizes answers from MAS data, internet research, and child node answers.
  - Handles missing or insufficient data gracefully, indicating gaps in evidence.
- **Deduplication & Aliasing:**
  - Prevents redundant nodes by checking for similar questions at each level.
  - Creates alias nodes that point to canonical nodes when duplication is detected.
- **Summary Node Creation:**
  - When multiple child questions are similar, a summary node is created at the next level to combine their analysis.
- **Interactive Regeneration:**
  - Supports full subtree regeneration and answer propagation when a node/question is edited.

### 3. Results & Outputs
- **execution_report.json:**
  - Contains the full tree structure, all node details, answers, reasoning, citations, and internet research.
  - Includes evidence anchors, DCF snapshot, risk compartment, technical analysis, and more.
  - Logs all confidence adjustments and evidence gate status.
  - Tracks all URLs and data sources used.
- **Interactive Editing:**
  - Allows users to edit any node/question and regenerate the subtree and all affected answers.
  - All edits are tracked and saved with incremented report versions.

### 4. Node Deduplication & Summary Nodes
- **Deduplication:**
  - Each new child question is checked for similarity to existing nodes at the same level.
  - If a duplicate is found, an alias node is created to point to the canonical node, avoiding redundant computation and answers.
- **Summary Nodes:**
  - If two or more child questions are similar/overlapping, a new summary node is created at the next level.
  - The original nodes reference this summary node, which provides a combined analysis.
  - This ensures the tree remains concise, non-redundant, and logically organized.

### 5. Confidence & Evidence Gate
- **Evidence Gate:**
  - The system checks for sufficient validated evidence (vendor nodes, citations, provenance, lack of contradictions).
  - If evidence is insufficient, the confidence in the final recommendation is reduced or synthesis is suppressed.
- **Confidence Kill-Switch:**
  - All reasons for confidence reduction (evidence gate, contradictions, provenance, etc.) are logged and included in the final report.
  - The final decision includes a `confidence_rationale` explaining any reductions.

---

This workflow ensures that every recommendation is:
- Fully evidence-based and auditable
- Transparent in its reasoning and data sources
- Adaptable to new data, agents, or user edits
- Robust against missing or contradictory information

For further details, see the code and comments in each module.

## Files in This Folder
- `tree_orchestrator_main.py` — Main orchestrator and workflow logic.
- `api.py` — FastAPI endpoint for programmatic access (POST /analyze).
- `preference_manager.py` — User preference management (presets, saved preferences, defaults).
- `openai_prompts.py` — All LLM prompt templates and logic.
- `agents.py` — BM25 and other agent logic.
- `config.py` — Configuration and constants.
- `internet_agent.py` — Internet research agent logic.
- `LLM.py` — LLM service wrapper.
- `node.py` — Tree node data structure.
- `prompts.py` — Additional prompt logic.
- `execution_report.json` — Example output report.
- `user_preferences.json` — User preference storage (auto-generated).
- `README.md` — This file.

## How to Run

> **Quick Start:** For immediate running instructions, see [QUICK_START_API.md](QUICK_START_API.md)

### Option 1: Direct CLI Execution (Interactive)

1. Install all dependencies (see MAS-main and requirements.txt).
2. Set your OpenAI API key and any other required environment variables.
3. Run the orchestrator:
   ```bash
   python tree_orchestrator_main.py
   ```
4. Follow the prompts for interactive editing if desired.
5. Review the generated `execution_report.json` for full results.

### Option 2: FastAPI Endpoint (Recommended for Frontend Integration)

The system now exposes a REST API endpoint for programmatic access.

#### Installation

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. Ensure all environment variables are set (OpenAI API key, etc.)

#### Starting the API Server

**Method 1: Using Python directly**
```bash
cd OpenAI
python api.py
```

**Method 2: Using uvicorn directly**
```bash
cd OpenAI
uvicorn api:app --host 0.0.0.0 --port 8000
```

The API will be available at `http://localhost:8000`

#### API Endpoints

**POST /analyze** - Analyze investment query using Tree + MAS system

**Request Body:**
```json
{
  "user_id": "string",
  "query": "string",
  "preferences": {
    "max_levels": 4,
    "max_children": 2,
    "preset": "balanced",
    "save": true
  }
}
```

**Request Parameters:**
- `user_id` (required): User identifier for preference management
- `query` (required): Investment analysis query/question
- `preferences` (optional): Analysis configuration
  - `max_levels`: Maximum tree depth (overrides preset/saved)
  - `max_children`: Maximum children per node (overrides preset/saved)
  - `preset`: Preset name - `"fast"`, `"balanced"`, or `"thorough"`
    - `fast`: max_levels=3, max_children=1
    - `balanced`: max_levels=4, max_children=2
    - `thorough`: max_levels=5, max_children=3
  - `save`: Whether to save preferences for the user (default: false)

**Preference Resolution Priority:**
1. Explicit values (`max_levels`, `max_children`) - highest priority
2. Preset values (if `preset` is provided)
3. Saved user preferences
4. System defaults (from `config.py`) - lowest priority

**Response Body:**
```json
{
  "answer": "final aggregated analysis",
  "execution_report": {
    "tree_structure": {...},
    "all_nodes": {...},
    "stats": {
      "llm_calls": 42,
      "bm25_hits": 15,
      "internet_searches": 8,
      "num_nodes": 25
    },
    "final_decision": {
      "position": "long",
      "confidence_level": 0.75,
      "detailed_analysis": "..."
    },
    "execution_log": [...]
  },
  "metadata": {
    "max_levels": 4,
    "max_children": 2,
    "used_saved_preferences": false,
    "source": "MAS + Tree"
  }
}
```

#### Example API Usage

**Using curl:**
```bash
curl -X POST "http://localhost:8000/analyze" \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "user123",
    "query": "Should I invest in RELIANCE for October 2024 to December 2024?",
    "preferences": {
      "preset": "balanced",
      "save": true
    }
  }'
```

**Using Python requests:**
```python
import requests

response = requests.post(
    "http://localhost:8000/analyze",
    json={
        "user_id": "user123",
        "query": "Should I invest in RELIANCE for October 2024 to December 2024?",
        "preferences": {
            "preset": "balanced",
            "save": True
        }
    }
)

result = response.json()
print(result["answer"])
print(result["execution_report"]["final_decision"])
```

**Using JavaScript (fetch):**
```javascript
const response = await fetch('http://localhost:8000/analyze', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
  },
  body: JSON.stringify({
    user_id: 'user123',
    query: 'Should I invest in RELIANCE for October 2024 to December 2024?',
    preferences: {
      preset: 'balanced',
      save: true
    }
  })
});

const result = await response.json();
console.log(result.answer);
console.log(result.execution_report.final_decision);
```

#### API Documentation

Once the server is running, you can access:
- **Interactive API docs**: `http://localhost:8000/docs` (Swagger UI)
- **Alternative docs**: `http://localhost:8000/redoc` (ReDoc)
- **Root endpoint**: `http://localhost:8000/` (API info)

#### User Preferences

The API automatically manages user preferences:
- Preferences are stored in `user_preferences.json` in the OpenAI directory
- Each user's preferences persist across requests
- Use `save: true` to update saved preferences
- Saved preferences are automatically used if no explicit values or preset are provided

#### Execution Flow

The API follows this explicit flow:
1. Extract `user_id` from request
2. Get user's saved preferences (if any)
3. Resolve preferences: explicit → preset → saved → defaults
4. Initialize `TreeOrchestrator` with resolved preferences
5. Invoke MAS fetch (happens inside orchestration)
6. Build tree and execute nodes in parallel
7. Aggregate bottom-up reasoning
8. Generate final decision
9. (Optional) Save updated preferences if `save=true`
10. Return structured API response

**Note:** The API skips interactive editing (suitable for programmatic use). For interactive editing, use the CLI option.

## Notes
- The system is modular and can be extended with new agents, prompt logic, or evidence gating rules.
- All major steps and decisions are logged for transparency and auditability.
- For advanced customization, see the comments and docstrings in each file.

---

