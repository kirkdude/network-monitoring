#!/usr/bin/env python3
"""
Base Collector Class
Defines interface for all router data collectors
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Any
import sys


class BaseCollector(ABC):
    """Base class for all router data collectors"""

    def __init__(self, connection, state_manager=None):
        """
        Initialize collector

        Args:
            connection: RouterConnection instance
            state_manager: Optional state manager for persistent data
        """
        self.connection = connection
        self.state = state_manager
        self.name = self.__class__.__name__

    @abstractmethod
    def collect(self) -> Dict[str, Any]:
        """
        Collect data from router

        Returns:
            Dictionary containing collected data

        Raises:
            Exception: If collection fails
        """
        pass

    @abstractmethod
    def format_metrics(self, data: Dict[str, Any]) -> List[str]:
        """
        Format collected data as InfluxDB line protocol

        Args:
            data: Collected data dictionary

        Returns:
            List of InfluxDB line protocol strings

        Raises:
            Exception: If formatting fails
        """
        pass

    def run(self) -> List[str]:
        """
        Run full collection cycle

        Returns:
            List of InfluxDB line protocol strings
        """
        try:
            print(f"[{self.name}] Starting collection...", file=sys.stderr)
            data = self.collect()

            print(f"[{self.name}] Formatting metrics...", file=sys.stderr)
            metrics = self.format_metrics(data)

            print(f"[{self.name}] Collected {len(metrics)} metrics", file=sys.stderr)
            return metrics

        except Exception as e:
            print(f"[{self.name}] ERROR: Collection failed: {e}", file=sys.stderr)
            raise

    def log(self, message: str):
        """Helper to log messages"""
        print(f"[{self.name}] {message}", file=sys.stderr)

    def log_error(self, message: str):
        """Helper to log errors"""
        print(f"[{self.name}] ERROR: {message}", file=sys.stderr)
