#!/usr/bin/env python3
"""
Opportunistic CDN Ping Orchestrator for Network Monitoring

This script runs as a Telegraf execd input plugin and intelligently pings CDN
hosts only when streaming devices are actively streaming (>1 Mbps bandwidth).

Behavior:
- Queries InfluxDB every 30 seconds for bandwidth data
- Detects streaming: LG TV, Roku TV, or Apple TV with >1 MB in last 60s
- If streaming detected: pings Netflix, YouTube, Amazon, Cloudflare (5 pings each)
- If no streaming: skips pings (silent, no network traffic)
- Outputs InfluxDB line protocol to stdout for Telegraf ingestion

Author: Network Monitoring Stack
Date: 2026-01-01
"""

import ipaddress
import os
import shutil
import sys
import time
import subprocess  # nosec B404
import re
from datetime import datetime

try:
    from influxdb_client import InfluxDBClient
except ImportError:
    sys.stderr.write(
        "ERROR: influxdb-client not installed. Run: pip3 install influxdb-client\n"
    )
    sys.exit(1)

# Configuration from environment variables
INFLUXDB_URL = os.getenv("INFLUXDB_URL", "http://influxdb:8086")
INFLUXDB_TOKEN = os.getenv("INFLUXDB_TOKEN")
INFLUXDB_ORG = os.getenv("INFLUXDB_ORG", "home")
INFLUXDB_BUCKET = os.getenv("INFLUXDB_BUCKET", "network")

# Streaming device IPs (LG TV, Roku TV, Apple TV)
# Validate IP addresses to prevent Flux query injection
STREAMING_DEVICES_STR = os.getenv(
    "STREAMING_DEVICES", "192.168.1.70,192.168.1.95,192.168.1.109"
)
STREAMING_DEVICES = []
for ip_str in STREAMING_DEVICES_STR.split(","):
    ip = ip_str.strip()
    if not ip:
        continue
    try:
        ipaddress.ip_address(ip)
        STREAMING_DEVICES.append(ip)
    except ValueError:
        sys.stderr.write(
            f"WARNING: Invalid IP address '{ip}' in STREAMING_DEVICES ignored.\n"
        )

# CDN hosts to ping
CDN_HOSTS = [
    "www.netflix.com",
    "www.youtube.com",
    "www.amazon.com",
    "www.cloudflare.com",
]

# Ping configuration
PING_COUNT = 5
PING_INTERVAL = 0.5  # seconds between pings
PING_TIMEOUT = 5  # seconds
CHECK_INTERVAL = 30  # seconds between streaming checks

# Bandwidth threshold (1 MB in 60 seconds = ~8 Mbps)
BANDWIDTH_THRESHOLD = 1_000_000

# Resolve ping executable path at startup for security (CWE-78)
PING_EXECUTABLE = shutil.which("ping")
if not PING_EXECUTABLE:
    sys.stderr.write("ERROR: 'ping' executable not found in PATH\n")
    sys.exit(1)

# Pre-compiled regex patterns for ping output parsing (performance optimization)
PACKET_LOSS_RE = re.compile(
    r"(\d+) packets transmitted, (\d+) received, ([\d.]+)% packet loss"
)
RTT_RE = re.compile(
    r"rtt min/avg/max/(?:mdev|stddev) = ([\d.]+)/([\d.]+)/([\d.]+)/([\d.]+)"
)
TTL_RE = re.compile(r"ttl=(\d+)")


def is_streaming_active(client):
    """
    Query InfluxDB to determine if any streaming device has >1 Mbps bandwidth.

    Returns:
        bool: True if streaming detected, False otherwise
    """
    # Return early if no devices configured to avoid Flux syntax error
    if not STREAMING_DEVICES:
        return False

    # Build Flux query to check bandwidth in last 60 seconds
    device_filter = " or ".join([f'r.ip == "{ip}"' for ip in STREAMING_DEVICES])

    query = f"""
from(bucket: "{INFLUXDB_BUCKET}")
  |> range(start: -60s)
  |> filter(fn: (r) =>
      r._measurement == "bandwidth" and
      r.direction == "rx" and
      ({device_filter})
  )
  |> group(columns: ["ip"])
  |> sum()
  |> filter(fn: (r) => r._value > {BANDWIDTH_THRESHOLD})
  |> group()
  |> limit(n: 1)
"""

    try:
        result = client.query_api().query(query, org=INFLUXDB_ORG)

        # If the query returns any tables, at least one device is streaming
        return len(result) > 0

    except Exception as e:
        sys.stderr.write(f"ERROR querying InfluxDB: {e}\n")
        sys.stderr.flush()
        # Default to not streaming on error (avoid unnecessary pings)
        return False


def ping_host(host):
    """
    Execute native ping command and parse results.

    Args:
        host (str): Hostname or IP to ping

    Returns:
        dict: Ping metrics or None if a critical error occurs.
    """
    # Initialize metrics with defaults for failure
    metrics = {
        "url": host,
        "packets_transmitted": PING_COUNT,
        "packets_received": 0,
        "percent_packet_loss": 100.0,
        "minimum_response_ms": 0.0,
        "average_response_ms": 0.0,
        "maximum_response_ms": 0.0,
        "standard_deviation_ms": 0.0,
        "ttl": 0,
        "result_code": 2,  # 2 = timeout/failure
    }

    try:
        # Execute ping: 5 packets, 0.5s interval, 5s timeout
        result = subprocess.run(  # nosec B603
            [
                PING_EXECUTABLE,
                "-c",
                str(PING_COUNT),
                "-i",
                str(PING_INTERVAL),
                "-W",
                str(PING_TIMEOUT),
                host,
            ],
            capture_output=True,
            text=True,
            timeout=15,
            env={"LC_ALL": "C"},
        )

        output = result.stdout

        # Parse packet statistics
        # Example: "5 packets transmitted, 3 received, 40% packet loss"
        packet_match = PACKET_LOSS_RE.search(output)
        if packet_match:
            metrics["packets_transmitted"] = int(packet_match.group(1))
            metrics["packets_received"] = int(packet_match.group(2))
            metrics["percent_packet_loss"] = float(packet_match.group(3))

        # Parse RTT statistics
        # Example: "rtt min/avg/max/mdev = 12.123/15.234/18.456/2.345 ms"
        rtt_match = RTT_RE.search(output)
        if rtt_match:
            metrics["minimum_response_ms"] = float(rtt_match.group(1))
            metrics["average_response_ms"] = float(rtt_match.group(2))
            metrics["maximum_response_ms"] = float(rtt_match.group(3))
            metrics["standard_deviation_ms"] = float(rtt_match.group(4))
            metrics["result_code"] = 0  # Success

        # Parse TTL from first ping response
        # Example: "64 bytes from ... ttl=54 time=12.3 ms"
        ttl_match = TTL_RE.search(output)
        if ttl_match:
            metrics["ttl"] = int(ttl_match.group(1))

    except subprocess.TimeoutExpired:
        sys.stderr.write(f"WARNING: Ping to {host} timed out\n")
        sys.stderr.flush()
        # Return the default failure metrics
    except Exception as e:
        sys.stderr.write(f"ERROR pinging {host}: {e}\n")
        sys.stderr.flush()
        return None

    return metrics


def output_line_protocol(metrics_list):
    """
    Output ping metrics in InfluxDB line protocol format to stdout.

    Args:
        metrics_list (list): List of metric dictionaries from ping_host()
    """
    for metrics in metrics_list:
        if metrics is None:
            continue

        # Build tags
        tags = f'host=network-monitoring,url={metrics["url"]}'

        # Build fields
        fields = [
            f'average_response_ms={metrics["average_response_ms"]}',
            f'maximum_response_ms={metrics["maximum_response_ms"]}',
            f'minimum_response_ms={metrics["minimum_response_ms"]}',
            f'packets_received={metrics["packets_received"]}i',
            f'packets_transmitted={metrics["packets_transmitted"]}i',
            f'percent_packet_loss={metrics["percent_packet_loss"]}',
            f'result_code={metrics["result_code"]}i',
            f'standard_deviation_ms={metrics["standard_deviation_ms"]}',
            f'ttl={metrics["ttl"]}i',
        ]

        # Output line protocol: measurement,tags fields
        # Telegraf will add the timestamp upon ingestion
        line = f'ping,{tags} {",".join(fields)}'
        print(line)
        sys.stdout.flush()


def main():
    """Main loop: check streaming status and conditionally ping CDNs."""

    # Validate InfluxDB token
    if not INFLUXDB_TOKEN:
        sys.stderr.write("ERROR: INFLUXDB_TOKEN environment variable not set\n")
        sys.exit(1)

    # Initialize InfluxDB client
    try:
        client = InfluxDBClient(
            url=INFLUXDB_URL, token=INFLUXDB_TOKEN, org=INFLUXDB_ORG
        )
        sys.stderr.write("Opportunistic CDN Ping Orchestrator started\n")
        sys.stderr.write(f"  InfluxDB: {INFLUXDB_URL}\n")
        sys.stderr.write(f"  Bucket: {INFLUXDB_BUCKET}\n")
        sys.stderr.write(f"  Streaming devices: {', '.join(STREAMING_DEVICES)}\n")
        sys.stderr.write(f"  CDN hosts: {', '.join(CDN_HOSTS)}\n")
        sys.stderr.write(f"  Check interval: {CHECK_INTERVAL}s\n")
        sys.stderr.flush()
    except Exception as e:
        sys.stderr.write(f"ERROR initializing InfluxDB client: {e}\n")
        sys.exit(1)

    # Main loop
    while True:
        try:
            # Check if streaming is active
            streaming = is_streaming_active(client)

            if streaming:
                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                sys.stderr.write(f"[{timestamp}] Streaming detected - pinging CDNs\n")
                sys.stderr.flush()

                # Ping all CDNs
                metrics_list = []
                for cdn in CDN_HOSTS:
                    metrics = ping_host(cdn)
                    if metrics:
                        metrics_list.append(metrics)

                # Output line protocol to stdout (Telegraf ingests this)
                if metrics_list:
                    output_line_protocol(metrics_list)
            else:
                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                sys.stderr.write(
                    f"[{timestamp}] No streaming detected - skipping pings\n"
                )
                sys.stderr.flush()

        except KeyboardInterrupt:
            sys.stderr.write("Shutting down...\n")
            break

        except Exception as e:
            sys.stderr.write(f"ERROR in main loop: {e}\n")
            sys.stderr.flush()

        # Wait before next check
        time.sleep(CHECK_INTERVAL)

    # Cleanup
    client.close()


if __name__ == "__main__":
    main()
