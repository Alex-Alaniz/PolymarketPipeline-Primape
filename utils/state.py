"""
State management utilities for the Polymarket pipeline.
"""
import os
import json
import logging
from datetime import datetime
from typing import Dict, Any, Optional

from config import STATE_FILE

logger = logging.getLogger("state_manager")

class StateManager:
    """Manages the pipeline state."""
    
    def __init__(self):
        """Initialize the state manager."""
        self.state_file = STATE_FILE
        self.state = self._load_state()
        
        # Ensure state file directory exists
        os.makedirs(os.path.dirname(self.state_file), exist_ok=True)
    
    def _load_state(self) -> Dict[str, Any]:
        """
        Load the state from the state file.
        
        Returns:
            Dict[str, Any]: The state
        """
        if os.path.exists(self.state_file):
            try:
                with open(self.state_file, 'r') as f:
                    state = json.load(f)
                logger.info(f"Loaded state from {self.state_file}")
                return state
            except json.JSONDecodeError:
                logger.error(f"Error decoding state file {self.state_file}")
                return self._initialize_state()
            except Exception as e:
                logger.error(f"Error loading state: {str(e)}")
                return self._initialize_state()
        else:
            logger.info(f"State file {self.state_file} does not exist, initializing new state")
            return self._initialize_state()
    
    def _save_state(self) -> bool:
        """
        Save the state to the state file.
        
        Returns:
            bool: Success status
        """
        try:
            with open(self.state_file, 'w') as f:
                json.dump(self.state, f, indent=2)
            logger.info(f"Saved state to {self.state_file}")
            return True
        except Exception as e:
            logger.error(f"Error saving state: {str(e)}")
            return False
    
    def _initialize_state(self) -> Dict[str, Any]:
        """
        Initialize a new state.
        
        Returns:
            Dict[str, Any]: The new state
        """
        return {
            "pipeline": {
                "last_run": None,
                "status": "idle",
                "markets_processed": 0,
                "markets_approved": 0,
                "markets_rejected": 0,
                "markets_deployed": 0
            },
            "markets": {}
        }
    
    def get_pipeline_state(self) -> Dict[str, Any]:
        """
        Get the pipeline state.
        
        Returns:
            Dict[str, Any]: The pipeline state
        """
        return self.state.get("pipeline", {})
    
    def update_pipeline_state(self, **kwargs) -> bool:
        """
        Update the pipeline state.
        
        Args:
            **kwargs: The fields to update
            
        Returns:
            bool: Success status
        """
        pipeline_state = self.state.get("pipeline", {})
        for key, value in kwargs.items():
            pipeline_state[key] = value
        self.state["pipeline"] = pipeline_state
        return self._save_state()
    
    def get_market_state(self, market_id: str) -> Optional[Dict[str, Any]]:
        """
        Get the state of a market.
        
        Args:
            market_id (str): The market ID
            
        Returns:
            Optional[Dict[str, Any]]: The market state, or None if not found
        """
        return self.state.get("markets", {}).get(market_id)
    
    def update_market_state(self, market_id: str, **kwargs) -> bool:
        """
        Update the state of a market.
        
        Args:
            market_id (str): The market ID
            **kwargs: The fields to update
            
        Returns:
            bool: Success status
        """
        market_state = self.state.get("markets", {}).get(market_id, {})
        for key, value in kwargs.items():
            market_state[key] = value
        if "markets" not in self.state:
            self.state["markets"] = {}
        self.state["markets"][market_id] = market_state
        return self._save_state()
    
    def get_all_markets(self) -> Dict[str, Dict[str, Any]]:
        """
        Get the state of all markets.
        
        Returns:
            Dict[str, Dict[str, Any]]: A dictionary of market IDs to market states
        """
        return self.state.get("markets", {})