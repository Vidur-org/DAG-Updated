# MAS Financial Analysis & Decision System

## 🚀 Overview
This project is a state-of-the-art, modular, multi-agent financial analysis and decision support platform. It combines:
- **MAS (Multi-Agent System) data extraction**
- **LLM-driven reasoning and synthesis**
- **Internet research and citation tracking**
- **A hierarchical, context-propagating decision tree**
- **Evidence gating and confidence logic**
- **Interactive editing and full auditability**

to deliver robust, transparent, and actionable investment recommendations for any company and period.

---

## 🏗️ System Architecture

```
User Input (Company, Period)
        │
        ▼
MAS Agents (fundamental, news, internet, macro, etc.)
        │
        ▼
Consolidated MAS Context & Specialized Reports
        │
        ▼
Tree Orchestrator (OpenAI/tree_orchestrator_main.py)
        │
        ├─► Node Context Selection (specialized/inherited)
        ├─► Internet Research (live, summarized, cited)
        ├─► LLM Child Question Generation (unique, non-overlapping)
        ├─► Node Deduplication & Summary Node Creation
        ├─► Evidence Gating & Confidence Adjustment
        └─► Interactive Editing & Regeneration
        │
        ▼
Comprehensive Execution Report (execution_report.json)
```

---

## 🧩 Key Components

### MAS-main (Multi-Agent System)
- **Agents:** `fundamental_agent`, `news_agent`, `internet_agent`, `macro_agent`, etc.
- **Function:** Extracts, filters, and synthesizes all relevant data for the specified period.
- **Output:**
  - Consolidated MAS context (all data, all agents)
  - 5 specialized reports (one for each level-1 question in the tree)

### OpenAI (Tree Orchestrator & LLM Integration)
- **Tree Orchestrator:**
  - Builds a multi-level Q&A tree for investment analysis.
  - Propagates constant context (company, period) to every node.
  - Integrates MAS data, internet research, and LLM-generated reasoning.
  - Deduplicates and combines similar nodes, creating summary nodes as needed.
  - Enforces unique, non-overlapping child questions at each node.
  - Uses BM25 for context retrieval and relevance ranking.
  - Evidence gating and confidence kill-switch: Reduces confidence if evidence is weak, contradictory, or missing.
  - Interactive node editing and subtree regeneration.
  - Generates a comprehensive execution report with all reasoning, answers, and citations.
- **Internet Agent:**
  - Supplements MAS data with up-to-date internet research and citations at every node.
  - Summarizes queries if too long for the Tavily API.
  - Always provides fallback content if search fails.
  - Citations and URLs are tracked and included in the report.
- **LLM Service:**
  - Generates child questions, answers, and specialized context using OpenAI or Groq models.
  - Prompts enforce uniqueness, clarity, and context propagation.
  - Summarizes or combines similar questions at each level.
  - Handles missing or insufficient MAS/internet data gracefully.
- **BM25 Context Retrieval:**
  - Ranks and retrieves the most relevant context for each node/question.
  - Used for both MAS and internet data.
  - Ensures each node's context is as focused and relevant as possible.
- **Evidence Gate & Confidence Kill-Switch:**
  - Ensures recommendations are only made when sufficient, non-contradictory evidence is present.
  - If too few vendor nodes or citations, or if contradictions are detected, confidence is reduced or synthesis is suppressed.
  - All reasons for confidence reduction are logged and included in the final report.
- **Interactive Editing:**
  - Allows users to edit any node/question and regenerate its subtree and all affected answers.
  - Supports full tree regeneration and answer propagation.
  - All edits are tracked and saved with incremented report versions.
- **Comprehensive Reporting:**
  - Full execution report with all nodes, answers, reasoning, citations, and confidence rationale.

### financial_intelligence, fundamental, llm, prompts, router, tools
- **Supporting modules** for data processing, LLMs, prompt management, and utility functions.

---

## 🔄 Full Data Workflow

1. **User Input:**
   - Specify the target company and investment period.
2. **MAS Data Extraction:**
   - MAS agents extract all relevant data for the specified period.
   - Data is filtered, cleaned, and synthesized into a consolidated context and 5 specialized reports (one for each level-1 question in the tree).
3. **Tree Construction:**
   - The orchestrator creates a root node with the main investment question.
   - For each node:
     - Context is selected (specialized for level-1, inherited for deeper nodes).
     - Internet research is fetched and appended to the context.
     - The LLM generates unique, non-overlapping child questions.
     - **Node Deduplication:**
       - If a new question is similar to an existing node at the same level, it is deduplicated (aliased) to avoid redundancy.
       - If multiple child questions are similar/overlapping, they are combined into a summary node at the next level, and both original nodes reference this summary node.
     - **Multi-Parent Combination Nodes (from Level 3 onward):**
       - After level 2, at each level, the system additionally generates new child questions that are derived as combinations of two or three parent nodes that are similar in context or base.
       - The LLM is used to synthesize these combined questions if required, ensuring they are meaningful and non-redundant.
       - These combination children are numbered appropriately, and each is linked to all relevant parent nodes (multi-parent links), forming a richer, more interconnected tree structure.
       - Usual children questions remain as before, ensuring both granular and synthesized perspectives are present at each level.
     - All context, reasoning, and citations are tracked at every node, including for multi-parent combination nodes.
4. **Answer Generation:**
   - For leaf nodes, the LLM generates a direct answer using all available context (MAS, internet, prior reasoning).
   - For internal nodes, answers are synthesized from child answers, ensuring logical consistency and evidence-based reasoning.
5. **Evidence Gating & Confidence Adjustment:**
   - The system checks for sufficient evidence (vendor nodes, citations, lack of contradictions, provenance coverage).
   - If evidence is weak or missing, the confidence in the final recommendation is reduced or the synthesis is suppressed.
   - All reasons for confidence reduction are logged and included in the final report.
6. **Reporting:**
   - The entire tree, all nodes, answers, reasoning, citations, and confidence rationale are saved in `execution_report.json`.
   - All URLs, MAS data, internet research, and evidence anchors are included for transparency.
   - Interactive editing allows users to modify any node/question and regenerate the affected subtree and answers.

---

## 🧠 LLM Capabilities & Node Management

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

---

## 📊 Results & Outputs

- **execution_report.json:**
  - Contains the full tree structure, all node details, answers, reasoning, citations, and internet research.
  - Includes evidence anchors, DCF snapshot, risk compartment, technical analysis, and more.
  - Logs all confidence adjustments and evidence gate status.
  - Tracks all URLs and data sources used.
- **Interactive Editing:**
  - Allows users to edit any node/question and regenerate the subtree and all affected answers.
  - All edits are tracked and saved with incremented report versions.

---

## 🛠️ How to Run

1. **Install all dependencies** (see `MAS-main/requirements.txt` and `financial_intelligence/requirements.txt`).
2. **Set your OpenAI API key** and any other required environment variables.
3. **Run the orchestrator from the OpenAI folder:**
   ```bash
   cd OpenAI
   python tree_orchestrator_main.py
   ```
4. **Follow prompts** for interactive editing if desired.
5. **Review the generated `execution_report.json`** for full results.

---

## 🌟 System Capabilities & Extensibility

- **Modular and extensible:** Add new agents, prompt logic, or evidence gating rules as needed.
- **Transparent and auditable:** All steps, data sources, and reasoning are logged.
- **Robust:** Handles missing or contradictory data, and adapts to user edits.
- **Evidence-based:** Confidence and recommendations are always tied to the strength and provenance of the underlying data.
- **Interactive:** Users can edit any node/question and instantly regenerate the affected subtree and answers.

---

## 📁 Folder Structure

- `MAS-main/` — Multi-agent data extraction system
- `OpenAI/` — Tree orchestrator, LLM integration, internet agent, reporting
- `financial_intelligence/` — Utilities, config, agent wrappers
- `fundamental/`, `llm/`, `prompts/`, `router/`, `tools/` — Supporting modules
- `README.md` — This file
- `execution_report.json` — Example output report

---

## 📚 Further Reading & Customization
- See the README and code in each subfolder/module for more details.
- All major steps and decisions are documented for transparency and auditability.
- For advanced customization, see the comments and docstrings in each file.

---

**Built for robust, transparent, and actionable financial decision-making.**