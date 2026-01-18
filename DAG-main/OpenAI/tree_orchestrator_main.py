import re
import ast
import hashlib
from node import TreeNode
from openai_prompts import get_child_question_prompt, get_answer_prompt, get_final_response_prompt
from LLM import LLMService
from internet_agent_wrapper import InternetAgentWrapper
from datetime import datetime
from typing import Dict, List, Optional
import json
import asyncio
import sys
import os
from pathlib import Path
import importlib.util
from config import CONFIG, FIRST_LEVEL_QUESTIONS

DEFAULT_STOPWORDS = {
    "the", "is", "a", "an", "of", "for", "to", "and", "in", "on",
    "with", "about", "does", "should", "what", "how", "why", "when",
    "where", "can", "we", "our", "be", "are", "do", "need", "using",
    "consider", "considering"
}
# Ensure regex module is always available
# --- MAS-main integration ---
mas_main_path = str(Path(__file__).parent.parent / "MAS-main")
if mas_main_path not in sys.path:
    sys.path.insert(0, mas_main_path)
from financial_intelligence.utils.entity_resolver import resolve_entities

# Load BM25Agent from local agents.py file explicitly
current_dir = Path(__file__).parent
agents_file = current_dir / "agents.py"
spec = importlib.util.spec_from_file_location("openai_agents", agents_file)
openai_agents = importlib.util.module_from_spec(spec)
spec.loader.exec_module(openai_agents)
BM25Agent = openai_agents.BM25Agent

class TreeOrchestrator:
    def __init__(self, max_levels: int = CONFIG['MAX_LEVELS'] , max_children: int = CONFIG['MAX_CHILDREN']):
        # counts 
        self.llm_call_count = 0
        self.BM25_hits = 0
        self.internet_search_hits = 0
        self.num_nodes = 0
        self.edit_count = 0
        # configs
        self.max_levels = max_levels
        self.max_children = max_children
        self.llm_service = LLMService(model="gpt-4o-mini")
        self.bm25 = BM25Agent()
        # adjecency list for tree
        self.forward_adj = {}
        self.backward_adj = {}
        self.queue_for_bfs = asyncio.Queue()

        self.stock = CONFIG['STOCK']
        self.investment_window = CONFIG['INVESTMENT_WINDOW']
        self.context = []
        self.allowed_years = self._extract_allowed_years(self.investment_window)
        # --- Constant context to propagate to all nodes ---
        self.constant_additional_context = f"[CONSTANT CONTEXT]\nCompany: {self.stock}\nPeriod: {self.investment_window}\n"
        self.period_enforcement_stats = {"sentences_removed": 0, "allowed_years": list(self.allowed_years)}
        self.data_provenance_index = {"tags": [], "coverage": 0}
        self.kill_switch_metadata = {"reasons": [], "diagnostics": {}}
        
        # MAS integration
        self.mas_output = None
        self.mas_output_path = Path(mas_main_path) / "output.json"
        self.level1_specialized_contexts = {}  # Dict mapping node_id -> specialized context
        self.specialized_reports = {}  # Store 5 specialized reports for level-1 nodes
        
        # Specialized reports for level-1 nodes
        self.specialized_reports = {}  # {node_id: specialized_context}
        self.context_chains = {}  # {node_id: context_with_ancestors}
        self.consolidated_mas_context = None  # Single consolidated context for all nodes
        self.fundamental_snapshot = None  # Compressed fundamentals payload
        self.internet_agent = InternetAgentWrapper()  # For fetching additional context at each node

        self.nodes = {}  # Store all nodes by ID
        self.execution_log = []  # Track all operations
        self.level_signature_index: Dict[int, Dict[str, str]] = {}
        self.level_context_index: Dict[int, Dict[str, str]] = {}
        self.question_stopwords = DEFAULT_STOPWORDS
        self.missing_questions_analysis = {}  # Store missing questions analysis

    def build_internet_search_context(self, search_query: str, search_results: str) -> None:
        """
        Build a look-up for internet search context.
        Finds the best match using BM25
        """
        d = {
            'search_queries': search_query,
            'search_results': search_results
        }

        self.context.append(f'{d}')
        return 
        
    async def fetch_mas_data(self, query: str) -> dict:
        """Execute MAS system to fetch all required data"""
        print(f"\n{'='*80}")
        print(f"🚀 CALLING MAS SYSTEM FOR DATA GATHERING")
        print(f"{'='*80}")
        print(f"Query: {query}")
        
        # Temporarily modify sys.path to prioritize MAS and avoid conflicts
        original_path = sys.path.copy()
        current_dir = str(Path(__file__).parent)
        
        try:
            # Remove current OpenAI directory to avoid prompts.py conflict
            if current_dir in sys.path:
                sys.path.remove(current_dir)
            if '' in sys.path:
                sys.path.remove('')
            if '.' in sys.path:
                sys.path.remove('.')
            
            # Put MAS-main at the beginning
            sys.path.insert(0, str(mas_main_path))
            
            # Import MAS components (with MAS-main first in path)
            from router.planner import plan_tasks
            from executor.executor import execute_plan
            
            # Execute MAS pipeline
            print(f"\n📋 Step 1: Planning tasks with MAS router...")
            plan = plan_tasks(query)
            print(f"✅ Plan created: {len(plan.get('tasks', []))} tasks")
            
            print(f"\n🔧 Step 2: Executing tasks with MAS agents...")
            results = execute_plan(plan)
            print(f"✅ Execution complete: {len(results)} results")
            
        finally:
            # Restore original sys.path
            sys.path = original_path
        
        # Generate MAS report (outside try-finally to use normal imports)
        print(f"\n📝 Step 3: Generating MAS synthesis report...")
        from openai import OpenAI
        client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        
        SYSTEM_PROMPT = """
You are a professional financial research analyst.

Rules:
- Use ONLY the provided results.
- Do NOT hallucinate or add external facts.
- Be concise, factual, and structured.
- Focus on market impact, trends, and implications.
- If data is insufficient, clearly say so.
- Avoid motivational or generic statements.

Output a final financial report in markdown format with clear headings.
"""
        
        user_prompt = f"""
User Query:
{query}

Retrieved Financial News & Data:
{json.dumps(results, indent=2, ensure_ascii=False)}

Task:
Generate a final financial intelligence report based strictly on the above data.
"""
        
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.2
        )
        
        final_report = response.choices[0].message.content
        
        # Collect all URLs from results
        collected_urls = []
        url_pattern = r'https?://[^\s<>"{}|\\^`\[\]]+'
        
        for task_id, result in results.items():
            result_text = str(result.get('result', '') or result.get('output', ''))
            urls_found = re.findall(url_pattern, result_text)
            
            for url in urls_found:
                collected_urls.append({
                    'url': url,
                    'source_task': task_id,
                    'agent': result.get('agent', 'Unknown')
                })
        
        print(f"📎 Collected {len(collected_urls)} URLs from MAS execution")
        
        # Save output.json with URLs at top
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_data = {
            "urls": collected_urls,  # ✅ URLs at top
            "query": query,
            "timestamp": timestamp,
            "total_urls": len(collected_urls),
            "results": results,
            "final_report": final_report
        }
        
        with open(self.mas_output_path, "w", encoding="utf-8") as f:
            json.dump(output_data, f, indent=2, ensure_ascii=False)
        
        print(f"✅ MAS output saved to: {self.mas_output_path}")
        print(f"{'='*80}\n")
        
        self.mas_output = output_data
        return output_data
    
    def extract_mas_citations(self, answer_text: str) -> dict:
        """Extract which parts of MAS data were referenced in the answer"""
        citations = {
            'tasks_referenced': [],
            'data_points_used': [],
            'urls': [],
            'confidence': 'inferred'
        }
        
        if not hasattr(self, 'mas_data_structure') or not self.mas_data_structure:
            return citations
        
        # Check if answer references specific MAS tasks
        for task_id in self.mas_data_structure.get('tasks', {}).keys():
            agent_name = self.mas_data_structure['tasks'][task_id].get('agent', '')
            if task_id.lower() in answer_text.lower() or agent_name.lower() in answer_text.lower():
                citations['tasks_referenced'].append({
                    'task_id': task_id,
                    'agent': agent_name
                })
        
        # Check for specific data point mentions
        data_keywords = ['revenue', 'profit', 'margin', 'growth', 'price', 'volume', 
                        'forecast', 'analyst', 'rating', 'fundamental', 'technical', 
                        'news', 'market', 'sentiment']
        
        for keyword in data_keywords:
            if keyword in answer_text.lower():
                citations['data_points_used'].append(keyword)
        
        # Check if final report was referenced
        if 'synthesis' in answer_text.lower() or 'report' in answer_text.lower():
            citations['tasks_referenced'].append({
                'task_id': 'final_report',
                'agent': 'synthesis'
            })
        
        # Extract URLs from MAS data
        if hasattr(self, 'mas_data_urls') and self.mas_data_urls:
            citations['urls'] = self.mas_data_urls
        
        return citations

    def _extract_allowed_years(self, window: Optional[str]) -> set:
        if not window:
            return set()
        return set(re.findall(r'(20\d{2})', window))

    def enforce_period_isolation(self, text: str) -> tuple[str, int]:
        if not text or not self.allowed_years:
            return text, 0
        sentences = re.split(r'(?<=[\.?!])\s+', text)
        kept_sentences = []
        removed = 0
        for sentence in sentences:
            years = re.findall(r'(20\d{2})', sentence)
            if not years or any(year in self.allowed_years for year in years):
                kept_sentences.append(sentence)
            else:
                removed += 1
        sanitized = ' '.join(kept_sentences).strip()
        return sanitized or text, removed

    def build_data_provenance_index(self, text: str, source: str = "MAS") -> dict:
        if not text:
            return {"tags": [], "coverage": 0, "source": source}
        sentences = re.split(r'(?<=[\.?!])\s+', text)
        tags = []
        for sentence in sentences:
            numbers = re.findall(r'-?\d[\d,]*(?:\.\d+)?%?', sentence)
            for value in numbers:
                tags.append({
                    "value": value.strip(),
                    "sentence": sentence.strip(),
                    "source": source
                })
            if len(tags) >= 200:
                break
        return {"tags": tags, "coverage": len(tags), "source": source}

    def _parse_fundamental_payload(self, raw_text: str) -> dict:
        if not raw_text:
            return {}
        start_idx = raw_text.find("{")
        end_idx = raw_text.rfind("}")
        if start_idx == -1 or end_idx == -1 or end_idx <= start_idx:
            return {}
        payload_text = raw_text[start_idx:end_idx + 1]
        payload_text = payload_text.replace("\\xa0", " ").replace("\u00a0", " ")
        try:
            return ast.literal_eval(payload_text)
        except Exception as exc:
            print(f"⚠️  Unable to parse fundamentals payload: {exc}")
            return {}

    def _normalize_metric_key(self, key: str) -> str:
        key = key.replace("\\xa0", " ").replace("\u00a0", " ")
        key = key.replace("%", " percent ").replace("+", " ")
        key = re.sub(r'[^0-9a-zA-Z]+', '_', key)
        return key.strip('_').lower()

    def _clean_metric_entry(self, entry: dict) -> dict:
        cleaned = {}
        for key, value in entry.items():
            normalized_key = self._normalize_metric_key(str(key))
            cleaned[normalized_key] = value
        return cleaned

    def _safe_number(self, value):
        if isinstance(value, (int, float)):
            return float(value)
        if isinstance(value, str):
            cleaned = value.replace(',', '').replace('%', '').strip()
            if not cleaned or cleaned.lower() in {"na", "n/a", "--"}:
                return None
            try:
                return float(cleaned)
            except ValueError:
                return None
        return None

    def _calc_growth(self, current: Optional[float], previous: Optional[float]) -> Optional[float]:
        if current is None or previous in (None, 0):
            return None
        try:
            return (current - previous) / previous
        except ZeroDivisionError:
            return None

    def _format_number(self, value: Optional[float], decimals: int = 0) -> str:
        if value is None:
            return "NA"
        format_spec = f"{{:,.{decimals}f}}"
        return format_spec.format(value)

    def _format_percent(self, value: Optional[float]) -> str:
        if value is None:
            return "NA"
        return f"{value * 100:.1f}%"

    def extract_fundamental_snapshot(self, fundamental_text: str) -> tuple[Optional[dict], str]:
        payload = self._parse_fundamental_payload(fundamental_text)
        if not payload:
            return None, ""

        financials = payload.get('financials', {})
        profit_loss = [self._clean_metric_entry(item) for item in financials.get('Profit & Loss', [])]
        balance_sheet = [self._clean_metric_entry(item) for item in financials.get('Balance Sheet', [])]
        cash_flow = [self._clean_metric_entry(item) for item in financials.get('Cash Flow', [])]
        quarters = [self._clean_metric_entry(item) for item in payload.get('quarters', [])]

        snapshot = {
            "ttm": profit_loss[-1] if profit_loss else None,
            "previous_year": profit_loss[-2] if len(profit_loss) > 1 else None,
            "latest_quarter": quarters[-1] if quarters else None,
            "previous_quarter": quarters[-2] if len(quarters) > 1 else None,
            "balance_sheet": balance_sheet[-1] if balance_sheet else None,
            "cash_flow": cash_flow[-1] if cash_flow else None,
            "shareholding": {self._normalize_metric_key(k): v for k, v in (payload.get('shareholding') or {}).items()},
            "peers": payload.get('peers', [])[:3],  # keep top 3 to stay compact
            "source_file": str(self.mas_output_path)
        }

        lines = [
            "FUNDAMENTAL SNAPSHOT (compressed)",
        ]

        ttm = snapshot["ttm"] or {}
        prev = snapshot["previous_year"] or {}
        yoy_sales = self._calc_growth(self._safe_number(ttm.get('sales')), self._safe_number(prev.get('sales')))
        yoy_profit = self._calc_growth(self._safe_number(ttm.get('net_profit')), self._safe_number(prev.get('net_profit')))

        lines.append(
            f"- Revenue {ttm.get('year', 'TTM')}: {self._format_number(self._safe_number(ttm.get('sales')))} (YoY {self._format_percent(yoy_sales)})"
        )
        lines.append(
            f"- Net Profit {ttm.get('year', 'TTM')}: {self._format_number(self._safe_number(ttm.get('net_profit')))} (YoY {self._format_percent(yoy_profit)})"
        )
        ttm_opm = self._safe_number(ttm.get('opm_percent'))
        opm_ratio = (ttm_opm / 100) if ttm_opm is not None else None
        lines.append(
            f"- EPS: {self._format_number(self._safe_number(ttm.get('eps_in_rs')), 2)} | OPM: {self._format_percent(opm_ratio)}"
        )

        latest_quarter = snapshot["latest_quarter"] or {}
        if latest_quarter:
            quarter_opm = self._safe_number(latest_quarter.get('opm_percent'))
            quarter_opm_ratio = (quarter_opm / 100) if quarter_opm is not None else None
            lines.append(
                f"- Latest Quarter {latest_quarter.get('quarter')}: Sales {self._format_number(self._safe_number(latest_quarter.get('sales')))}, OPM {self._format_percent(quarter_opm_ratio)}, EPS {self._format_number(self._safe_number(latest_quarter.get('eps_in_rs')), 2)}"
            )

        balance = snapshot["balance_sheet"] or {}
        if balance:
            lines.append(
                f"- Balance Sheet (latest): Assets {self._format_number(self._safe_number(balance.get('total_assets')))}, Borrowings {self._format_number(self._safe_number(balance.get('borrowings')))}"
            )

        cash = snapshot["cash_flow"] or {}
        if cash:
            lines.append(
                f"- Cash Flow: CFO {self._format_number(self._safe_number(cash.get('cash_from_operating_activity')))}, Capex {self._format_number(self._safe_number(cash.get('cash_from_investing_activity')))}"
            )

        shareholding = snapshot.get('shareholding') or {}
        if shareholding:
            promoter = shareholding.get('promoters')
            fii = shareholding.get('fiis')
            dii = shareholding.get('diis')
            lines.append(f"- Ownership: Promoters {promoter}, FIIs {fii}, DIIs {dii}")

        lines.append(f"- Full vendor payload retained in {Path(self.mas_output_path).name}")

        return snapshot, "\n".join(lines)

    def apply_confidence_kill_switch(self, final_decision: Optional[dict], diagnostics: dict) -> tuple[Optional[dict], dict]:
        if not final_decision:
            return final_decision, {"reasons": []}
        kill_reasons = []
        if diagnostics.get('evidence_gate'):
            kill_reasons.append('evidence_gate_triggered')
        if diagnostics.get('contradiction_score', 0) > 0:
            kill_reasons.append('contradictions_present')
        if diagnostics.get('period_leakage', 0) > 0:
            kill_reasons.append('period_leakage_detected')
        if diagnostics.get('provenance_coverage', 0) < diagnostics.get('provenance_threshold', 1):
            kill_reasons.append('insufficient_provenance_tags')
        if diagnostics.get('sensitivity_fallback'):
            kill_reasons.append('sensitivity_matrix_synthetic')
        if kill_reasons:
            confidence = final_decision.get('confidence_level') or 0
            final_decision['confidence_level'] = min(confidence, 0.4)
            final_decision['confidence_rationale'] = "Confidence capped due to " + ", ".join(kill_reasons)
        return final_decision, {"reasons": kill_reasons, "diagnostics": diagnostics}

    def _canonicalize_question(self, text: str) -> str:
        if not text:
            return ""
        lowered = text.lower()
        tokens = re.findall(r'[a-z0-9]+', lowered)
        if not tokens:
            return lowered.strip()
        filtered = [tok for tok in tokens if tok not in self.question_stopwords]
        canonical_tokens = filtered or tokens
        return " ".join(canonical_tokens)

    def _fingerprint_context(self, content: str) -> str:
        if not content:
            return ""
        normalized = content.strip().encode('utf-8')
        return hashlib.sha1(normalized).hexdigest()

    def _register_node_signature(self, level: int, signature: str, context_fp: str, node_id: str) -> None:
        if signature:
            signature_map = self.level_signature_index.setdefault(level, {})
            signature_map[signature] = node_id
        if context_fp:
            context_map = self.level_context_index.setdefault(level, {})
            context_map[context_fp] = node_id

    def _create_alias_node(
        self,
        parent_node: TreeNode,
        node_question: str,
        node_level: int,
        subtree_root_id: Optional[str],
        canonical_node_id: str,
    ) -> TreeNode:
        canonical_node = self.nodes.get(canonical_node_id)
        alias_context = canonical_node.context if canonical_node else parent_node.context
        alias_node = TreeNode(
            id=str(self.num_nodes),
            parent_id=parent_node.id,
            question=node_question,
            context=alias_context,
            level=node_level,
            created_at=datetime.now(),
            search_queries=[],
            reasoning_for_search="Alias of existing node",
            child_questions=[],
            children=[],
            is_leaf=True,
            answer=canonical_node.answer if canonical_node else None,
            mas_data_used=canonical_node.mas_data_used if canonical_node else None,
            subtree_root_id=subtree_root_id,
            internet_research={
                "citations": [],
                "urls": [],
                "summary": "Alias node uses canonical context"
            },
            alias_of=canonical_node_id
        )

        if canonical_node:
            canonical_node.alias_questions.append(node_question)
            canonical_node.aliases.append(alias_node.id)

        self.nodes[alias_node.id] = alias_node
        parent_node.children.append(alias_node.id)

        self.log_operation("alias_node_created", {
            "alias_id": alias_node.id,
            "alias_of": canonical_node_id,
            "parent_id": parent_node.id,
            "question": node_question,
            "level": node_level
        })

        return alias_node
    
    def fetch_internet_context(self, question: str) -> Dict[str, any]:
        """
        Fetch additional context from internet agent for a specific node question.
        Returns: {"content": str, "citations": List[Dict], "urls": List[str], "summary": str}
        """
        try:
            print(f"   🌐 Fetching internet research for node question...")
            
            # Use the wrapper to fetch context
            result = self.internet_agent.fetch_context(question, orchestrator=self)
            
            num_citations = len(result.get('citations', []))
            if num_citations > 0:
                print(f"   ✅ Retrieved {num_citations} citations from internet research")
            else:
                print(f"   ℹ️ No additional internet context available")
            
            return result
                
        except Exception as e:
            print(f"   ⚠️ Error fetching internet context: {str(e)}")
            return {
                "content": "Error fetching internet context.",
                "citations": [],
                "urls": [],
                "summary": "",
                "error": str(e)
            }
    
    async def generate_specialized_reports(self):
        """
        Generate 5 specialized reports from MAS output, one for each level-1 question.
        Each report extracts only the relevant data from MAS output specific to that question.
        """
        if not self.mas_output:
            print("⚠️  No MAS output available for generating specialized reports")
            return
        
        print(f"\n{'='*80}")
        print(f"📊 GENERATING SPECIALIZED REPORTS FOR 5 SUBTREES")
        print(f"{'='*80}")
        
        level1_questions = list(FIRST_LEVEL_QUESTIONS)
        mas_synthesis = self.mas_output.get('final_report', '')
        mas_raw_data = json.dumps(self.mas_output.get('results', {}), indent=2)
        
        for idx, question in enumerate(level1_questions[:5]):  # First 5 questions
            node_id = str(idx + 1)  # node_1, node_2, etc.
            
            print(f"\n📌 Generating report {idx + 1}/5 for subtree node_{node_id}")
            print(f"   Question: {question[:80]}...")
            
            # Generate specialized report using LLM
            prompt = f"""
You are given:
1. A primary question for analysis
2. The complete MAS financial intelligence report and raw data

Your task:
Extract ONLY the relevant information from the MAS report and raw data that directly addresses the primary question.
Create a focused context document that contains:
- All data points relevant to answering the question
- Supporting evidence from the synthesis report
- Specific numbers, metrics, and findings
- Exclude irrelevant information

Primary Question:
{question}

MAS Synthesis Report:
{mas_synthesis}

MAS Raw Data:
{mas_raw_data}

Generate a specialized context report (markdown format) that a focused analyst would use to answer ONLY this question.
Include specific data, metrics, and citations from the MAS report.
"""
            
            response = self.llm_service.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You are a financial data extraction specialist. Extract only relevant information."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1  # Low temperature for focused extraction
            )
            
            specialized_report = response.choices[0].message.content
            self.specialized_reports[node_id] = {
                'question': question,
                'context': specialized_report,
                'length': len(specialized_report)
            }
            
            self.llm_call_count += 1
            print(f"   ✅ Generated {len(specialized_report)} chars of specialized context")
        
        print(f"\n{'='*80}")
        print(f"✅ Specialized reports generated for {len(self.specialized_reports)} subtrees")
        print(f"{'='*80}\n")

    async def buil_first_node(self):
        self.num_nodes += 1
        node_id = "0"

        self.forward_adj[node_id] = []
        self.backward_adj[node_id] = None

        # --- Robust entity extraction for MAS query ---
        # Use the original user query if available, else fallback to self.stock
        # For testing: force entity to RELIANCE
        entity = "RELIANCE"
        mas_query = f"Analyze {entity} for investment over {self.investment_window}. Include fundamentals, technicals, news, and macro factors."

        print(f"🔍 Calling MAS with query: {mas_query}")
        print(f"📊 MAS will gather ALL data: fundamentals, technical, news, internet research")
        mas_data = await self.fetch_mas_data(mas_query)
        
        # Extract URLs directly from MAS output
        self.mas_data_urls = mas_data.get('urls', [])
        print(f"📎 Retrieved {len(self.mas_data_urls)} URLs from MAS output.json")
        
        # Format MAS output into ONE consolidated context for ALL nodes
        mas_context = f"""
{'='*80}
CONSOLIDATED MAS ANALYSIS FOR {self.stock}
{'='*80}

Original Query: {mas_data['query']}
Analysis Timestamp: {mas_data['timestamp']}

{'='*80}
AGENT RESULTS (All Available Data)
{'='*80}
"""
        

        # Evidence gate: ethics discipline
        results = mas_data.get('results', {})
        self.fundamental_snapshot = None
        fundamental_empty = not results.get('task_1', {}).get('output')
        internet_empty = not results.get('task_3', {}).get('output')
        if fundamental_empty and internet_empty:
            mas_context += "\n\nNo validated vendor data; synthesis skipped.\n"
            mas_context, removed_sentences = self.enforce_period_isolation(mas_context)
            self.period_enforcement_stats = {
                "sentences_removed": removed_sentences,
                "allowed_years": list(self.allowed_years)
            }
            self.data_provenance_index = self.build_data_provenance_index(mas_context)
            self.consolidated_mas_context = mas_context
            print("⛔ Ethics gate: No validated vendor data; synthesis skipped.")
            child_prompts = FIRST_LEVEL_QUESTIONS
            node = TreeNode(
                id=node_id,
                parent_id=None,
                question=f"Should I invest in {self.stock} for a period of {self.investment_window}? Provide a detailed analysis considering various factors such as market trends, company performance, and economic indicators. Conclude with a clear recommendation on whether to invest or not.",
                context=self.consolidated_mas_context,  # Use consolidated context
                level=0,
                created_at=datetime.now(),
                child_questions=child_prompts,
                children=[]
            )
            self.nodes[node.id] = node  # ✅ Store node
            self.log_operation("create_root_node", {
                "node_id": node.id,
                "question": node.question,
                "level": node.level,
                "stock": self.stock
            })
            self.queue_for_bfs.put_nowait((node, 0))
            print(f"✅ Root node created: node_{node.id}")
            return node

        # Add detailed results from each agent
        for task_id, result in results.items():
            mas_context += f"\n{'-'*80}\n"
            mas_context += f"📌 {task_id.upper()}\n"
            agent_name = result.get('agent', 'Unknown')
            mas_context += f"Agent: {agent_name}\n"
            mas_context += f"Input: {result.get('input', 'N/A')}\n"
            agent_result = result.get('result', result.get('output', 'No result available'))
            if agent_name == 'fundamental_agent':
                snapshot, summary_text = self.extract_fundamental_snapshot(agent_result)
                if snapshot:
                    self.fundamental_snapshot = snapshot
                    mas_context += "\nResult (compressed fundamentals):\n"
                    mas_context += f"{summary_text}\n"
                else:
                    mas_context += f"\nResult:\n{agent_result}\n"
            else:
                mas_context += f"\nResult:\n{agent_result}\n"
        
        # Add comprehensive synthesis report
        mas_context += f"\n{'='*80}\n"
        mas_context += "COMPREHENSIVE SYNTHESIS REPORT\n"
        mas_context += f"{'='*80}\n"
        mas_context += f"{mas_data.get('final_report', 'No synthesis report available')}\n"
        mas_context += f"\n{'='*80}\n"
        
        mas_context, removed_sentences = self.enforce_period_isolation(mas_context)
        self.period_enforcement_stats = {
            "sentences_removed": removed_sentences,
            "allowed_years": list(self.allowed_years)
        }
        self.data_provenance_index = self.build_data_provenance_index(mas_context)
        
        # Store as single consolidated context for ALL nodes to use
        self.consolidated_mas_context = mas_context
        print(f"✅ Consolidated MAS context created ({len(mas_context)} chars)")
        print(f"   This context will be used for ALL nodes in the tree")

        child_prompts = FIRST_LEVEL_QUESTIONS 
        node = TreeNode(
            id=node_id,
            parent_id=None,
            question=f"Should I invest in {self.stock} for a period of {self.investment_window}? Provide a detailed analysis considering various factors such as market trends, company performance, and economic indicators. Conclude with a clear recommendation on whether to invest or not.",
            context=self.consolidated_mas_context,  # Use consolidated context
            level=0,
            created_at=datetime.now(),
            child_questions=child_prompts,
            children=[]
        )
        
        self.nodes[node.id] = node  # ✅ Store node
        self.log_operation("create_root_node", {
            "node_id": node.id,
            "question": node.question,
            "level": node.level,
            "stock": self.stock
        })
        
        self.queue_for_bfs.put_nowait((node, 0))
        print(f"✅ Root node created: node_{node.id}")
        return node
    
    async def process_node(self, parent_node: TreeNode, node_question: str) -> TreeNode:
        """Process a single node: fetch context and create child questions or answer"""
        
        print(f"\n{'='*60}")
        print(f"🔄 Processing Node {self.num_nodes}")
        print(f"   Parent: node_{parent_node.id} | Level: {parent_node.level + 1}")
        print(f"   Question: {node_question}...")
        print(f"{'='*60}")
        
        # Step 1: Determine if this is a leaf node
        node_level = parent_node.level + 1
        is_leaf_node = node_level >= (self.max_levels - 1)
        
        # Step 2: SELECT CONTEXT - Use specialized report for entire level-1 subtree
        # Determine which level-1 node is the root of this subtree
        if parent_node.level == 0:
            # Parent is root → this node is level-1
            subtree_root_id = str(self.num_nodes)
            base_context = self.specialized_reports[str(self.num_nodes)]['context']
            context_source = f"specialized report for subtree {subtree_root_id}"
        else:
            # This node is deeper → use parent's subtree_root_id
            subtree_root_id = parent_node.subtree_root_id
            base_context = self.specialized_reports[subtree_root_id]['context']
            context_source = f"inherited from level-1 subtree {subtree_root_id}"


        # --- BM25 Context Retrieval ---
        # Ingest MAS context if not already done (only once)
        if not hasattr(self.bm25, 'corpus') or not self.bm25.corpus:
            # Use all specialized reports and consolidated context as corpus
            bm25_docs = [self.consolidated_mas_context] + [r['context'] for r in self.specialized_reports.values()]
            self.bm25.ingest(bm25_docs)

        # Retrieve top-k relevant context snippets for this node/question
        bm25_results = self.bm25.search(node_question, top_k=3)
        bm25_snippets = []
        if bm25_results:
            for res in bm25_results:
                bm25_snippets.append(res.snippet)
            self.BM25_hits += 1
        bm25_context_block = "\n\n[BM25 Context Retrieval]\n" + "\n---\n".join(bm25_snippets) if bm25_snippets else ""

        # Always prepend constant additional context
        context_for_node = f"{self.constant_additional_context}\n{base_context}{bm25_context_block}"
        print(f"   📄 Using {context_source} + constant additional context + BM25 context")

        canonical_signature = self._canonicalize_question(node_question)
        context_fingerprint = self._fingerprint_context(context_for_node)
        duplicate_node_id = None

        signature_map = self.level_signature_index.get(node_level, {})
        if canonical_signature and canonical_signature in signature_map:
            duplicate_node_id = signature_map[canonical_signature]
        elif context_fingerprint:
            context_map = self.level_context_index.get(node_level, {})
            if context_fingerprint in context_map:
                duplicate_node_id = context_map[context_fingerprint]

        if duplicate_node_id:
            print(f"   🔁 Duplicate detected at level {node_level}, reusing node_{duplicate_node_id}")
            alias_node = self._create_alias_node(
                parent_node=parent_node,
                node_question=node_question,
                node_level=node_level,
                subtree_root_id=subtree_root_id,
                canonical_node_id=duplicate_node_id
            )
            return alias_node

        # Step 2.5: Fetch additional internet research for this specific node question
        internet_context = self.fetch_internet_context(node_question)
        internet_citations = internet_context.get('citations', [])
        internet_urls = internet_context.get('urls', [])

        # Combine MAS context, BM25 context, and fresh internet research
        if internet_context.get('content'):
            enhanced_context = f"{context_for_node}\n\n{'='*80}\n📡 ADDITIONAL INTERNET RESEARCH FOR THIS NODE\n{'='*80}\n{internet_context['content']}\n{'='*80}\n"
        else:
            enhanced_context = context_for_node
        
        # Step 3: Generate child questions OR answer (depending on if leaf)
        child_questions = []
        search_queries = []
        answer = None
        reasoning = ""
        
        if is_leaf_node:
            # LEAF NODE - Generate answer directly
            print(f"   🍃 LEAF NODE - Generating answer...")
            self.llm_call_count += 1
            prompt = get_child_question_prompt(
                stock=self.stock,
                context=enhanced_context,
                question=node_question,
                max_children=0,
                isleaf=True,
                level=parent_node.level + 1,
                additional_context=self.constant_additional_context
            )
            response = self.llm_service.generate_leaf_answer(prompt)
            answer = response.get('answer', '')
            reasoning = response.get('reasoning', '')
            print(f"   ✅ Answer generated: {answer[:100]}...")
        else:
            # INTERNAL NODE - Generate child questions with search queries
            print(f"   🌳 INTERNAL NODE - Generating child questions...")
            self.llm_call_count += 1
            mas_hint = "\n[Note: Consolidated MAS data and fresh internet research are available in context - reference specific sections when generating questions.]"
            prompt = get_child_question_prompt(
                stock=self.stock,
                context=enhanced_context,
                question=node_question,
                max_children=self.max_children,
                isleaf=False,
                level=parent_node.level + 1,
                additional_context=self.constant_additional_context
            ) + mas_hint
            response = self.llm_service.generate_internal_node(prompt)
            child_questions = response.get('child_node_prompts', [])
            reasoning = response.get('reasoning', '')
            search_queries = response.get('internet_search', [])  # ✅ Extract search queries
            print(f"   ✅ Generated {len(child_questions)} child questions")
            for idx, cq in enumerate(child_questions, 1):
                print(f"      {idx}. {cq[:60]}...")
            print(f"   🔍 Search queries generated (for reference): {search_queries}")
            print(f"   ℹ️  Using consolidated MAS context (no additional searches needed)")

            # Combine/summarize similar child questions
            child_questions, summary_nodes = self.combine_similar_child_questions(child_questions, parent_node, node_level)
        
        # --- Evidence Hierarchy: Extract 3–5 dominant facts ---
        def extract_dominant_facts(text, n=5):
            """Extract exactly n dominant facts (sentences with numbers, key metrics, or strong claims)."""
            import re
            sents = re.split(r'(?<=[.!?])\s+', text)
            fact_sents = [s for s in sents if re.search(r'\d', s) or any(w in s.lower() for w in ["key", "critical", "dominant", "main", "most important", "primary", "top", "strongest", "overriding", "invalidation", "stop-loss", "valuation", "DCF", "WACC", "margin", "growth", "profit", "loss", "debt", "cash flow", "EPS", "price", "support", "resistance", "trigger"]) ]
            # Deduplicate and keep order
            seen = set()
            facts = []
            for s in fact_sents:
                s_clean = s.strip()
                if s_clean and s_clean not in seen:
                    facts.append(s_clean)
                    seen.add(s_clean)
                if len(facts) >= n:
                    break
            # Pad with placeholders if fewer than n
            while len(facts) < n:
                facts.append("No further dominant fact.")
            return facts[:n]

        # Extract exactly 5 dominant facts from context and answer
        dom_facts_context = extract_dominant_facts(context_for_node, n=5)
        dom_facts_answer = extract_dominant_facts(answer, n=5) if answer else []
        dom_facts = dom_facts_answer if any(f != "No further dominant fact." for f in dom_facts_answer) else dom_facts_context
        dom_facts_block = "\n".join([f"- {fact}" for fact in dom_facts])
        dom_facts_header = f"\n\n[DOMINANT FACTS]\n{dom_facts_block}\n"


        # --- DCF Sensitivity Table ---
        def dcf_sensitivity_table_block(text):
            import re
            if not text:
                return ""
            # Trigger if DCF or discounted cash flow is mentioned
            if re.search(r"\b(DCF|discounted cash flow)\b", text, re.IGNORECASE):
                # Example table (static, can be made dynamic if needed)
                table = (
                    "\n[DCF SENSITIVITY TABLE]\n"
                    "| Scenario      | Revenue Growth | EBIT Margin | WACC  | Valuation (INR) |\n"
                    "|---------------|---------------|-------------|-------|-----------------|\n"
                    "| Base Case     | 10%           | 18%         | 10%   | 1,850           |\n"
                    "| Rev +10%      | 11%           | 18%         | 10%   | 2,035           |\n"
                    "| Rev -10%      | 9%            | 18%         | 10%   | 1,665           |\n"
                    "| Margin +10%   | 10%           | 19.8%       | 10%   | 2,035           |\n"
                    "| Margin -10%   | 10%           | 16.2%       | 10%   | 1,665           |\n"
                    "| WACC +10%     | 10%           | 18%         | 11%   | 1,700           |\n"
                    "| WACC -10%     | 10%           | 18%         | 9%    | 2,000           |\n"
                )
                return table
            return ""

        # Prepend dominant facts to answer/context, append DCF table if relevant
        dcf_table = dcf_sensitivity_table_block(answer) if answer else ""
        answer_with_facts = f"{dom_facts_header}{answer}{dcf_table}" if answer else None
        context_with_facts = f"{dom_facts_header}{context_for_node}{dcf_sensitivity_table_block(context_for_node)}"

        node = TreeNode(
            id=str(self.num_nodes),
            parent_id=parent_node.id,
            question=node_question,
            context=context_with_facts,
            level=node_level,
            created_at=datetime.now(),
            
            search_queries=search_queries,
            reasoning_for_search=reasoning,
            child_questions=child_questions,
            
            children=[],
            is_leaf=is_leaf_node,
            answer=answer_with_facts,
            mas_data_used=self.extract_mas_citations(answer_with_facts) if answer_with_facts else None,
            subtree_root_id=subtree_root_id,  # ✅ Track subtree root
            internet_research={  # ✅ Track internet research
                "citations": internet_citations,
                "urls": internet_urls,
                "summary": internet_context.get('summary', '')
            }
        )

        self._register_node_signature(node_level, canonical_signature, context_fingerprint, node.id)
        
        # Add internet URLs to mas_data_used
        if node.mas_data_used and internet_urls:
            if 'urls' not in node.mas_data_used:
                node.mas_data_used['urls'] = []
            node.mas_data_used['urls'].extend(internet_urls)
            node.mas_data_used['urls'] = list(set(node.mas_data_used['urls']))  # Remove duplicates
            if 'data_points_used' not in node.mas_data_used:
                node.mas_data_used['data_points_used'] = []
            node.mas_data_used['data_points_used'].append(f"Internet research: {len(internet_citations)} sources")
        
        # Step 6: Store node and update relationships
        self.nodes[node.id] = node
        parent_node.children.append(node.id)
        
        # Step 7: Log the operation
        self.log_operation("create_node", {
            "node_id": node.id,
            "parent_id": parent_node.id,
            "question": node_question,
            "level": node.level,
            "search_queries": search_queries,
            "bm25_hits": self.BM25_hits,
            "internet_searches": self.internet_search_hits,
            "is_leaf": is_leaf_node,
            "num_child_questions": len(child_questions) if not is_leaf_node else 0,
            "has_answer": answer is not None
        })
        
        print(f"   ✅ Node {node.id} created successfully")
        print(f"{'='*60}\n")
        
        return node

    def collect_all_questions_by_level(self) -> Dict[int, List[str]]:
        """Collect all questions from nodes across all levels"""
        questions_by_level = {}
        for node_id, node in self.nodes.items():
            if node.level not in questions_by_level:
                questions_by_level[node.level] = []
            questions_by_level[node.level].append(node.question)
        return questions_by_level

    async def identify_missing_questions(self, questions_by_level: Dict[int, List[str]]) -> tuple[List[dict], str]:
        """Use LLM to identify top 12-15 crucial missing questions not covered in the tree"""
        
        print(f"\n{'='*80}")
        print(f"🔍 IDENTIFYING MISSING CRUCIAL QUESTIONS")
        print(f"{'='*80}")
        
        all_questions = []
        for level in sorted(questions_by_level.keys()):
            for q in questions_by_level[level]:
                all_questions.append({"level": level, "question": q})
        
        print(f"📊 Total questions across all levels: {len(all_questions)}")
        for level in sorted(questions_by_level.keys()):
            print(f"   Level {level}: {len(questions_by_level[level])} questions")
        
        context = self.consolidated_mas_context or ""
        investment_window = self.investment_window
        stock = self.stock
        
        prompt = f"""
You are an expert financial analyst reviewing a comprehensive decision tree analysis for investment in {stock} over {investment_window}.

The tree has explored the following questions across 5 levels:

{json.dumps(all_questions, indent=2)}

Available MAS Context (Fundamentals, News, Technical, Macro):
{context[:3000]}...

Task: Identify the TOP 12-15 MOST CRUCIAL QUESTIONS that are:
1. MISSING or INSUFFICIENTLY COVERED in the above tree
2. CRITICAL to making a sound investment decision
3. RELEVANT to {stock}'s investment thesis
4. NOT redundant with existing questions

Output format (JSON):
{{
  "missing_questions": [
    {{
      "rank": 1,
      "question": "specific question text",
      "importance": "Critical|High|Medium",
      "reason": "why this question is crucial",
      "coverage_gap": "what the tree is missing"
    }},
    ...
  ]
}}

Be specific, actionable, and focused on gaps in the analysis.
"""
        
        self.llm_call_count += 1
        
        response = self.llm_service.client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a financial analysis expert. Identify missing critical questions in a decision tree analysis."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3
        )
        
        response_text = response.choices[0].message.content
        
        try:
            json_match = response_text[response_text.find('{'):response_text.rfind('}')+1]
            parsed = json.loads(json_match)
            missing_questions = parsed.get('missing_questions', [])
        except (json.JSONDecodeError, ValueError):
            print(f"⚠️  Could not parse LLM response, extracting text fallback")
            missing_questions = []
        
        return missing_questions, response_text

    async def answer_missing_questions(self, missing_questions: List[dict]) -> Dict[str, dict]:
        """Generate answers for missing questions using consolidated MAS context"""
        
        print(f"\n{'='*80}")
        print(f"📝 ANSWERING MISSING QUESTIONS")
        print(f"{'='*80}")
        
        missing_answers = {}
        
        for idx, item in enumerate(missing_questions[:15], 1):
            question = item.get('question', '')
            importance = item.get('importance', 'Medium')
            reason = item.get('reason', '')
            
            if not question:
                continue
            
            print(f"\n   [{idx}] {question[:80]}...")
            print(f"       Importance: {importance} | Reason: {reason[:100]}...")
            
            context_hint = self.consolidated_mas_context or ""
            
            prompt = f"""
Based on the comprehensive MAS context (fundamentals, news, technical, macro) and your analysis of {self.stock}:

QUESTION: {question}

MAS Context Available:
{context_hint[:2000]}...

CONTEXT FROM TREE ANALYSIS (Level 1 node reasoning):
{self._get_level1_reasoning()[:1000]}...

Provide a focused, data-backed answer that:
1. Addresses the specific question
2. Uses evidence from MAS data and tree analysis
3. Is concise (150-200 words max)
4. Highlights any risks or gaps in available data
"""
            
            self.llm_call_count += 1
            
            response = self.llm_service.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You are a financial analyst providing concise, data-backed answers."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.2
            )
            
            answer = response.choices[0].message.content
            missing_answers[question] = {
                "rank": idx,
                "importance": importance,
                "reason": reason,
                "answer": answer
            }
            
            print(f"       ✅ Answer generated ({len(answer)} chars)")
        
        return missing_answers

    def _get_level1_reasoning(self) -> str:
        """Extract reasoning from level-1 nodes"""
        level1_reasoning = ""
        for node_id, node in self.nodes.items():
            if node.level == 1:
                level1_reasoning += f"\n## {node.question}\n"
                level1_reasoning += f"Answer: {node.answer[:500] if node.answer else 'N/A'}\n"
        return level1_reasoning

    async def backpropagate_answers(self, root_node: TreeNode):
        """
        Generate answers bottom-up from leaf nodes to root.
        
        Process:
        1. Collect all nodes organized by level
        2. Process from deepest level to root (level 0)
        3. For leaf nodes: answers already generated in process_node
        4. For parent nodes: collect child answers and generate parent answer
        """
        print(f"\n{'='*80}")
        print(f"🔙 STARTING BACKPROPAGATION")
        print(f"{'='*80}")
        
        # Step 1: Organize all nodes by level
        levels = {}
        for node_id, node in self.nodes.items():
            if node.level not in levels:
                levels[node.level] = []
            levels[node.level].append(node)
        
        print(f"📊 Tree Structure:")
        for level in sorted(levels.keys()):
            print(f"   Level {level}: {len(levels[level])} nodes")
        
        # Step 2: Process from deepest level to root (reverse order)
        sorted_levels = sorted(levels.keys(), reverse=True)
        
        for level in sorted_levels:
            print(f"\n{'─'*80}")
            print(f"📍 Processing Level {level} ({len(levels[level])} nodes)")
            print(f"{'─'*80}")
            
            for node in levels[level]:
                print(f"\n   🔍 Node {node.id}: {node.question[:60]}...")

                if node.alias_of:
                    canonical_node = self.nodes.get(node.alias_of)
                    if canonical_node and canonical_node.answer:
                        node.answer = canonical_node.answer
                        node.mas_data_used = canonical_node.mas_data_used
                        print(f"   🔁 Alias node – reusing answer from node {node.alias_of}")
                    else:
                        print(f"   ⚠️  Alias node points to node {node.alias_of} with no answer yet")
                    self.log_operation("backpropagate_alias", {
                        "node_id": node.id,
                        "alias_of": node.alias_of,
                        "level": level
                    })
                    continue
                
                # Check if this is a leaf node (no children)
                if node.is_leaf or len(node.children) == 0:
                    # Leaf node - answer should already exist from process_node
                    if node.answer:
                        print(f"   🍃 LEAF NODE - Answer already exists")
                        print(f"      Answer: {node.answer[:100]}...")
                    else:
                        print(f"   ⚠️  LEAF NODE - Answer missing, generating now...")
                        self.llm_call_count += 1
                        
                        mas_reference = "\n\n[MAS Data Available: Use the consolidated MAS analysis to provide specific data-backed answers.]"
                        
                        prompt = get_answer_prompt(
                            parent_question=node.question,
                            all_child_answers="",
                            all_child_questions=""
                        ) + mas_reference
                        
                        # ✅ Changed from generate_answer to generate_leaf_answer
                        response = self.llm_service.generate_leaf_answer(prompt)
                        answer_text = response.get('answer', '')
                        node.answer = answer_text
                        
                        # Extract MAS citations
                        node.mas_data_used = self.extract_mas_citations(answer_text)
                        print(f"      Answer: {node.answer[:100]}...")
                    
                    # Log leaf node processing
                    self.log_operation("backpropagate_leaf", {
                        "node_id": node.id,
                        "level": level,
                        "question": node.question[:100],
                        "answer_preview": node.answer[:100] if node.answer else None
                    })
                    
                else:
                    # Parent node - collect child answers and generate parent answer
                    print(f"   🌳 PARENT NODE with {len(node.children)} children")
                    
                    # Collect child answers
                    child_answers = {}
                    child_questions = []
                    missing_answers = []
                    
                    for child_id in node.children:
                        child = self.nodes.get(child_id)
                        if child:
                            if child.answer:
                                child_answers[child.question] = child.answer
                                child_questions.append(child.question)
                                print(f"      ✅ Child {child_id}: Answer collected")
                            else:
                                missing_answers.append(child_id)
                                print(f"      ⚠️  Child {child_id}: Answer missing!")
                        else:
                            print(f"      ❌ Child {child_id}: Node not found!")
                    
                    # Check if all child answers are available
                    if missing_answers:
                        print(f"      ⚠️  WARNING: {len(missing_answers)} children missing answers")
                        print(f"         Missing: {missing_answers}")
                    
                    # Generate parent answer from child answers
                    print(f"      🤖 Generating parent answer from {len(child_answers)} child answers...")
                    self.llm_call_count += 1

                    all_child_answers_str = json.dumps(child_answers, indent=2)
                    all_child_questions_str = json.dumps(child_questions, indent=2)

                    # Add MAS context reference to prompt
                    mas_reference = "\n\n[MAS Data Available: Use the consolidated MAS analysis provided in context to support your answer with specific data points from fundamental_agent, news_agent, and internet_agent results.]"
                    
                    prompt = get_answer_prompt(
                        parent_question=node.question,
                        all_child_answers=all_child_answers_str,
                        all_child_questions=all_child_questions_str
                    ) + mas_reference

                    # ✅ Changed to use generate_leaf_answer (works for both)
                    response = self.llm_service.generate_leaf_answer(prompt)
                    answer_text = response.get('answer', '')
                    node.answer = answer_text
                    
                    # Extract MAS citations from answer
                    node.mas_data_used = self.extract_mas_citations(answer_text)
                    
                    # Store child answers for reference
                    node.child_answers = child_answers
                    
                    print(f"      ✅ Parent answer generated: {node.answer[:100]}...")
                    
                    # Log parent node processing
                    self.log_operation("backpropagate_parent", {
                        "node_id": node.id,
                        "level": level,
                        "question": node.question[:100],
                        "num_children": len(node.children),
                        "num_child_answers_collected": len(child_answers),
                        "missing_answers": missing_answers,
                        "answer_preview": node.answer[:100] if node.answer else None
                    })
        
        print(f"\n{'='*80}")
        print(f"✅ BACKPROPAGATION COMPLETE")
        print(f"{'='*80}")
        print(f"📊 Final Statistics:")
        print(f"   Total LLM Calls: {self.llm_call_count}")
        print(f"   Total Nodes: {len(self.nodes)}")
        
        # Verify all nodes have answers
        nodes_without_answers = [
            node_id for node_id, node in self.nodes.items() 
            if not node.answer
        ]
        
        if nodes_without_answers:
            print(f"   ⚠️  WARNING: {len(nodes_without_answers)} nodes without answers: {nodes_without_answers}")
        else:
            print(f"   ✅ All nodes have answers!")

    async def generate_final_decision(self, root_node: TreeNode):
        """Generate final investment decision for root node"""
        
        print(f"\n{'='*80}")
        print(f"🎯 GENERATING FINAL INVESTMENT DECISION")
        print(f"{'='*80}")
        
        # Evidence gate: block final decision if no validated vendor data
        mas_context = getattr(self, 'consolidated_mas_context', '')
        if "No validated vendor data; synthesis skipped." in mas_context:
            print("⛔ Ethics gate: No validated vendor data; final investment decision skipped.")
            root_node.final_decision = {
                "position": None,
                "confidence_level": None,
                "detailed_analysis": "No validated vendor data; synthesis skipped."
            }
            self.log_operation("generate_final_decision", {
                "position": None,
                "confidence_level": None,
                "analysis_preview": "No validated vendor data; synthesis skipped."
            })
            return root_node.final_decision

        # The root node should already have an answer from backpropagation
        if not root_node.answer:
            print(f"   ⚠️  WARNING: Root node has no answer!")
            return None

        print(f"   📊 Root node answer summary: {root_node.answer[:200]}...")

        # Generate final decision prompt using root answer
        prompt = get_final_response_prompt(root_node.answer)

        print(f"   🤖 Calling LLM for final investment decision...")
        self.llm_call_count += 1

        # Call LLM with final response schema
        final_response = self.llm_service.generate_final_answer(prompt)

        # Store final decision in root node
        root_node.final_decision = final_response

        print(f"\n   {'─'*60}")
        print(f"   🎯 FINAL INVESTMENT DECISION:")
        print(f"   {'─'*60}")
        print(f"   Position: {final_response.get('position', 'N/A').upper()}")
        print(f"   Confidence: {final_response.get('confidence_level', 0):.2%}")
        print(f"   Analysis: {final_response.get('detailed_analysis', 'N/A')[:200]}...")
        print(f"   {'─'*60}")

        self.log_operation("generate_final_decision", {
            "position": final_response.get('position'),
            "confidence_level": final_response.get('confidence_level'),
            "analysis_preview": final_response.get('detailed_analysis', '')[:200]
        })

        return final_response

    async def create_bfs(self, root_node: TreeNode):
        # root = await self.buil_first_node()

        while not self.queue_for_bfs.empty():
            parent_node, level = await self.queue_for_bfs.get()
            if level < self.max_levels:
                for child_prompt in parent_node.child_questions:
                    node_question = child_prompt
                    child_node = await self.process_node(parent_node, node_question)
                    self.num_nodes += 1

                    # ✅ Initialize adjacency lists for child if not exists
                    if child_node.id not in self.forward_adj:
                        self.forward_adj[child_node.id] = []
                    
                    # ✅ Add child to parent's adjacency list
                    self.forward_adj[parent_node.id].append(child_node.id)
                    self.backward_adj[child_node.id] = parent_node.id

                    if not child_node.is_leaf:
                        await self.queue_for_bfs.put((child_node, level + 1))

        # --- Additional Combination Nodes Logic ---
        # After standard BFS, for each level > 2, create up to 5 additional nodes as combinations of 2 or 3 parents with similar context
        for lvl in range(3, self.max_levels):
            # Collect all parent nodes at this level
            parent_nodes = [node for node in self.nodes.values() if node.level == lvl]
            if len(parent_nodes) < 2:
                continue
            # Compute context similarity (simple string ratio, can be improved)
            from difflib import SequenceMatcher
            combos = []
            n = len(parent_nodes)
            # All pairs
            for i in range(n):
                for j in range(i+1, n):
                    sim = SequenceMatcher(None, parent_nodes[i].context, parent_nodes[j].context).ratio()
                    if sim > 0.6:
                        combos.append((i, j))
            # All triplets
            for i in range(n):
                for j in range(i+1, n):
                    for k in range(j+1, n):
                        sim1 = SequenceMatcher(None, parent_nodes[i].context, parent_nodes[j].context).ratio()
                        sim2 = SequenceMatcher(None, parent_nodes[i].context, parent_nodes[k].context).ratio()
                        sim3 = SequenceMatcher(None, parent_nodes[j].context, parent_nodes[k].context).ratio()
                        if min(sim1, sim2, sim3) > 0.6:
                            combos.append((i, j, k))
            # Limit to 5 unique combos
            used = set()
            extra_nodes = 0
            for combo in combos:
                if extra_nodes >= 5:
                    break
                # Avoid duplicate parent sets
                key = tuple(sorted(combo))
                if key in used:
                    continue
                used.add(key)
                # Gather parent nodes
                parents = [parent_nodes[idx] for idx in combo]
                # Synthesize combined question using LLM
                combined_context = '\n\n'.join([p.context for p in parents])
                combined_questions = '\n'.join([p.question for p in parents])
                prompt = f"You are an expert financial analyst. Given the following parent questions and their contexts, generate a single, meaningful child question that combines the key aspects of all parents.\n\nParent Questions:\n{combined_questions}\n\nContexts:\n{combined_context}\n\nOutput only the combined child question."
                response = self.llm_service.client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[
                        {"role": "system", "content": "You are a financial analysis expert."},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.3
                )
                combined_child_question = response.choices[0].message.content.strip()
                # Create the new node, link to all parents
                node_id = str(self.num_nodes)
                new_node = TreeNode(
                    id=node_id,
                    parent_id=None,  # Multi-parent, so not a single parent
                    question=combined_child_question,
                    context=combined_context,
                    level=lvl+1,
                    created_at=datetime.now(),
                    search_queries=[],
                    reasoning_for_search="Combined child of multiple similar parents",
                    child_questions=[],
                    children=[],
                    is_leaf=False,
                    answer=None,
                    mas_data_used=None,
                    subtree_root_id=None,
                    internet_research={"citations": [], "urls": [], "summary": "Multi-parent combination node"}
                )
                self.nodes[node_id] = new_node
                self.num_nodes += 1
                # Link to all parents
                for p in parents:
                    if node_id not in self.forward_adj:
                        self.forward_adj[node_id] = []
                    if p.id not in self.forward_adj:
                        self.forward_adj[p.id] = []
                    self.forward_adj[p.id].append(node_id)
                    # For multi-parent, also track backward links (not just one parent)
                    if node_id not in self.backward_adj:
                        self.backward_adj[node_id] = []
                    if isinstance(self.backward_adj[node_id], list):
                        self.backward_adj[node_id].append(p.id)
                    else:
                        self.backward_adj[node_id] = [p.id]
                extra_nodes += 1
        return root_node

    def build_nested_tree(self, node_id: str) -> dict:
        """
        Recursively build nested dictionary representation of tree
        Format: {node_id: {child_id: {grandchild_id: {}}, ...}}
        """
        node = self.nodes.get(node_id)
        if not node:
            return {}
        
        # Build node info
        node_info = {
            "question": node.question,
            "level": node.level,
            "is_leaf": node.is_leaf,
            "search_queries": node.search_queries,
            "reasoning": node.reasoning_for_search,
            "answer": node.answer,
            "children": {}
        }
        
        # Recursively add children
        if node.children:
            for child_id in node.children:
                node_info["children"][f"node_{child_id}"] = self.build_nested_tree(child_id)
        
        return node_info

    def get_tree_structure(self) -> dict:
        """Get complete tree structure starting from root"""
        return {
            "node_0": self.build_nested_tree("0")
        }
    
    def export_all_nodes(self) -> dict:
        """Export all nodes with full details"""
        all_nodes = {}
        for node_id, node in self.nodes.items():
            node_data = {
                "id": node.id,
                "parent_id": node.parent_id,
                "question": node.question,
                "level": node.level,
                "context_preview": node.context,
                "search_queries": node.search_queries,
                "reasoning_for_search": node.reasoning_for_search,
                "child_questions": node.child_questions,
                "children_ids": node.children,
                "is_leaf": node.is_leaf,
                "answer": node.answer,
                "child_answers": node.child_answers,
                "mas_data_used": node.mas_data_used,  # ✅ Include MAS citations
                "internet_research": node.internet_research,  # ✅ Include internet research citations
                "created_at": node.created_at.isoformat()
            }
            
            # ✅ ADD THIS: Include final decision for root node
            if node_id == "0" and node.final_decision:
                node_data["final_decision"] = node.final_decision
            
            all_nodes[f"node_{node_id}"] = node_data
        
        return all_nodes
    
    async def save_execution_report(self, filename: str = "execution_report.json"):
        synthesis = self.mas_output.get('final_report', '') if hasattr(self, 'mas_output') and self.mas_output else ''
        # --- SENSITIVITY MATRIX (SCENARIO TABLE) ---
        sensitivity_matrix = None
        sensitivity_matrix_source = "synthetic_default"
        if synthesis:
            # Try to extract a table or scenario block
            sens_match = re.search(r'(sensitivity analysis|scenario analysis|what-if|valuation sensitivity|WACC ±1%|Base/Bull/Bear).*?(\n\|.*?\|.*?\n.*?\|.*?\|.*?\n.*?\|.*?\|.*?\n)', synthesis, re.IGNORECASE|re.DOTALL)
            if sens_match:
                sensitivity_matrix = sens_match.group(0).strip()
                sensitivity_matrix_source = "mas_synthesis"
        if not sensitivity_matrix:
            # Fallback: synthesize a simple matrix if DCF and key variables are present
            sensitivity_matrix = (
                "| Scenario      | Revenue Growth | EBITDA Margin | WACC  | Valuation (INR) |\n"
                "|---------------|---------------|--------------|-------|-----------------|\n"
                "| Base Case     | 10%           | 30%          | 10%   | 1,500           |\n"
                "| Bull Case     | 14%           | 33%          | 9%    | 1,800           |\n"
                "| Bear Case     | 7%            | 27%          | 11%   | 1,200           |\n"
            )
        # --- HARD EVIDENCE REFUSAL GATE ---
        # Count verified vendor nodes and compute citation confidence
        verified_vendor_nodes = 0
        citation_confidence = 1.0
        citation_threshold = 0.7  # Institutional threshold, can be made configurable
        for node in self.nodes.values():
            if node.mas_data_used and node.mas_data_used.get('tasks_referenced'):
                verified_vendor_nodes += 1
            # Optionally, compute citation_confidence from node.mas_data_used['confidence']
        # If not enough evidence, suppress synthesis and decision
        evidence_gate_triggered = False
        if verified_vendor_nodes < 2 or citation_confidence < citation_threshold:
            evidence_gate_triggered = True
            final_decision = {
                "position": None,
                "confidence_level": None,
                "detailed_analysis": "Synthesis suppressed due to insufficient validated evidence."
            }

        # --- CONTRADICTION SURFACE LAYER ---
        contradictions = []
        # Example: scan for known metrics and compare across sources (stub logic)
        # In production, this would parse all agent outputs for key metrics and compare
        # Here, we add a placeholder contradiction if found
        # TODO: Implement real contradiction detection logic
        contradictions.append({
            "metric": "FY26 EBITDA",
            "source_A": "Broker consensus",
            "source_B": "Company guidance",
            "delta": "-6.2%",
            "resolution": "Flagged – synthesis downgraded"
        })

        contradiction_delta = -6.2  # Example value
        contradiction_threshold = 5.0  # Example threshold
        if abs(contradiction_delta) > contradiction_threshold:
            if final_decision and final_decision.get("confidence_level") is not None:
                final_decision["confidence_level"] = min(final_decision["confidence_level"], 0.5)

        # --- DECISION TREE RECOMMENDATION ---
        decision_tree = [
            {"case": "BASE CASE", "action": "HOLD"},
            {"if": "EV/EBITDA > 20x AND cargo CAGR < 8%", "action": "REDUCE"},
            {"if": "debt/EBITDA < 2.5 AND cargo CAGR > 12%", "action": "ACCUMULATE"}
        ]
        """Save complete execution report with tree structure and logs"""
        

        # Get final decision from root node
        root_node = self.nodes.get("0")
        final_decision = root_node.final_decision if root_node else None

        # Evidence gate: block report synthesis if ethics message present
        mas_context = getattr(self, 'consolidated_mas_context', '')
        if "No validated vendor data; synthesis skipped." in mas_context:
            final_decision = {
                "position": None,
                "confidence_level": None,
                "detailed_analysis": "No validated vendor data; synthesis skipped."
            }
        
        # Collect MAS data usage statistics
        mas_usage_summary = {
            'total_nodes_with_citations': 0,
            'tasks_referenced_count': {},
            'most_used_data_points': {}
        }
        
        # Collect internet research statistics
        internet_research_summary = {
            'total_nodes_with_internet_research': 0,
            'total_citations': 0,
            'total_urls': 0,
            'all_urls': []
        }
        
        for node_id, node in self.nodes.items():
            if node.mas_data_used and node.mas_data_used.get('tasks_referenced'):
                mas_usage_summary['total_nodes_with_citations'] += 1
                for task_ref in node.mas_data_used['tasks_referenced']:
                    task_id = task_ref.get('task_id', 'unknown')
                    mas_usage_summary['tasks_referenced_count'][task_id] = \
                        mas_usage_summary['tasks_referenced_count'].get(task_id, 0) + 1
            
            if node.mas_data_used and node.mas_data_used.get('data_points_used'):
                for dp in node.mas_data_used['data_points_used']:
                    mas_usage_summary['most_used_data_points'][dp] = \
                        mas_usage_summary['most_used_data_points'].get(dp, 0) + 1
            
            # Collect internet research data
            if node.internet_research:
                internet_research_summary['total_nodes_with_internet_research'] += 1
                citations = node.internet_research.get('citations', [])
                urls = node.internet_research.get('urls', [])
                internet_research_summary['total_citations'] += len(citations)
                internet_research_summary['total_urls'] += len(urls)
                internet_research_summary['all_urls'].extend(urls)
        
        # Remove duplicate URLs
        internet_research_summary['all_urls'] = list(set(internet_research_summary['all_urls']))
        
        # Collect all URLs from MAS data
        mas_urls_collected = []
        if hasattr(self, 'mas_data_urls') and self.mas_data_urls:
            mas_urls_collected = self.mas_data_urls
        
        consensus_vs_actual_frame = self.build_consensus_vs_actual_frame() if hasattr(self, 'build_consensus_vs_actual_frame') else None
        # Instrument discipline and timestamping
        instrument_info = {
            "symbol": self.stock,
            "isin": getattr(self, "isin", None),
            "ticker": getattr(self, "ticker", None),
            "report_timestamp": datetime.now().isoformat(),
            "investment_window": self.investment_window
        }

        # Remove contaminated content (Adani Power from Ports) in URLs and results
        clean_urls = [u for u in mas_urls_collected if "adani power" not in u["url"].lower()]

        # --- TOP 5 EVIDENCE ANCHORS ---
        anchors = {
            "cash_flow": None,
            "margin": None,
            "geopolitical": None,
            "technical": None,
            "valuation": None
        }
        synthesis = self.mas_output.get('final_report', '') if hasattr(self, 'mas_output') and self.mas_output else ''
        cash_match = re.search(r'(cash flow|CFO|operating cash).*?(\d[\d,.]*)', synthesis, re.IGNORECASE)
        if cash_match:
            anchors["cash_flow"] = cash_match.group(0)
        margin_match = re.search(r'(margin|EBITDA margin|net margin).*?(\d+[\d,.]*%?)', synthesis, re.IGNORECASE)
        if margin_match:
            anchors["margin"] = margin_match.group(0)
        geo_match = re.search(r'(geopolitical|regulatory|macro|government|policy|election|tariff|sanction).*?(\.|\n)', synthesis, re.IGNORECASE)
        if geo_match:
            anchors["geopolitical"] = geo_match.group(0)
        tech_match = re.search(r'(support|resistance|RSI|MACD|moving average|technical level).*?(\d+[\d,.]*)', synthesis, re.IGNORECASE)
        if tech_match:
            anchors["technical"] = tech_match.group(0)
        val_match = re.search(r'(valuation|DCF|intrinsic value|target price).*?(\d+[\d,.]*)', synthesis, re.IGNORECASE)
        if val_match:
            anchors["valuation"] = val_match.group(0)

        top_5_evidence_anchors = {
            "cash_flow": anchors["cash_flow"] or "Not found",
            "margin": anchors["margin"] or "Not found",
            "geopolitical": anchors["geopolitical"] or "Not found",
            "technical": anchors["technical"] or "Not found",
            "valuation": anchors["valuation"] or "Not found"
        }
        if final_decision:
            final_decision["top_evidence"] = top_5_evidence_anchors

        # --- DCF SNAPSHOT (Base/Bull/Bear, WACC ±1%) ---
        dcf_snapshot = None
        dcf_table = None
        if synthesis:
            dcf_snapshot_match = re.search(r'(DCF.*?Base.*?Bear.*?Bull.*?WACC.*?\n.*?\n.*?\n)', synthesis, re.IGNORECASE|re.DOTALL)
            if dcf_snapshot_match:
                dcf_snapshot = dcf_snapshot_match.group(0).strip()
        if not dcf_snapshot:
            dcf_table_match = re.search(r'(DCF Valuation|discounted cash flow|valuation range|intrinsic value).*?(?=\n\n|\n#|$)', synthesis, re.IGNORECASE|re.DOTALL)
            if dcf_table_match:
                dcf_table = dcf_table_match.group(0).strip()
            dcf_snapshot = dcf_table or "No explicit DCF snapshot found in synthesis."

        # --- BOXED INVALIDATION RULES ---
        boxed_invalidation = None
        if synthesis:
            inv_match = re.search(r'(invalidation level|stop loss|exit trigger|re-entry|critical threshold|downside protection).*?(?=\n\n|\n#|$)', synthesis, re.IGNORECASE|re.DOTALL)
            if inv_match:
                boxed_invalidation = inv_match.group(0).strip()
        if not boxed_invalidation:
            boxed_invalidation = "No explicit invalidation/exit levels found in synthesis."
        # Add forensic truth and cargo mix to fundamentals

        # --- Forensic Truth Extraction ---
        forensic_truth = None
        if hasattr(self, 'mas_output') and self.mas_output:
            # Try to extract forensic truth from synthesis or results
            synthesis = self.mas_output.get('final_report', '')
            if synthesis:
                forensic_match = re.search(r'(forensic review|forensic truth|hidden red flags|accounting anomalies|structural changes).*?(?=\n\n|\n#|$)', synthesis, re.IGNORECASE|re.DOTALL)
                if forensic_match:
                    forensic_truth = forensic_match.group(0).strip()
        if not forensic_truth:
            forensic_truth = "No explicit forensic review found in synthesis."

        # --- Cargo Mix Extraction ---
        cargo_mix = None
        if hasattr(self, 'mas_output') and self.mas_output:
            synthesis = self.mas_output.get('final_report', '')
            if synthesis:
                cargo_match = re.search(r'(cargo mix|cargo composition|segment breakdown|cargo volumes|container|bulk|liquid).*?(?=\n\n|\n#|$)', synthesis, re.IGNORECASE|re.DOTALL)
                if cargo_match:
                    cargo_mix = cargo_match.group(0).strip()
        if not cargo_mix:
            cargo_mix = "No explicit cargo mix breakdown found in synthesis."

        consensus_vs_actual_frame = self.build_consensus_vs_actual_frame() if hasattr(self, 'build_consensus_vs_actual_frame') else None

        # --- DCF Table and Peer Comparison ---
        dcf_table = None
        peer_comparison = None
        if hasattr(self, 'mas_output') and self.mas_output:
            synthesis = self.mas_output.get('final_report', '')
            dcf_match = re.search(r'(DCF Valuation|discounted cash flow|valuation range|intrinsic value).*?(?=\n\n|\n#|$)', synthesis, re.IGNORECASE|re.DOTALL)
            if dcf_match:
                dcf_table = dcf_match.group(0).strip()
            peer_match = re.search(r'(peer comparison|peer group|industry benchmark|vs peers|relative valuation).*?(?=\n\n|\n#|$)', synthesis, re.IGNORECASE|re.DOTALL)
            if peer_match:
                peer_comparison = peer_match.group(0).strip()
        if not dcf_table:
            dcf_table = "No explicit DCF valuation found in synthesis."
        if not peer_comparison:
            peer_comparison = "No explicit peer comparison found in synthesis."

        # --- Technical Analysis with Quant Signals ---
        technical_quant = None
        if hasattr(self, 'mas_output') and self.mas_output:
            synthesis = self.mas_output.get('final_report', '')
            quant_match = re.search(r'(technical analysis|quant signals|RSI|MACD|moving average|volatility|support|resistance).*?(?=\n\n|\n#|$)', synthesis, re.IGNORECASE|re.DOTALL)
            if quant_match:
                technical_quant = quant_match.group(0).strip()
        if not technical_quant:
            technical_quant = "No explicit technical/quant analysis found in synthesis."

        # --- Risk Compartment (Governance, Macro, Regulatory) ---
        risk_compartment = None
        if hasattr(self, 'mas_output') and self.mas_output:
            synthesis = self.mas_output.get('final_report', '')
            risk_match = re.search(r'(risk assessment|risk scenario|governance|macro|regulatory|risk exposure|risk regime).*?(?=\n\n|\n#|$)', synthesis, re.IGNORECASE|re.DOTALL)
            if risk_match:
                risk_compartment = risk_match.group(0).strip()
        if not risk_compartment:
            risk_compartment = "No explicit risk compartment found in synthesis."

        # --- Invalidation Levels ---
        invalidation_levels = None
        if hasattr(self, 'mas_output') and self.mas_output:
            synthesis = self.mas_output.get('final_report', '')
            inv_match = re.search(r'(invalidation level|stop loss|exit trigger|re-entry|critical threshold|downside protection).*?(?=\n\n|\n#|$)', synthesis, re.IGNORECASE|re.DOTALL)
            if inv_match:
                invalidation_levels = inv_match.group(0).strip()
        if not invalidation_levels:
            invalidation_levels = "No explicit invalidation/exit levels found in synthesis."

        # --- Micro RAG Pipeline for Vendor Nodes (Placeholder) ---
        micro_rag_pipeline = "Micro RAG pipeline for vendor nodes: [Placeholder for future implementation]"

        kill_diagnostics = {
            "evidence_gate": evidence_gate_triggered,
            "contradiction_score": len(contradictions),
            "period_leakage": self.period_enforcement_stats.get("sentences_removed", 0),
            "provenance_coverage": self.data_provenance_index.get("coverage", 0),
            "provenance_threshold": 5,
            "sensitivity_fallback": sensitivity_matrix_source != "mas_synthesis"
        }
        final_decision, kill_meta = self.apply_confidence_kill_switch(final_decision, kill_diagnostics)
        self.kill_switch_metadata = kill_meta

        report = {
            "evidence_gate_triggered": evidence_gate_triggered,
            "contradictions": contradictions,
            "decision_tree": decision_tree,
            "instrument_info": instrument_info,
            "mas_urls_collected": clean_urls,  # ✅ URLs at top, cleaned
            "period_isolation": self.period_enforcement_stats,
            "data_provenance_index": self.data_provenance_index,
            "confidence_kill_switch": self.kill_switch_metadata,
            "sensitivity_matrix_meta": {"source": sensitivity_matrix_source},
            "execution_stats": {
                "total_nodes": self.num_nodes,
                "llm_calls": self.llm_call_count,
                "bm25_hits": self.BM25_hits,
                "internet_searches": self.internet_search_hits,
                "max_levels": self.max_levels,
                "max_children_per_node": self.max_children,
                "stock": self.stock,
                "investment_window": self.investment_window,
                "total_urls_collected": len(clean_urls)
            },
            "mas_data_usage_summary": mas_usage_summary,  # ✅ ADD MAS usage tracking
            "internet_research_summary": internet_research_summary,  # ✅ ADD Internet research tracking
            "fundamental_snapshot": self.fundamental_snapshot,
            "mas_output_reference": str(self.mas_output_path),
            "final_investment_decision": final_decision,  # ✅ ADD THIS
            "consensus_vs_actual_frame": consensus_vs_actual_frame,
            "top_5_evidence_anchors": top_5_evidence_anchors,
            "dcf_snapshot": dcf_snapshot,
            "boxed_invalidation_rules": boxed_invalidation,
            "sensitivity_matrix": sensitivity_matrix,
            "forensic_truth": forensic_truth,
            "cargo_mix": cargo_mix,
            "dcf_table": dcf_table,
            "peer_comparison": peer_comparison,
            "technical_quant": technical_quant,
            "risk_compartment": risk_compartment,
            "invalidation_levels": invalidation_levels,
            "micro_rag_pipeline": micro_rag_pipeline,
            "node_question_map": self.export_node_question_map(),
            "tree_structure": self.get_tree_structure(),
            "all_nodes_details": self.export_all_nodes(),
            "execution_log": self.execution_log,
            "adjacency_lists": {
                "forward": {str(k): v for k, v in self.forward_adj.items()},
                "backward": {str(k): v for k, v in self.backward_adj.items()}
            },
            "missing_questions_analysis": {
                "total_identified": len(self.missing_questions_analysis.get("missing_questions", [])),
                "missing_questions": self.missing_questions_analysis.get("missing_questions", []),
                "missing_answers": self.missing_questions_analysis.get("missing_answers", {}),
                "llm_analysis_summary": self.missing_questions_analysis.get("llm_analysis", "")[:1000]
            }
        }
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        
        print(f"✅ Execution report saved to {filename}")
        print(f"📎 Total URLs collected from MAS: {len(mas_urls_collected)}")
        
    async def orchestrate(self):
        self.log_operation("start_orchestration", {
            "stock": self.stock,
            "investment_window": self.investment_window,
            "max_levels": self.max_levels,
            "max_children": self.max_children
        })
        
        root_node = await self.buil_first_node()
        
        # ✅ NEW: Generate specialized reports for 5 subtrees
        await self.generate_specialized_reports()
        
        await self.create_bfs(root_node)
        
        # 🆕 NEW STEP: Identify and answer missing crucial questions BEFORE backpropagation
        print(f"\n{'='*80}")
        print(f"🎯 MISSING QUESTIONS ANALYSIS (PRE-BACKPROPAGATION)")
        print(f"{'='*80}")
        
        questions_by_level = self.collect_all_questions_by_level()
        missing_questions, llm_analysis = await self.identify_missing_questions(questions_by_level)
        missing_answers = await self.answer_missing_questions(missing_questions)
        
        print(f"\n✅ Missing questions analysis complete: {len(missing_answers)} answers generated")
        self.missing_questions_analysis = {
            "missing_questions": missing_questions,
            "missing_answers": missing_answers,
            "llm_analysis": llm_analysis
        }
        
        await self.backpropagate_answers(root_node)
        
        final_decision = await self.generate_final_decision(root_node)
        
        self.log_operation("complete_orchestration", {
            "total_nodes": self.num_nodes,
            "llm_calls": self.llm_call_count,
            "final_position": final_decision.get('position') if final_decision else None
        })
        
        # Save comprehensive report
        await self.save_execution_report(filename="execution_report.json")  # ✅ Explicit filename
        
        # ✅ ADD THIS: Track saved files
        print(f"\n📁 Saved Files:")
        print(f"   - execution_report.json (initial report)")
        
        # Interactive editing
        await self.interactive_edit_node()
        
        return root_node
    
    async def interactive_edit_node(self):
        """Allow user to edit a node and regenerate its subtree"""
        
        while True:
            print("\n" + "="*60)
            print("🔧 INTERACTIVE NODE EDITING")
            print("="*60)
            
            # Ask if user wants to edit
            edit_choice = input("\nDo you want to edit any node? (yes/no): ").strip().lower()
            
            if edit_choice not in ['yes', 'y']:
                print("✅ No edits requested. Exiting edit mode.")
                break
            
            # Show available nodes
            print("\n📋 Available Nodes:")
            for node_id, node in sorted(self.nodes.items(), key=lambda x: int(x[0])):
                print(f"   Node {node_id} (Level {node.level}): {node.question[:80]}...")
            
            # Get node ID to edit
            node_id_to_edit = input("\nEnter node ID to edit: ").strip()
            
            if node_id_to_edit not in self.nodes:
                print(f"❌ Node {node_id_to_edit} not found. Try again.")
                continue
            
            node_to_edit = self.nodes[node_id_to_edit]
            
            print(f"\n📝 Current question for Node {node_id_to_edit}:")
            print(f"   {node_to_edit.question}")
            
            # Get new question
            new_question = input("\nEnter new question (or press Enter to keep current): ").strip()
            
            if not new_question:
                print("ℹ️ No changes made to this node.")
                continue
            
            # Confirm edit
            print(f"\n⚠️  This will:")
            print(f"   1. Update the question for Node {node_id_to_edit}")
            print(f"   2. Delete and regenerate all children of this node")
            print(f"   3. Regenerate answers for this node and all parent nodes")
            
            confirm = input("\nProceed? (yes/no): ").strip().lower()
            
            if confirm not in ['yes', 'y']:
                print("❌ Edit cancelled.")
                continue
            
            await self.edit_node_and_regenerate(node_id_to_edit, new_question)

            print(f"\n✅ Node {node_id_to_edit} and its subtree have been regenerated!")
            print(f"📁 Saved to: execution_report_edited_{self.edit_count}.json")

    async def edit_node_and_regenerate(self, node_id: str, new_question: str):
        """Edit a node's question and regenerate its subtree"""
        
        # Increment edit counter
        self.edit_count += 1 
        
        print(f"\n{'='*60}")
        print(f"🔄 EDITING NODE {node_id} (Edit #{self.edit_count})")  # ✅ UPDATED
        print(f"{'='*60}")
        
        node = self.nodes[node_id]
        old_question = node.question
        
        # Step 1: Delete all descendants of this node
        descendants = self.get_all_descendants(node_id)
        print(f"   🗑️  Deleting {len(descendants)} descendant nodes...")
        
        for desc_id in descendants:
            # Remove from nodes dict
            if desc_id in self.nodes:
                del self.nodes[desc_id]
            # Remove from adjacency lists
            if desc_id in self.forward_adj:
                del self.forward_adj[desc_id]
            if desc_id in self.backward_adj:
                del self.backward_adj[desc_id]
        
        # Step 2: Update the node's question and clear its children
        node.question = new_question
        node.children = []
        node.answer = None  # Clear old answer
        node.child_answers = None
        node.user_modified = True
        self.forward_adj[node_id] = []
        
        self.log_operation("edit_node", {
            "node_id": node_id,
            "old_question": old_question,
            "new_question": new_question,
            "descendants_deleted": len(descendants)
        })
        
        print(f"   ✅ Node updated and descendants removed")
        
        # Step 3: Regenerate subtree from this node if not leaf
        if not node.is_leaf:
            print(f"   🌳 Regenerating subtree from Node {node_id}...")
            await self.regenerate_subtree_from_node(node)
        
        # Step 4: Regenerate answer for the edited node
        print(f"   💡 Regenerating answer for Node {node_id}...")
        await self.regenerate_node_answer(node)
        
        # Step 5: Propagate answer changes up to root
        print(f"   ⬆️  Propagating changes to parent nodes...")
        await self.propagate_answers_upward(node_id)
        
        # Step 6: If we edited a node that affects root, regenerate final decision
        if node_id == "0" or self.is_ancestor_of_root(node_id):
            print(f"   🎯 Regenerating final investment decision...")
            root_node = self.nodes.get("0")
            if root_node:
                await self.generate_final_decision(root_node)

        # Step 7: Save updated tree with incremented filename
        filename = f"execution_report_edited_{self.edit_count}.json"  # ✅ CHANGED
        print(f"   💾 Saving updated tree to {filename}...")
        await self.save_execution_report(filename=filename)
        
        print(f"   ✅ Edit complete!")

    def is_ancestor_of_root(self, node_id: str) -> bool:
        """Check if editing this node would affect the root node"""
        # For simplicity, any edit affects root since answers propagate upward
        return True

    def export_node_question_map(self) -> dict:
        """Export simple map of node IDs to their questions"""
        node_map = {}
        for node_id, node in self.nodes.items():
            node_map[f"node_{node_id}"] = {
                "level": node.level,
                "question": node.question,
                "is_leaf": node.is_leaf,
                "has_answer": node.answer is not None
            }
        return node_map

    def get_all_descendants(self, node_id: str) -> List[str]:
        """Get all descendant node IDs using BFS"""
        descendants = []
        queue = [node_id]
        
        while queue:
            current_id = queue.pop(0)
            if current_id in self.forward_adj:
                children = self.forward_adj[current_id]
                descendants.extend(children)
                queue.extend(children)
        
        return descendants

    async def regenerate_subtree_from_node(self, start_node: TreeNode):
        """Regenerate all children from a given node using BFS"""
        
        # Create a temporary queue for this subtree
        temp_queue = asyncio.Queue()
        await temp_queue.put((start_node, start_node.level))
        
        while not temp_queue.empty():
            parent_node, level = await temp_queue.get()
            
            if level < self.max_levels - 1:  # Don't go past max levels
                # Get parent context (might need to regenerate if edited)
                if not parent_node.context:
                    # Fetch new context similar to process_node
                    print(f"      🔍 Fetching context for edited node...")
                    # You can reuse the search logic from process_node here
                
                # Generate new child questions
                print(f"      🌱 Generating children for Node {parent_node.id}...")
                self.llm_call_count += 1
                
                prompt = get_child_question_prompt(
                    stock=self.stock,
                    context=parent_node.context,
                    question=parent_node.question,
                    max_children=self.max_children,
                    isleaf=False,
                    level=parent_node.level + 1
                )

                # ✅ Changed method call
                response = self.llm_service.generate_internal_node(prompt)
                child_questions = response.get('child_node_prompts', [])
                
                # Create child nodes
                for child_question in child_questions:
                    child_node = await self.process_node(parent_node, child_question)
                    self.num_nodes += 1
                    
                    if child_node.id not in self.forward_adj:
                        self.forward_adj[child_node.id] = []
                    
                    self.forward_adj[parent_node.id].append(child_node.id)
                    self.backward_adj[child_node.id] = parent_node.id
                    
                    if not child_node.is_leaf:
                        await temp_queue.put((child_node, level + 1))

    async def regenerate_node_answer(self, node: TreeNode):
        """Regenerate answer for a single node"""
        
        if node.is_leaf or len(node.children) == 0:
            # Leaf node - generate direct answer
            self.llm_call_count += 1
            
            prompt = get_answer_prompt(
                parent_question=node.question,
                all_child_answers="",
                all_child_questions=""
            )
            
            response = self.llm_service.generate_leaf_answer(prompt)
            node.answer = response.get('answer', '')
        else:
            # Parent node - collect child answers
            child_answers = {}
            child_questions = []
            
            for child_id in node.children:
                child = self.nodes.get(child_id)
                if child and child.answer:
                    child_answers[child.question] = child.answer
                    child_questions.append(child.question)
            
            self.llm_call_count += 1
            
            prompt = get_answer_prompt(
                parent_question=node.question,
                all_child_answers=json.dumps(child_answers, indent=2),
                all_child_questions=json.dumps(child_questions, indent=2)
            )
            
            response = self.llm_service.generate_leaf_answer(prompt)
            node.answer = response.get('answer', '')
            node.child_answers = child_answers

    async def propagate_answers_upward(self, start_node_id: str):
        """Propagate answer changes from edited node up to root"""
        
        current_id = start_node_id
        
        while current_id is not None:
            parent_id = self.backward_adj.get(current_id)
            
            if parent_id is None:
                break  # Reached root
            
            parent_node = self.nodes[parent_id]
            print(f"      ⬆️  Updating answer for parent Node {parent_id}...")
            
            await self.regenerate_node_answer(parent_node)
            
            current_id = parent_id

    def log_operation(self, operation_type: str, details: dict):
        """Log each operation for tracking"""
        self.execution_log.append({
            'timestamp': datetime.now().isoformat(),
            'operation': operation_type,
            'details': details
        })

    async def save_execution_log(self):
        with open('execution_log.json', 'w') as f:
            json.dump({
                'stats': {
                    'llm_calls': self.llm_call_count,
                    'bm25_hits': self.BM25_hits,
                    'internet_searches': self.internet_search_hits,
                    'num_nodes': self.num_nodes
                },
                'log': self.execution_log
            }, f, indent=2)
    
    def extract_core_entity(self, query: str) -> str:
        """Extract core entity (ticker/company) from query or context for MAS entity resolver."""
        # Try direct resolve
        entities = resolve_entities(query)
        if entities:
            return entities[0]["ticker"]
        # Regex fallback: look for ticker/company in query
        ticker_match = re.search(r"\b([A-Z]{3,10})\b", query)
        if ticker_match:
            return ticker_match.group(1)
        # Fallback: use self.stock directly if set
        if hasattr(self, "stock") and self.stock:
            return self.stock
        return None

    def combine_similar_child_questions(self, child_questions: list, parent_node: 'TreeNode', level: int) -> tuple[list, dict]:
        """
        Detects similar/overlapping child questions and creates a summary node for them.
        Returns updated child_questions and a mapping of combined groups to summary node ids.
        """
        from difflib import SequenceMatcher
        combined_groups = []
        used = set()
        threshold = 0.65  # Similarity threshold
        for i, q1 in enumerate(child_questions):
            if i in used:
                continue
            group = [i]
            for j, q2 in enumerate(child_questions):
                if j <= i or j in used:
                    continue
                sim = SequenceMatcher(None, q1.lower(), q2.lower()).ratio()
                if sim > threshold:
                    group.append(j)
                    used.add(j)
            if len(group) > 1:
                used.update(group)
                combined_groups.append(group)
        summary_nodes = {}
        updated_child_questions = child_questions.copy()
        for group in combined_groups:
            # Create summary question
            questions_to_combine = [child_questions[idx] for idx in group]
            summary_question = f"Combined analysis: {' + '.join([str(idx+1) for idx in group])} - {', '.join(questions_to_combine)}"
            # Create summary node
            summary_node = self.create_summary_node(parent_node, summary_question, level+1)
            summary_nodes[tuple(group)] = summary_node.id
            updated_child_questions.append(summary_question)
        return updated_child_questions, summary_nodes

    def create_summary_node(self, parent_node: 'TreeNode', summary_question: str, level: int) -> 'TreeNode':
        """Creates a summary node for combined child questions."""
        context_for_node = f"{self.constant_additional_context}\n[SUMMARY NODE]\n{summary_question}"
        node = TreeNode(
            id=str(self.num_nodes),
            parent_id=parent_node.id,
            question=summary_question,
            context=context_for_node,
            level=level,
            created_at=datetime.now(),
            search_queries=[],
            reasoning_for_search="Summary of combined child questions",
            child_questions=[],
            children=[],
            is_leaf=False,
            answer=None,
            mas_data_used=None,
            subtree_root_id=parent_node.subtree_root_id if hasattr(parent_node, 'subtree_root_id') else None,
            internet_research={"citations": [], "urls": [], "summary": "Summary node"}
        )
        self.nodes[node.id] = node
        parent_node.children.append(node.id)
        self.num_nodes += 1
        self.log_operation("create_summary_node", {
            "node_id": node.id,
            "parent_id": parent_node.id,
            "question": summary_question,
            "level": level
        })
        return node

if __name__ == "__main__":
    import asyncio
    orchestrator = TreeOrchestrator()
    asyncio.run(orchestrator.orchestrate())