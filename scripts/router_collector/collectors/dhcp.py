#!/usr/bin/env python3
"""
DHCP Collector
Collects DHCP lease data from OpenWrt router
"""

import re
import time
from typing import Dict, List, Any, Set, Tuple
from .base import BaseCollector
from ..formatters.influxdb import InfluxDBFormatter


class DHCPCollector(BaseCollector):
    """Collects DHCP lease and pool information"""

    def __init__(self, connection, state_manager=None, device_name='glmt2500a'):
        super().__init__(connection, state_manager)
        self.device_name = device_name

    def collect(self) -> Dict[str, Any]:
        """
        Collect DHCP data from router

        Returns:
            Dictionary with lease data, pool config, and static reservations
        """
        # Batch all commands in single SSH session
        commands = [
            'cat /tmp/dhcp.leases',
            'uci show dhcp.lan.start',
            'uci show dhcp.lan.limit',
            "uci show dhcp | grep 'dhcp.@host' | grep '.mac='"
        ]

        self.log("Executing batch commands...")
        results = self.connection.execute_batch(commands)

        # Parse results
        leases = self._parse_leases(results.get('cat /tmp/dhcp.leases', ''))
        pool_start, pool_limit = self._parse_pool_config(
            results.get('uci show dhcp.lan.start', ''),
            results.get('uci show dhcp.lan.limit', '')
        )
        static_macs = self._parse_static_reservations(
            results.get("uci show dhcp | grep 'dhcp.@host' | grep '.mac='", '')
        )

        self.log(f"Found {len(leases)} active leases, pool size: {pool_limit}")

        return {
            'leases': leases,
            'pool_start': pool_start,
            'pool_limit': pool_limit,
            'static_macs': static_macs
        }

    def _parse_leases(self, output: str) -> List[Dict[str, Any]]:
        """
        Parse DHCP leases file

        Format: timestamp MAC IP hostname client_id
        Example: 1766215920 a8:23:fe:2c:58:c5 192.168.1.70 LGwebOSTV *
        """
        leases = []
        if not output:
            return leases

        for line in output.strip().split('\n'):
            if not line or line.startswith('#'):
                continue

            parts = line.split()
            if len(parts) < 4:
                self.log(f"WARNING: Malformed lease line: {line}")
                continue

            try:
                lease = {
                    'expires_timestamp': int(parts[0]),
                    'mac': parts[1].lower(),
                    'ip': parts[2],
                    'hostname': parts[3] if parts[3] != '*' else 'unknown',
                    'client_id': parts[4] if len(parts) > 4 else None
                }
                leases.append(lease)
            except (ValueError, IndexError) as e:
                self.log(f"WARNING: Error parsing lease line '{line}': {e}")
                continue

        return leases

    def _parse_pool_config(self, start_output: str, limit_output: str) -> Tuple[int, int]:
        """
        Parse UCI DHCP pool configuration

        Example:
            dhcp.lan.start='51'
            dhcp.lan.limit='204'
        """
        pool_start = 51  # Default
        pool_limit = 150  # Default

        # Parse start
        match = re.search(r"start='?(\d+)'?", start_output)
        if match:
            pool_start = int(match.group(1))

        # Parse limit
        match = re.search(r"limit='?(\d+)'?", limit_output)
        if match:
            pool_limit = int(match.group(1))

        return pool_start, pool_limit

    def _parse_static_reservations(self, output: str) -> Set[str]:
        """
        Parse static DHCP reservations

        Example:
            dhcp.@host[0].mac='a8:23:fe:2c:58:c5'
            dhcp.@host[1].mac='80:f5:05:xx:xx:xx'
        """
        static_macs = set()
        if not output:
            return static_macs

        for line in output.strip().split('\n'):
            match = re.search(r"mac='?([0-9a-fA-F:]+)'?", line)
            if match:
                static_macs.add(match.group(1).lower())

        return static_macs

    def _calculate_pool_metrics(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate pool-level metrics"""
        leases = data['leases']
        pool_limit = data['pool_limit']
        static_macs = data['static_macs']

        active_leases = len(leases)
        available_leases = pool_limit - active_leases
        utilization_percent = (active_leases / pool_limit * 100) if pool_limit > 0 else 0

        # Count static vs dynamic
        static_count = sum(1 for lease in leases if lease['mac'] in static_macs)
        dynamic_count = active_leases - static_count

        # Calculate lease rate (new leases per hour)
        lease_rate = self._calculate_lease_rate(active_leases)

        return {
            'total_leases': pool_limit,
            'active_leases': active_leases,
            'available_leases': available_leases,
            'utilization_percent': round(utilization_percent, 2),
            'static_leases': static_count,
            'dynamic_leases': dynamic_count,
            'lease_rate_per_hour': lease_rate
        }

    def _calculate_lease_rate(self, current_active: int) -> float:
        """
        Calculate lease allocation rate (new leases per hour)

        Uses state to track changes over time
        """
        if not self.state:
            return 0.0

        # Load previous state
        prev_state = self.state.load_state('dhcp') or {}
        prev_active = prev_state.get('active_leases', current_active)
        prev_timestamp = prev_state.get('timestamp', time.time())

        # Calculate rate
        current_timestamp = time.time()
        time_delta_hours = (current_timestamp - prev_timestamp) / 3600.0

        if time_delta_hours > 0:
            lease_delta = current_active - prev_active
            rate = lease_delta / time_delta_hours
        else:
            rate = 0.0

        # Save current state
        self.state.save_state('dhcp', {
            'active_leases': current_active,
            'timestamp': current_timestamp
        })

        return round(rate, 2)

    def format_metrics(self, data: Dict[str, Any]) -> List[str]:
        """Format collected data as InfluxDB line protocol"""
        metrics = []

        # Calculate pool metrics
        pool_metrics = self._calculate_pool_metrics(data)

        # Format pool-level measurement
        pool_line = InfluxDBFormatter.format_line(
            measurement='dhcp_pool',
            tags={
                'device': self.device_name,
                'pool_name': 'lan'
            },
            fields=pool_metrics
        )
        metrics.append(pool_line)

        # Format individual lease measurements
        current_time = int(time.time())
        for lease in data['leases']:
            remaining_seconds = lease['expires_timestamp'] - current_time
            lease_type = 'static' if lease['mac'] in data['static_macs'] else 'dynamic'

            lease_line = InfluxDBFormatter.format_line(
                measurement='dhcp_lease',
                tags={
                    'device': self.device_name,
                    'mac': lease['mac'],
                    'ip': lease['ip'],
                    'lease_type': lease_type,
                    'hostname': lease['hostname'],
                    'device_name': lease['hostname']  # Can be enriched later
                },
                fields={
                    'expires_timestamp': lease['expires_timestamp'],
                    'remaining_seconds': remaining_seconds
                }
            )
            metrics.append(lease_line)

        return metrics
