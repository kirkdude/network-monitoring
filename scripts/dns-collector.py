#!/usr/bin/env python3
"""
DNS Query Collector - Fetches new DNS queries from router log via SSH
Runs every 60s via Telegraf execd, outputs InfluxDB line protocol
"""

import subprocess
import re
import sys
import time

STATE_FILE = "/tmp/dns-log-position.txt"
ROUTER = "root@192.168.1.2"
LOG_FILE = "/var/log/dnsmasq.log"

def get_last_position():
    """Read last processed position from state file"""
    try:
        with open(STATE_FILE, 'r') as f:
            return int(f.read().strip())
    except:
        return 0

def save_position(position):
    """Save current position to state file"""
    with open(STATE_FILE, 'w') as f:
        f.write(str(position))

def fetch_new_log_data(position):
    """Fetch new bytes from log file via SSH"""
    cmd = f'ssh {ROUTER} "tail -c +{position + 1} {LOG_FILE}"'
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=10)
    return result.stdout

def parse_dns_query(line):
    """Parse dnsmasq log line and extract DNS query details"""
    # Match: query[A] domain from IP or query[type=65] domain from IP
    match = re.search(r'query\[(?:type=)?([A-Z0-9]+)\]\s+(\S+)\s+from\s+([0-9.]+)', line)
    if not match:
        return None

    query_type, domain, client_ip = match.groups()
    return {
        'query_type': query_type,
        'domain': domain.rstrip('.'),  # Remove trailing dot
        'client_ip': client_ip
    }

def main():
    """Main collection loop"""
    last_position = get_last_position()

    # Fetch new data
    try:
        new_data = fetch_new_log_data(last_position)
    except Exception as e:
        print(f"# Error fetching log data: {e}", file=sys.stderr)
        return

    if not new_data:
        return  # No new data

    # Parse and output InfluxDB line protocol
    timestamp_ns = int(time.time() * 1e9)
    query_count = 0

    for line in new_data.split('\n'):
        if 'query[' not in line or 'from' not in line:
            continue

        query = parse_dns_query(line)
        if query:
            # Escape special chars in domain for InfluxDB line protocol
            domain = query['domain'].replace(',', '\\,').replace(' ', '\\ ').replace('=', '\\=')

            # Output InfluxDB line protocol
            print(f"dns_query,query_type={query['query_type']},client_ip={query['client_ip']} domain=\"{domain}\" {timestamp_ns}")
            query_count += 1

    # Update position
    new_position = last_position + len(new_data.encode('utf-8'))
    save_position(new_position)

    # Log to stderr for debugging
    if query_count > 0:
        print(f"Processed {query_count} DNS queries", file=sys.stderr)

if __name__ == "__main__":
    # Run once and exit - Telegraf exec will re-invoke every 60s
    try:
        main()
    except Exception as e:
        print(f"# ERROR: {e}", file=sys.stderr)
        sys.exit(1)
