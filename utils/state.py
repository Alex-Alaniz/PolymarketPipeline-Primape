"""
State management for the Polymarket pipeline.
"""
import os
import json
from datetime import datetime
from typing import Dict, List, Any, Optional

from config import STATE_FILE, DATA_DIR

class StateManager:
    """Manages the state of the pipeline."""
    
    def __init__(self):
        """Initialize the state manager."""
        # Create data directory if it doesn't exist
        os.makedirs(DATA_DIR, exist_ok=True)
        
        # Load state from file or initialize if not exists
        self.state = self._load_state()
    
    def _load_state(self) -> Dict[str, Any]:
        """Load the state from the state file."""
        if os.path.exists(STATE_FILE):
            try:
                with open(STATE_FILE, 'r') as f:
                    return json.load(f)
            except json.JSONDecodeError:
                print("Warning: Error reading state file, initializing fresh state")
                return self._initialize_state()
        return self._initialize_state()
    
    def _initialize_state(self) -> Dict[str, Any]:
        """Initialize a fresh state."""
        return {
            "last_run": None,
            "markets": {}
        }
    
    def save_state(self):
        """Save the state to the state file."""
        with open(STATE_FILE, 'w') as f:
            json.dump(self.state, f, indent=2)
    
    def get_market_state(self, market_id: str) -> Optional[Dict[str, Any]]:
        """Get the state of a market."""
        return self.state["markets"].get(market_id)
    
    def set_market_state(self, market_id: str, state_data: Dict[str, Any]):
        """Set the state of a market."""
        self.state["markets"][market_id] = state_data
        self.save_state()
    
    def update_market_state(self, market_id: str, **kwargs):
        """Update the state of a market."""
        if market_id not in self.state["markets"]:
            self.state["markets"][market_id] = {}
        
        for key, value in kwargs.items():
            self.state["markets"][market_id][key] = value
        
        self.save_state()
    
    def get_all_markets(self) -> Dict[str, Dict[str, Any]]:
        """Get all markets."""
        return self.state["markets"]
    
    def get_markets_by_status(self, status: str) -> List[str]:
        """Get all markets with the specified status."""
        return [
            market_id for market_id, market_data in self.state["markets"].items()
            if market_data.get("status") == status
        ]
    
    def set_last_run(self, timestamp: str):
        """Set the timestamp of the last run."""
        self.state["last_run"] = timestamp
        self.save_state()
    
    def get_last_run(self) -> Optional[str]:
        """Get the timestamp of the last run."""
        return self.state.get("last_run")