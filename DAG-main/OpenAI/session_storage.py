"""
Persistent session storage for API server.

Stores sessions and reports to disk so they persist across server restarts.
"""

import json
import os
from pathlib import Path
from typing import Dict, Optional, List
from datetime import datetime
import uuid


class SessionStorage:
    """Manages persistent storage of sessions and reports"""
    
    def __init__(self, storage_dir: str = "sessions"):
        """
        Initialize session storage
        
        Args:
            storage_dir: Directory to store session files
        """
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(exist_ok=True)
        self.sessions_file = self.storage_dir / "sessions_index.json"
        self.sessions_index: Dict[str, Dict] = self._load_index()
    
    def _load_index(self) -> Dict[str, Dict]:
        """Load sessions index from disk"""
        if self.sessions_file.exists():
            try:
                with open(self.sessions_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError):
                return {}
        return {}
    
    def _save_index(self):
        """Save sessions index to disk"""
        try:
            with open(self.sessions_file, 'w', encoding='utf-8') as f:
                json.dump(self.sessions_index, f, indent=2, ensure_ascii=False)
        except IOError as e:
            print(f"Warning: Failed to save sessions index: {e}")
    
    def save_session(self, session_id: str, session_data: Dict, report_data: Dict):
        """
        Save session and report data to disk
        
        Args:
            session_id: Session identifier
            session_data: Session metadata
            report_data: Full execution report
        """
        session_file = self.storage_dir / f"{session_id}.json"
        
        # Prepare data to save
        data_to_save = {
            "session_id": session_id,
            "created_at": datetime.now().isoformat(),
            "session_metadata": session_data,
            "execution_report": report_data
        }
        
        # Save to file
        try:
            with open(session_file, 'w', encoding='utf-8') as f:
                json.dump(data_to_save, f, indent=2, ensure_ascii=False)
            
            # Update index
            self.sessions_index[session_id] = {
                "session_id": session_id,
                "created_at": data_to_save["created_at"],
                "query": session_data.get("query", ""),
                "user_id": session_data.get("user_id", ""),
                "stock": report_data.get("execution_report", {}).get("stats", {}).get("stock", ""),
                "num_nodes": report_data.get("execution_report", {}).get("stats", {}).get("num_nodes", 0),
                "final_position": report_data.get("execution_report", {}).get("final_decision", {}).get("position", ""),
                "file_path": str(session_file)
            }
            self._save_index()
            
        except IOError as e:
            print(f"Warning: Failed to save session {session_id}: {e}")
    
    def load_session(self, session_id: str) -> Optional[Dict]:
        """
        Load session and report data from disk
        
        Args:
            session_id: Session identifier
            
        Returns:
            Session data dict or None if not found
        """
        session_file = self.storage_dir / f"{session_id}.json"
        
        if not session_file.exists():
            return None
        
        try:
            with open(session_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            print(f"Warning: Failed to load session {session_id}: {e}")
            return None
    
    def list_sessions(self, user_id: Optional[str] = None, limit: int = 100) -> List[Dict]:
        """
        List all stored sessions
        
        Args:
            user_id: Optional filter by user ID
            limit: Maximum number of sessions to return
            
        Returns:
            List of session metadata
        """
        sessions = list(self.sessions_index.values())
        
        # Filter by user_id if provided
        if user_id:
            sessions = [s for s in sessions if s.get("user_id") == user_id]
        
        # Sort by created_at (newest first)
        sessions.sort(key=lambda x: x.get("created_at", ""), reverse=True)
        
        # Limit results
        return sessions[:limit]
    
    def delete_session(self, session_id: str) -> bool:
        """
        Delete a session from storage
        
        Args:
            session_id: Session identifier
            
        Returns:
            True if deleted, False if not found
        """
        session_file = self.storage_dir / f"{session_id}.json"
        
        if session_file.exists():
            try:
                session_file.unlink()
                if session_id in self.sessions_index:
                    del self.sessions_index[session_id]
                self._save_index()
                return True
            except IOError:
                return False
        
        return False
    
    def get_session_count(self) -> int:
        """Get total number of stored sessions"""
        return len(self.sessions_index)
