from pydantic import BaseModel, ConfigDict
from typing import Dict, List, Optional, Any
from datetime import datetime

class TreeNode(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)
    
    id: str
    parent_id: Optional[str] = None
    question: str
    context: str
    level: int
    created_at: datetime

    # processing results
    search_queries: Optional[List[str]] = None
    reasoning_for_search: Optional[str] = None
    child_questions: Optional[List] = None

    # tree relationships
    children: List[str] = []
    is_leaf: bool = False
    subtree_root_id: Optional[str] = None  # ✅ Track which level-1 node is root of this subtree
    alias_of: Optional[str] = None
    aliases: List[str] = []
    alias_questions: List[str] = []

    # user modifications
    user_modified: bool = False
        
    # answers
    answer: Optional[str] = None
    child_answers: Optional[Dict[str, str]] = None
    needs_more_context: Optional[bool] = None
    
    # MAS data citations
    mas_data_used: Optional[Dict[str, Any]] = None
    
    # Internet research citations (from internet_agent)
    internet_research: Optional[Dict[str, Any]] = None
    
    final_decision: Optional[Dict[str, Any]] = None

class SearchResult(BaseModel):
    title: str
    link: str
    snippet: Optional[str] = None
    score: Optional[float] = None
    content: Optional[str] = None