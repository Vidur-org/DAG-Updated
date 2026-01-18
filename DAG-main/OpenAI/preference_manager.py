"""
PreferenceManager: Manages user preferences for tree analysis parameters.

Handles:
- User-specific preferences (max_levels, max_children)
- Preset configurations (balanced, fast, thorough)
- System defaults
- JSON-backed persistence
"""

import json
from pathlib import Path
from typing import Dict, Optional
from config import CONFIG


class PreferenceManager:
    """Manages user preferences for analysis parameters"""
    
    # Preset configurations - Optimized for speed
    PRESETS = {
        "fast": {
            "max_levels": 2,  # Reduced from 3 to 2 for 2-minute inference
            "max_children": 1
        },
        "balanced": {
            "max_levels": 3,  # Reduced from 4 to 3
            "max_children": 2
        },
        "thorough": {
            "max_levels": 4,  # Reduced from 5 to 4
            "max_children": 2  # Reduced from 3 to 2
        }
    }
    
    def __init__(self, preferences_file: str = "user_preferences.json"):
        """
        Initialize PreferenceManager
        
        Args:
            preferences_file: Path to JSON file storing user preferences
        """
        self.preferences_file = Path(preferences_file)
        self._ensure_preferences_file()
    
    def _ensure_preferences_file(self):
        """Create preferences file if it doesn't exist"""
        if not self.preferences_file.exists():
            with open(self.preferences_file, 'w') as f:
                json.dump({}, f)
    
    def _load_preferences(self) -> Dict:
        """Load all preferences from JSON file"""
        try:
            with open(self.preferences_file, 'r') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return {}
    
    def _save_preferences(self, preferences: Dict):
        """Save preferences to JSON file"""
        with open(self.preferences_file, 'w') as f:
            json.dump(preferences, f, indent=2)
    
    def get_preferences(self, user_id: str) -> Dict[str, int]:
        """
        Get preferences for a specific user
        
        Args:
            user_id: User identifier
            
        Returns:
            Dict with 'max_levels' and 'max_children' keys
        """
        all_prefs = self._load_preferences()
        user_prefs = all_prefs.get(user_id, {})
        
        # Return user preferences if they exist, otherwise return system defaults
        if user_prefs:
            return {
                "max_levels": user_prefs.get("max_levels"),
                "max_children": user_prefs.get("max_children")
            }
        else:
            return self.get_system_defaults()
    
    def save_preferences(self, user_id: str, max_levels: int, max_children: int):
        """
        Save preferences for a specific user
        
        Args:
            user_id: User identifier
            max_levels: Maximum tree depth
            max_children: Maximum children per node
        """
        all_prefs = self._load_preferences()
        all_prefs[user_id] = {
            "max_levels": max_levels,
            "max_children": max_children
        }
        self._save_preferences(all_prefs)
    
    def get_preset(self, preset_name: str) -> Optional[Dict[str, int]]:
        """
        Get preset configuration by name
        
        Args:
            preset_name: Name of preset ('fast', 'balanced', 'thorough')
            
        Returns:
            Dict with 'max_levels' and 'max_children', or None if preset doesn't exist
        """
        return self.PRESETS.get(preset_name.lower())
    
    @staticmethod
    def get_system_defaults() -> Dict[str, int]:
        """
        Get system default preferences from CONFIG
        
        Returns:
            Dict with 'max_levels' and 'max_children' from CONFIG
        """
        return {
            "max_levels": CONFIG.get('MAX_LEVELS', 5),
            "max_children": CONFIG.get('MAX_CHILDREN', 1)
        }
