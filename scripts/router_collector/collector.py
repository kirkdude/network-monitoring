#!/usr/bin/env python3
"""
Router Collector Orchestrator
Coordinates multiple collectors and manages SSH connection
"""

import sys
from typing import List
from .connection import RouterConnection
from .utils.state import StateManager
from .collectors.dhcp import DHCPCollector


class RouterCollector:
    """Main orchestrator for router data collection"""

    def __init__(self, host: str, username: str = 'root',
                 collectors: List[str] = None, key_file: str = None):
        """
        Initialize router collector

        Args:
            host: Router IP address
            username: SSH username
            collectors: List of collector names to run (e.g., ['dhcp', 'dns'])
            key_file: Path to SSH private key
        """
        self.host = host
        self.username = username
        self.key_file = key_file
        self.collector_names = collectors or ['dhcp']

        # Initialize connection and state manager
        self.connection = RouterConnection(host, username, key_file)
        self.state_manager = StateManager()

        # Initialize collectors
        self.collectors = []
        self._initialize_collectors()

    def _initialize_collectors(self):
        """Initialize requested collectors"""
        collector_map = {
            'dhcp': DHCPCollector
        }

        for name in self.collector_names:
            if name not in collector_map:
                print(f"WARNING: Unknown collector '{name}', skipping", file=sys.stderr)
                continue

            collector_class = collector_map[name]
            collector = collector_class(self.connection, self.state_manager)
            self.collectors.append(collector)
            print(f"Initialized collector: {name}", file=sys.stderr)

    def run(self):
        """Run all collectors and output metrics"""
        try:
            # Connect to router
            print(f"Connecting to router at {self.host}...", file=sys.stderr)
            self.connection.connect()

            # Run all collectors
            all_metrics = []
            for collector in self.collectors:
                try:
                    metrics = collector.run()
                    all_metrics.extend(metrics)
                except Exception as e:
                    print(f"ERROR: Collector {collector.name} failed: {e}", file=sys.stderr)
                    # Continue with other collectors

            # Output all metrics to stdout (for Telegraf)
            if all_metrics:
                for metric in all_metrics:
                    print(metric)
                print(f"# Output {len(all_metrics)} metrics total", file=sys.stderr)
            else:
                print("# WARNING: No metrics collected", file=sys.stderr)

        except Exception as e:
            print(f"FATAL ERROR: {e}", file=sys.stderr)
            sys.exit(1)
        finally:
            # Always disconnect
            self.connection.disconnect()
