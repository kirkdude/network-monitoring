#!/usr/bin/env python3
"""
Router Connection Manager
Provides persistent SSH connection pooling using Netmiko
"""

import sys
import time
from typing import Dict, List, Optional
from netmiko import ConnectHandler
from netmiko.exceptions import NetmikoTimeoutException, NetmikoAuthenticationException


class RouterConnection:
    """Manages persistent SSH connection to router using Netmiko"""

    def __init__(self, host: str, username: str = 'root', key_file: Optional[str] = None):
        """
        Initialize router connection

        Args:
            host: Router IP address
            username: SSH username
            key_file: Path to SSH private key (optional)
        """
        self.host = host
        self.username = username
        self.key_file = key_file

        # Build device config
        self.device_config = {
            'device_type': 'linux',  # OpenWrt is Linux-based
            'host': host,
            'username': username,
            'timeout': 10,
            'session_log': '/tmp/router-ssh-session.log',
            'fast_cli': False,  # Disable fast CLI for stability
        }

        # Configure SSH key authentication
        if key_file:
            self.device_config['use_keys'] = True
            self.device_config['key_file'] = key_file
        else:
            # Enable key-based auth and let paramiko search ~/.ssh/
            self.device_config['use_keys'] = True
            # Explicitly set common key paths
            import os
            ssh_dir = os.path.expanduser('~/.ssh')
            for key_name in ['id_rsa', 'id_ed25519', 'id_ecdsa', 'id_dsa']:
                key_path = os.path.join(ssh_dir, key_name)
                if os.path.exists(key_path):
                    self.device_config['key_file'] = key_path
                    break

        self.connection = None
        self._last_used = None

    def connect(self):
        """Establish persistent SSH connection"""
        if self.connection and self.is_alive():
            return  # Already connected

        try:
            print(f"Connecting to router at {self.host}...", file=sys.stderr)
            self.connection = ConnectHandler(**self.device_config)
            self._last_used = time.time()
            print(f"Connected successfully to {self.host}", file=sys.stderr)
        except NetmikoTimeoutException:
            print(f"ERROR: SSH timeout connecting to {self.host}", file=sys.stderr)
            raise
        except NetmikoAuthenticationException:
            print(f"ERROR: SSH authentication failed for {self.host}", file=sys.stderr)
            raise
        except Exception as e:
            print(f"ERROR: Failed to connect to {self.host}: {e}", file=sys.stderr)
            raise

    def execute_command(self, command: str) -> str:
        """
        Execute single command on router

        Args:
            command: Shell command to execute

        Returns:
            Command output as string
        """
        if not self.connection or not self.is_alive():
            self.connect()

        try:
            output = self.connection.send_command(command, read_timeout=30)
            self._last_used = time.time()
            return output
        except Exception as e:
            print(f"ERROR: Command failed '{command}': {e}", file=sys.stderr)
            # Try to reconnect and retry once
            try:
                self.disconnect()
                self.connect()
                output = self.connection.send_command(command, read_timeout=30)
                self._last_used = time.time()
                return output
            except Exception as retry_error:
                print(f"ERROR: Retry failed for '{command}': {retry_error}", file=sys.stderr)
                raise

    def execute_batch(self, commands: List[str]) -> Dict[str, str]:
        """
        Execute multiple commands in single SSH session

        Args:
            commands: List of shell commands

        Returns:
            Dictionary mapping command -> output
        """
        if not self.connection or not self.is_alive():
            self.connect()

        results = {}
        for cmd in commands:
            try:
                output = self.connection.send_command(cmd, read_timeout=30)
                results[cmd] = output
                self._last_used = time.time()
            except Exception as e:
                print(f"ERROR: Batch command failed '{cmd}': {e}", file=sys.stderr)
                results[cmd] = None

        return results

    def is_alive(self) -> bool:
        """Check if connection is still active"""
        if not self.connection:
            return False

        try:
            return self.connection.is_alive()
        except Exception:
            return False

    def disconnect(self):
        """Close SSH connection"""
        if self.connection:
            try:
                self.connection.disconnect()
                print(f"Disconnected from {self.host}", file=sys.stderr)
            except Exception as e:
                print(f"WARNING: Error disconnecting from {self.host}: {e}", file=sys.stderr)
            finally:
                self.connection = None

    def __enter__(self):
        """Context manager entry"""
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.disconnect()
        return False
