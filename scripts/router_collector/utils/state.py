#!/usr/bin/env python3
"""
State Manager
Manages persistent state for collectors across runs
"""

import json
import os
from typing import Any, Dict, Optional
import sys


class StateManager:
    """Manages persistent state in JSON files"""

    def __init__(self, state_dir: str = "/tmp"):
        """
        Initialize state manager

        Args:
            state_dir: Directory to store state files
        """
        self.state_dir = state_dir
        os.makedirs(state_dir, exist_ok=True)

    def get_state_file(self, collector_name: str) -> str:
        """Get path to state file for collector"""
        return os.path.join(self.state_dir, f"{collector_name}-state.json")

    def load_state(self, collector_name: str) -> Optional[Dict[str, Any]]:
        """
        Load state for a collector

        Args:
            collector_name: Name of the collector

        Returns:
            State dictionary or None if no state exists
        """
        state_file = self.get_state_file(collector_name)

        if not os.path.exists(state_file):
            return None

        try:
            with open(state_file, 'r') as f:
                state = json.load(f)
            return state
        except Exception as e:
            print(f"WARNING: Failed to load state from {state_file}: {e}", file=sys.stderr)
            return None

    def save_state(self, collector_name: str, state: Dict[str, Any]):
        """
        Save state for a collector

        Args:
            collector_name: Name of the collector
            state: State dictionary to save
        """
        state_file = self.get_state_file(collector_name)

        try:
            with open(state_file, 'w') as f:
                json.dump(state, f, indent=2)
        except Exception as e:
            print(f"WARNING: Failed to save state to {state_file}: {e}", file=sys.stderr)

    def get(self, collector_name: str, key: str, default: Any = None) -> Any:
        """
        Get a specific value from collector state

        Args:
            collector_name: Name of the collector
            key: State key to retrieve
            default: Default value if key doesn't exist

        Returns:
            Value or default
        """
        state = self.load_state(collector_name)
        if state is None:
            return default
        return state.get(key, default)

    def set(self, collector_name: str, key: str, value: Any):
        """
        Set a specific value in collector state

        Args:
            collector_name: Name of the collector
            key: State key to set
            value: Value to store
        """
        state = self.load_state(collector_name) or {}
        state[key] = value
        self.save_state(collector_name, state)
