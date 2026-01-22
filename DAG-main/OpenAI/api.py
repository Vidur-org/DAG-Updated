"""
FastAPI endpoint for Tree + MAS analysis system.

Exposes POST /analyze endpoint that orchestrates the Tree + MAS system
for stock/investment analysis.
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
import asyncio
import sys
import uuid
from pathlib import Path

# Add paths for imports
current_dir = Path(__file__).parent
mas_main_path = str(current_dir.parent / "MAS-main")
if current_dir not in sys.path:
    sys.path.insert(0, str(current_dir))
if mas_main_path not in sys.path:
    sys.path.insert(0, mas_main_path)

from tree_orchestrator_main import TreeOrchestrator
from preference_manager import PreferenceManager
from config import CONFIG
from session_storage import SessionStorage


app = FastAPI(title="Tree + MAS Analysis API", version="1.0.0")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify your frontend domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize PreferenceManager
preference_manager = PreferenceManager()

# Session storage: session_id -> orchestrator instance (in-memory for active sessions)
session_storage: Dict[str, TreeOrchestrator] = {}

# Persistent storage for sessions and reports
persistent_storage = SessionStorage(storage_dir="sessions")


# Request/Response Models
class Preferences(BaseModel):
    """User preferences for analysis"""
    max_levels: Optional[int] = Field(None, description="Maximum tree depth")
    max_children: Optional[int] = Field(None, description="Maximum children per node")
    preset: Optional[str] = Field(None, description="Preset name: 'fast', 'balanced', or 'thorough'")
    save: Optional[bool] = Field(False, description="Whether to save preferences for user")


class AnalyzeRequest(BaseModel):
    """Request body for /analyze endpoint"""
    user_id: str = Field(..., description="User identifier")
    query: str = Field(..., description="Investment analysis query")
    preferences: Optional[Preferences] = Field(None, description="Analysis preferences")


class AnalyzeResponse(BaseModel):
    """Response body for /analyze endpoint"""
    session_id: str = Field(..., description="Session ID for subsequent operations")
    answer: str = Field(..., description="Final aggregated analysis")
    execution_report: Dict[str, Any] = Field(..., description="Execution report with tree structure")
    metadata: Dict[str, Any] = Field(..., description="Metadata about the analysis")


class EditNodeRequest(BaseModel):
    """Request body for editing a node"""
    new_question: str = Field(..., description="New question for the node")


def resolve_preferences(
    user_id: str,
    request_preferences: Optional[Preferences]
) -> tuple[int, int, bool, bool]:
    """
    Resolve preferences from request, user saved preferences, presets, and defaults.
    
    Returns:
        tuple: (max_levels, max_children, should_save, used_saved_preferences)
    """
    # Step 1: Get user's saved preferences (if any)
    saved_prefs = preference_manager.get_preferences(user_id)
    defaults = preference_manager.get_system_defaults()
    
    # Check if saved preferences exist and differ from defaults
    has_saved = (
        saved_prefs.get("max_levels") is not None or 
        saved_prefs.get("max_children") is not None
    )
    used_saved_preferences = has_saved
    
    # Step 2: Start with saved preferences or system defaults
    if has_saved and saved_prefs.get("max_levels") is not None:
        max_levels = saved_prefs.get("max_levels")
    else:
        max_levels = defaults["max_levels"]
        used_saved_preferences = False
    
    if has_saved and saved_prefs.get("max_children") is not None:
        max_children = saved_prefs.get("max_children")
    else:
        max_children = defaults["max_children"]
        used_saved_preferences = False
    
    # Step 3: Apply preset if provided (preset values override saved/defaults)
    should_save = False
    if request_preferences and request_preferences.preset:
        preset = preference_manager.get_preset(request_preferences.preset)
        if preset:
            max_levels = preset["max_levels"]
            max_children = preset["max_children"]
            used_saved_preferences = False  # Preset overrides saved
        # Invalid preset name - keep current values
    
    # Step 4: Apply explicit overrides (explicit values override preset)
    if request_preferences:
        if request_preferences.max_levels is not None:
            max_levels = request_preferences.max_levels
            used_saved_preferences = False  # Explicit override
        if request_preferences.max_children is not None:
            max_children = request_preferences.max_children
            used_saved_preferences = False  # Explicit override
        if request_preferences.save is not None:
            should_save = request_preferences.save
    
    return max_levels, max_children, should_save, used_saved_preferences


async def run_orchestration_without_interactive(
    orchestrator: TreeOrchestrator
) -> tuple[Any, Dict[str, Any]]:
    """
    Run orchestration but skip interactive editing.
    
    This is a modified version of orchestrate() that skips interactive editing.
    """
    orchestrator.log_operation("start_orchestration", {
        "stock": orchestrator.stock,
        "investment_window": orchestrator.investment_window,
        "max_levels": orchestrator.max_levels,
        "max_children": orchestrator.max_children
    })
    
    root_node = await orchestrator.buil_first_node()
    
    # Generate specialized reports for 5 subtrees
    await orchestrator.generate_specialized_reports()
    
    await orchestrator.create_bfs(root_node)
    
    # Identify and answer missing crucial questions BEFORE backpropagation
    questions_by_level = orchestrator.collect_all_questions_by_level()
    missing_questions, llm_analysis = await orchestrator.identify_missing_questions(questions_by_level)
    missing_answers = await orchestrator.answer_missing_questions(missing_questions)
    
    orchestrator.missing_questions_analysis = {
        "missing_questions": missing_questions,
        "missing_answers": missing_answers,
        "llm_analysis": llm_analysis
    }
    
    await orchestrator.backpropagate_answers(root_node)
    
    final_decision = await orchestrator.generate_final_decision(root_node)
    
    orchestrator.log_operation("complete_orchestration", {
        "total_nodes": orchestrator.num_nodes,
        "llm_calls": orchestrator.llm_call_count,
        "final_position": final_decision.get('position') if final_decision else None
    })
    
    # Save comprehensive report
    await orchestrator.save_execution_report(filename="execution_report.json")
    
    # Skip interactive editing for API
    
    return root_node, final_decision


@app.post("/analyze", response_model=AnalyzeResponse)
async def analyze(request: AnalyzeRequest):
    """
    Analyze investment query using Tree + MAS system.
    
    Execution flow:
    1. Extract user_id
    2. Get preferences (saved -> preset -> explicit -> defaults)
    3. Initialize TreeOrchestrator with resolved preferences
    4. Invoke MAS fetch
    5. Build tree and execute nodes in parallel
    6. Aggregate bottom-up reasoning
    7. (Optional) Save updated preferences
    8. Return API response
    """
    try:
        # Step 1: Extract user_id
        user_id = request.user_id
        
        # Step 2: Resolve preferences
        max_levels, max_children, should_save, used_saved_preferences = resolve_preferences(
            user_id,
            request.preferences
        )
        
        # Step 3: Initialize TreeOrchestrator
        orchestrator = TreeOrchestrator(
            max_levels=max_levels,
            max_children=max_children
        )
        
        # Store user query for use in MAS fetch (minimal change - just set attribute)
        orchestrator.user_query = request.query
        
        # Step 4: Invoke MAS fetch (happens inside orchestration)
        # Step 5-6: Build tree and execute (happens in orchestration)
        root_node, final_decision = await run_orchestration_without_interactive(orchestrator)
        
        # Step 7: Save preferences if requested
        if should_save:
            preference_manager.save_preferences(user_id, max_levels, max_children)
        
        # Step 8: Create session and store orchestrator
        session_id = str(uuid.uuid4())
        session_storage[session_id] = orchestrator
        
        # Step 8.5: Save to persistent storage
        session_metadata = {
            "user_id": user_id,
            "query": request.query,
            "max_levels": max_levels,
            "max_children": max_children,
            "preset": request.preferences.preset if request.preferences else None
        }
        persistent_storage.save_session(session_id, session_metadata, {
            "execution_report": execution_report
        })
        
        # Step 9: Build response
        # Extract final answer from root node
        answer = root_node.answer or ""
        if final_decision and final_decision.get("detailed_analysis"):
            # Prefer final decision's detailed analysis if available
            answer = final_decision.get("detailed_analysis", answer)
        
        # Build execution report
        execution_report = {
            "tree_structure": orchestrator.get_tree_structure(),
            "all_nodes": orchestrator.export_all_nodes(),
            "stats": {
                "llm_calls": orchestrator.llm_call_count,
                "bm25_hits": orchestrator.BM25_hits,
                "internet_searches": orchestrator.internet_search_hits,
                "num_nodes": orchestrator.num_nodes
            },
            "final_decision": final_decision,
            "execution_log": orchestrator.execution_log
        }
        
        # Build metadata
        metadata = {
            "max_levels": max_levels,
            "max_children": max_children,
            "used_saved_preferences": used_saved_preferences,
            "source": "MAS + Tree"
        }
        
        return AnalyzeResponse(
            session_id=session_id,
            answer=answer,
            execution_report=execution_report,
            metadata=metadata
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")


@app.get("/sessions/{session_id}/nodes")
async def get_nodes(session_id: str):
    """Get all nodes for a session"""
    # Try in-memory storage first
    if session_id in session_storage:
        orchestrator = session_storage[session_id]
        nodes = []
        
        for node_id, node in sorted(orchestrator.nodes.items(), key=lambda x: int(x[0])):
            nodes.append({
                "id": node_id,
                "level": node.level,
                "question": node.question,
                "is_leaf": node.is_leaf,
                "has_answer": node.answer is not None,
                "answer_preview": (node.answer[:200] + "...") if node.answer and len(node.answer) > 200 else node.answer,
                "children": node.children,
                "parent_id": orchestrator.backward_adj.get(node_id)
            })
        
        return {
            "session_id": session_id,
            "nodes": nodes,
            "total_nodes": len(nodes)
        }
    
    # Try persistent storage
    stored_session = persistent_storage.load_session(session_id)
    if stored_session:
        execution_report = stored_session.get("execution_report", {})
        all_nodes = execution_report.get("all_nodes", {})
        
        # Convert stored nodes to the expected format
        nodes = []
        for node_id, node_data in sorted(all_nodes.items(), key=lambda x: int(x[0].replace("node_", ""))):
            node_id_clean = node_id.replace("node_", "")
            nodes.append({
                "id": node_id_clean,
                "level": node_data.get("level", 0),
                "question": node_data.get("question", ""),
                "is_leaf": node_data.get("is_leaf", False),
                "has_answer": node_data.get("answer") is not None,
                "answer_preview": (node_data.get("answer", "")[:200] + "...") if node_data.get("answer") and len(node_data.get("answer", "")) > 200 else node_data.get("answer", ""),
                "children": node_data.get("children", []),
                "parent_id": node_data.get("parent_id")
            })
        
        return {
            "session_id": session_id,
            "nodes": nodes,
            "total_nodes": len(nodes),
            "from_storage": True
        }
    
    raise HTTPException(status_code=404, detail="Session not found")


@app.get("/sessions/{session_id}/nodes/{node_id}")
async def get_node(session_id: str, node_id: str):
    """Get details of a specific node"""
    # Try in-memory storage first
    if session_id in session_storage:
        orchestrator = session_storage[session_id]
        
        if node_id not in orchestrator.nodes:
            raise HTTPException(status_code=404, detail="Node not found")
        
        node = orchestrator.nodes[node_id]
        
        return {
            "id": node_id,
            "level": node.level,
            "question": node.question,
            "answer": node.answer,
            "is_leaf": node.is_leaf,
            "children": node.children,
            "parent_id": orchestrator.backward_adj.get(node_id),
            "context": node.context[:500] + "..." if node.context and len(node.context) > 500 else node.context,
            "internet_research": node.internet_research,
            "mas_data_used": node.mas_data_used
        }
    
    # Try persistent storage
    stored_session = persistent_storage.load_session(session_id)
    if stored_session:
        execution_report = stored_session.get("execution_report", {})
        all_nodes = execution_report.get("all_nodes", {})
        node_key = f"node_{node_id}"
        
        if node_key not in all_nodes:
            raise HTTPException(status_code=404, detail="Node not found")
        
        node_data = all_nodes[node_key]
        
        return {
            "id": node_id,
            "level": node_data.get("level", 0),
            "question": node_data.get("question", ""),
            "answer": node_data.get("answer", ""),
            "is_leaf": node_data.get("is_leaf", False),
            "children": node_data.get("children", []),
            "parent_id": node_data.get("parent_id"),
            "context": (node_data.get("context", "")[:500] + "...") if node_data.get("context") and len(node_data.get("context", "")) > 500 else node_data.get("context", ""),
            "internet_research": node_data.get("internet_research", {}),
            "mas_data_used": node_data.get("mas_data_used", {}),
            "from_storage": True
        }
    
    raise HTTPException(status_code=404, detail="Session not found")


@app.post("/sessions/{session_id}/nodes/{node_id}/edit")
async def edit_node(session_id: str, node_id: str, request: EditNodeRequest):
    """Edit a node's question and regenerate its subtree"""
    if session_id not in session_storage:
        raise HTTPException(status_code=404, detail="Session not found")
    
    orchestrator = session_storage[session_id]
    
    if node_id not in orchestrator.nodes:
        raise HTTPException(status_code=404, detail="Node not found")
    
    try:
        # Perform the edit and regeneration
        await orchestrator.edit_node_and_regenerate(node_id, request.new_question)
        
        # Get updated node
        node = orchestrator.nodes[node_id]
        root_node = orchestrator.nodes.get("0")
        final_decision = None
        if root_node:
            final_decision = await orchestrator.generate_final_decision(root_node)
        
        # Build updated execution report
        execution_report = {
            "tree_structure": orchestrator.get_tree_structure(),
            "all_nodes": orchestrator.export_all_nodes(),
            "stats": {
                "llm_calls": orchestrator.llm_call_count,
                "bm25_hits": orchestrator.BM25_hits,
                "internet_searches": orchestrator.internet_search_hits,
                "num_nodes": orchestrator.num_nodes,
                "edit_count": orchestrator.edit_count
            },
            "final_decision": final_decision,
            "execution_log": orchestrator.execution_log
        }
        
        # Update persistent storage with edited report
        if session_id in session_storage:
            stored_session = persistent_storage.load_session(session_id)
            if stored_session:
                session_metadata = stored_session.get("session_metadata", {})
                persistent_storage.save_session(session_id, session_metadata, {
                    "execution_report": execution_report
                })
        
        return {
            "success": True,
            "message": f"Node {node_id} edited and subtree regenerated",
            "edit_count": orchestrator.edit_count,
            "updated_node": {
                "id": node_id,
                "question": node.question,
                "answer": node.answer,
                "children": node.children
            },
            "execution_report": execution_report
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to edit node: {str(e)}")


@app.get("/sessions/{session_id}/report")
async def get_report(session_id: str):
    """Get the full execution report for a session"""
    # Try in-memory storage first
    if session_id in session_storage:
        orchestrator = session_storage[session_id]
        root_node = orchestrator.nodes.get("0")
        final_decision = None
        if root_node:
            final_decision = await orchestrator.generate_final_decision(root_node)
        
        execution_report = {
            "tree_structure": orchestrator.get_tree_structure(),
            "all_nodes": orchestrator.export_all_nodes(),
            "stats": {
                "llm_calls": orchestrator.llm_call_count,
                "bm25_hits": orchestrator.BM25_hits,
                "internet_searches": orchestrator.internet_search_hits,
                "num_nodes": orchestrator.num_nodes,
                "edit_count": orchestrator.edit_count
            },
            "final_decision": final_decision,
            "execution_log": orchestrator.execution_log
        }
        
        return {
            "session_id": session_id,
            "execution_report": execution_report
        }
    
    # Try persistent storage
    stored_session = persistent_storage.load_session(session_id)
    if stored_session:
        return {
            "session_id": session_id,
            "execution_report": stored_session.get("execution_report", {}),
            "created_at": stored_session.get("created_at"),
            "from_storage": True
        }
    
    raise HTTPException(status_code=404, detail="Session not found")


@app.get("/sessions")
async def list_sessions(user_id: Optional[str] = None, limit: int = 50):
    """List all stored sessions"""
    sessions = persistent_storage.list_sessions(user_id=user_id, limit=limit)
    return {
        "sessions": sessions,
        "total": len(sessions),
        "total_stored": persistent_storage.get_session_count()
    }


@app.get("/sessions/{session_id}/load")
async def load_session(session_id: str):
    """Load a stored session back into memory for editing"""
    stored_session = persistent_storage.load_session(session_id)
    if not stored_session:
        raise HTTPException(status_code=404, detail="Session not found in storage")
    
    # Return the stored data
    return {
        "session_id": session_id,
        "session_data": stored_session,
        "message": "Session loaded from storage. Use session_id for node operations."
    }


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "Tree + MAS Analysis API",
        "version": "1.0.0",
        "endpoints": {
            "POST /analyze": "Analyze investment query",
            "GET /sessions": "List all stored sessions",
            "GET /sessions/{session_id}/nodes": "Get all nodes for a session",
            "GET /sessions/{session_id}/nodes/{node_id}": "Get a specific node",
            "POST /sessions/{session_id}/nodes/{node_id}/edit": "Edit a node and regenerate subtree",
            "GET /sessions/{session_id}/report": "Get full execution report",
            "GET /sessions/{session_id}/load": "Load stored session from disk"
        },
        "storage": {
            "total_sessions": persistent_storage.get_session_count(),
            "storage_directory": str(persistent_storage.storage_dir)
        }
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
