#!/usr/bin/env python3
"""
Unified Router Data Collector - Entry Point
Consolidates all router data collection into single framework

Usage:
    python3 router_collector.py
"""

import sys
import os

# Add router_collector module to path
sys.path.insert(0, os.path.dirname(__file__))

from router_collector.collector import RouterCollector


def main():
    """Main entry point for Telegraf exec input"""
    try:
        # Initialize collector
        collector = RouterCollector(
            host='192.168.1.2',
            username='root',
            collectors=['dhcp'],  # Phase 1: DHCP only
            key_file=None  # Uses SSH keys from ~/.ssh/
        )

        # Run collection and output metrics
        collector.run()

    except KeyboardInterrupt:
        print("\n# Interrupted by user", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"# FATAL ERROR: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
