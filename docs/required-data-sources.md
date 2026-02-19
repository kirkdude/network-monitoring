# Required Data Sources for Grafana Dashboards

**Analysis Date:** 2026-01-04
**Purpose:** Identify minimum data needed from router to support all existing dashboards

---

## Architecture Clarification: Pure InfluxDB

**IMPORTANT:** This system uses **Pure InfluxDB** architecture. We do NOT use Prometheus server.

### What We're NOT Using:
- ❌ Prometheus server/database
- ❌ Prometheus queries in Grafana
- ❌ Prometheus data storage

### What We ARE Using:
- ✅ prometheus-node-exporter-lua on router (just a **metrics exporter**, like a JSON API)
- ✅ Telegraf scrapes the prometheus-node-exporter HTTP endpoint
- ✅ Telegraf stores ALL data in InfluxDB
- ✅ Grafana queries InfluxDB using Flux

### Data Flow:
```
Router (prometheus-node-exporter @ :9100) → Telegraf (scraper) → InfluxDB → Grafana
           ↑
    Just a metric format
    (NOT Prometheus server)
```

**Why This Matters:**
We migrated from Prometheus to Pure InfluxDB due to time-range filtering issues. The name "prometheus-node-exporter" is confusing - it's just a standard way to expose metrics (like JSON or CSV format), not a database. Think of it as "HTTP metrics API that happens to use Prometheus format."

---

## Dashboard Inventory

1. **infrastructure-status.json** - Router & network health
2. **device-detail.json** - Per-device deep dive
3. **dns-activity-influx.json** - DNS query analytics
4. **all-devices.json** - Device overview
5. **client-monitoring.json** - Client tracking
6. **streaming-monitor.json** - Streaming detection

---

## Required InfluxDB Measurements

### 1. **`ping`** - Network Connectivity
**Used By:** Infrastructure Status, Device Detail

**Tags:**
- `type` = "infrastructure" | "wan_health" | "starlink_dishy"
- `url` = target IP/hostname
- `host` = "network-monitoring"

**Fields:**
- `result_code` (0=success, 2=timeout)
- `average_response_ms`
- `percent_packet_loss`
- `minimum_response_ms`
- `maximum_response_ms`

**Current Source:** Telegraf `inputs.ping` on Mac Mini ✅ (already efficient)

**Frequency:** Every 15-30 seconds

---

### 2. **`router_stats`** - Router Health Metrics
**Used By:** Infrastructure Status

**Tags:**
- `device` = "glmt2500a"
- `interface` = "wan"
- `host` = "network-monitoring"

**Fields:**
- `cpu_user`, `cpu_system`, `cpu_total` (for CPU % calculation)
- `mem_used`, `mem_total`, `mem_cached` (for memory % calculation)
- `uptime` (seconds)
- `rx_rate`, `tx_rate` (bytes/sec)
- `rx_errors`, `tx_errors`, `rx_dropped`, `tx_dropped`

**Current Source:** `router-stats-daemon.sh` on router (disabled)

**Needed From Router:** CPU, memory, uptime, WAN interface stats

**Frequency:** Every 60 seconds

---

### 3. **`bandwidth`** - Per-Device Bandwidth
**Used By:** Device Detail, All Devices

**Tags:**
- `device_name` = friendly device name
- `ip` = device IP address
- `mac` = device MAC address
- `protocol` = application protocol (http, https, dns, etc.)
- `direction` = "rx" | "tx"

**Fields:**
- `bytes` = bytes transferred (delta)

**Current Source:** `send-bandwidth-to-influx.sh` ✅ (kept, efficient via cron)

**Frequency:** Every 60 seconds (cron)

---

### 4. **`dns_query`** - DNS Activity
**Used By:** DNS Activity, Device Detail

**Tags:**
- `device_name` = friendly device name
- `ip` = client IP
- `mac` = client MAC
- `query_type` = "A" | "AAAA" | "MX" | etc.

**Fields:**
- `domain` = queried domain (string)

**Current Source:** `dns-monitor-daemon.sh` or `stream-dns-events.sh` (both disabled, were duplicates)

**Needed From Router:** DNS queries per device

**Frequency:** Real-time or batched (1-10 second batches)

---

### 5. **`connection_events`** - Connection Tracking
**Used By:** Device Detail

**Tags:**
- `device_name` = friendly device name
- `ip` = source IP
- `dst_ip` = destination IP
- `hostname` = reverse DNS of destination (optional)
- `protocol` = "tcp" | "udp" | "icmp"

**Fields:**
- `src_port` = source port (used for counting)
- `dst_port` = destination port

**Current Source:** `monitor-connection-flows.sh` (disabled)

**Needed From Router:** Connection events with IPs/ports

**Frequency:** Real-time or batched (30 second batches)

---

### 6. **`dpi_flow`** - Application Detection (OPTIONAL)
**Used By:** Device Detail (Application Bandwidth Distribution panel)

**Tags:**
- `device_name` = friendly device name
- `ip` = device IP
- `app` = application name (netflix, youtube, etc.)
- `protocol` = detected protocol

**Fields:**
- `flows` = flow count
- `bytes` = bytes transferred

**Current Source:** `send-dpi-flows-to-influx.sh` + netifyd (disabled, CPU killer)

**Status:** ⚠️ **OPTIONAL** - Only used in 1 panel across all dashboards

**Alternatives:**
- Move to Mac Mini with ntopng
- Live without it (most dashboards don't need it)
- Use protocol-based approximation from `bandwidth` measurement

---

## Data Priority Classification

### 🔴 **CRITICAL** - Required for core functionality
1. `ping` - Infrastructure monitoring ✅ (already efficient)
2. `router_stats` - Router health
3. `bandwidth` - Per-device usage ✅ (already efficient)

### 🟡 **IMPORTANT** - Used in multiple dashboards
4. `dns_query` - DNS analytics
5. `connection_events` - Connection tracking

### 🟢 **NICE TO HAVE** - Used in 1 panel
6. `dpi_flow` - Application detection

---

## Efficient Data Export Strategy: Option A

**Goal:** Get data off router to Mac Mini without killing router CPU

### Architecture

```
┌─────────────────────────────────────────────────────────────┐
│ Router (GL-MT2500A)                                         │
│                                                             │
│  ┌──────────────────────────────────────────────────────┐  │
│  │ Data Collection (lightweight)                        │  │
│  │                                                      │  │
│  │  • prometheus-node-exporter-lua (HTTP endpoint)     │  │
│  │    ├─ CPU, memory, uptime                           │  │
│  │    ├─ Network interface stats                       │  │
│  │    └─ System metrics                                │  │
│  │                                                      │  │
│  │  • dnsmasq --log-facility=- (stdout)                │  │
│  │    └─ DNS queries → syslog-ng → remote UDP         │  │
│  │                                                      │  │
│  │  • nlbwmon (already efficient)                      │  │
│  │    └─ Per-device bandwidth                          │  │
│  │                                                      │  │
│  │  • conntrack event system (optional)                │  │
│  │    └─ New connections only (not full table dump)   │  │
│  └──────────────────────────────────────────────────────┘  │
│                                                             │
│             │        │           │                          │
│             │        │           │                          │
│             HTTP    UDP         Cron                        │
│             GET     Stream      Script                      │
└─────────────┼────────┼───────────┼──────────────────────────┘
              │        │           │
              ▼        ▼           ▼
┌─────────────────────────────────────────────────────────────┐
│ Mac Mini (Data Processing Hub)                              │
│                                                             │
│  ┌──────────────────────────────────────────────────────┐  │
│  │ Telegraf (collector)                                 │  │
│  │                                                      │  │
│  │  • HTTP scraper → prometheus-node-exporter          │  │
│  │    └─ Polls every 60s                               │  │
│  │                                                      │  │
│  │  • UDP listener → DNS events                        │  │
│  │    └─ Batches & enriches                            │  │
│  │                                                      │  │
│  │  • Exec script → bandwidth data                     │  │
│  │    └─ SSH fetch from router                         │  │
│  │                                                      │  │
│  │  • Exec script → connection events (optional)       │  │
│  │    └─ SSH conntrack -E (event stream)               │  │
│  └──────────────────────────────────────────────────────┘  │
│                         │                                   │
│                         ▼                                   │
│                   InfluxDB v2                               │
│                         │                                   │
│                         ▼                                   │
│                     Grafana                                 │
│                                                             │
│  ┌──────────────────────────────────────────────────────┐  │
│  │ ntopng (optional - for DPI)                          │  │
│  │  • Monitors en0 interface                           │  │
│  │  • Application detection                            │  │
│  │  • No router impact                                 │  │
│  └──────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

---

## Method 1: Router Health Metrics via HTTP Exporter (RECOMMENDED)

**Note:** Despite the name "prometheus-node-exporter", this does NOT use Prometheus server. It's just an HTTP API that exposes metrics in Prometheus format. Telegraf scrapes it and stores in InfluxDB.

### On Router

**Package:** `prometheus-node-exporter-lua` (already installed!)

**What it does:**
- Exposes router metrics via HTTP endpoint (like a JSON API, but in Prometheus format)
- Lightweight Lua implementation for OpenWrt
- ~2-5% CPU, minimal memory
- **NOT a Prometheus server** - just a metrics exporter

**Exposes:**
```
http://192.168.1.2:9100/metrics

# HELP node_cpu_seconds_total Seconds the CPUs spent in each mode
node_cpu_seconds_total{cpu="0",mode="user"} 12345.67
node_cpu_seconds_total{cpu="0",mode="system"} 2345.67
node_cpu_seconds_total{cpu="0",mode="idle"} 98765.43

# HELP node_memory_MemTotal_bytes Memory information field MemTotal_bytes
node_memory_MemTotal_bytes 1.014972416e+09

# HELP node_network_receive_bytes_total Network device statistic receive_bytes
node_network_receive_bytes_total{device="eth0"} 1.234567890123e+12
```

### On Mac Mini (Telegraf)

**Add to `telegraf.conf`:**
```toml
[[inputs.prometheus]]
  # Scrape the router's HTTP endpoint
  # This reads Prometheus format but stores in InfluxDB (Pure InfluxDB architecture)
  urls = ["http://192.168.1.2:9100/metrics"]
  interval = "60s"

  # Rename to match existing dashboard queries
  name_override = "router_stats"

  [inputs.prometheus.tags]
    device = "glmt2500a"
    host = "network-monitoring"
```

**Benefits:**
- ✅ Pull-based (router doesn't initiate)
- ✅ Standard metric format (easy to parse)
- ✅ Lightweight on router (2-5% CPU)
- ✅ Easy to debug (curl http://192.168.1.2:9100/metrics)
- ✅ No custom scripts on router
- ✅ Data flows to InfluxDB (Pure InfluxDB architecture maintained)

---

## Method 2: DNS Query Export

### Option 2A: Syslog-ng UDP Forwarding (BEST)

**On Router:**
```bash
# Install syslog-ng
opkg update
opkg install syslog-ng

# Configure /etc/syslog-ng.conf
destination influxdb {
    udp("192.168.1.124" port(8094));
};

filter f_dnsmasq {
    program("dnsmasq");
};

log {
    source(src);
    filter(f_dnsmasq);
    destination(influxdb);
};

# Configure dnsmasq to log to syslog
uci set dhcp.@dnsmasq[0].logqueries='1'
uci set dhcp.@dnsmasq[0].logfacility='local0'
uci commit dhcp
/etc/init.d/dnsmasq restart
```

**On Mac Mini (Telegraf):**
```toml
[[inputs.syslog]]
  server = "udp://:8094"

  # Parse dnsmasq log format
  # Jan  4 20:00:00 dnsmasq[1234]: query[A] www.google.com from 192.168.1.100

[[processors.regex]]
  [[processors.regex.fields]]
    key = "message"
    pattern = 'query\[([A-Z]+)\] ([^ ]+) from ([0-9.]+)'
    replacement = "${1},${2},${3}"
    result_key = "parsed"

[[processors.strings]]
  [[processors.strings.split]]
    field = "parsed"
    separator = ","
    fields = ["query_type", "domain", "ip"]

[[outputs.influxdb_v2]]
  urls = ["http://influxdb:8086"]
  # ... existing config
```

**Benefits:**
- ✅ Native dnsmasq feature
- ✅ UDP (fire-and-forget, no blocking)
- ✅ Router CPU: <1%
- ✅ Batching happens in Telegraf buffer

### Option 2B: Telegraf Tail Plugin (SIMPLER)

**On Router:**
```bash
# Enable dnsmasq logging to file
uci set dhcp.@dnsmasq[0].logqueries='1'
uci commit dhcp
/etc/init.d/dnsmasq restart
```

**On Mac Mini (Telegraf):**
```toml
[[inputs.tail]]
  # Read dnsmasq log via SSH
  files = ["ssh://root@192.168.1.2:/var/log/dnsmasq.log"]

  data_format = "grok"
  grok_patterns = [
    '%{SYSLOGTIMESTAMP:timestamp} dnsmasq\[%{NUMBER:pid}\]: query\[%{WORD:query_type}\] %{NOTSPACE:domain} from %{IP:ip}'
  ]

  [inputs.tail.tags]
    measurement = "dns_query"
```

**Benefits:**
- ✅ Simplest setup
- ✅ Telegraf handles parsing on Mac Mini
- ✅ No router config beyond enabling logging

---

## Method 3: Bandwidth Data

### Current: SSH Fetch (KEEP THIS)

**Already working via cron:**
```bash
# On router: /etc/crontabs/root
* * * * * /root/bin/send-bandwidth-to-influx.sh
```

**How it works:**
1. Reads `nlbwmon` data (efficient, kernel-based)
2. Calculates deltas
3. Sends via UDP to Mac Mini

**Alternative for Option A:**
```toml
# On Mac Mini: telegraf.conf
[[inputs.exec]]
  commands = ["/usr/local/bin/fetch-router-bandwidth.sh"]
  interval = "60s"
  timeout = "10s"
  data_format = "influx"

# /usr/local/bin/fetch-router-bandwidth.sh
#!/bin/bash
ssh root@192.168.1.2 "nlbw -c show" | \
  awk '...' | \
  # Parse and format as InfluxDB line protocol
```

**Decision:** Keep existing cron script - it's already efficient.

---

## Method 4: Connection Events (Optional)

### Option 4A: conntrack Event Stream

**On Mac Mini (Telegraf):**
```toml
[[inputs.execd]]
  command = ["ssh", "root@192.168.1.2", "conntrack", "-E", "-o", "extended"]
  signal = "none"
  restart_delay = "10s"
  data_format = "grok"

  grok_patterns = [
    '\[NEW\] %{WORD:proto} .* src=%{IP:src_ip} .* dst=%{IP:dst_ip} .* sport=%{NUMBER:src_port} dport=%{NUMBER:dst_port}'
  ]
```

**Benefits:**
- ✅ Only captures NEW connections (not full table dumps)
- ✅ Event-based (efficient)
- ✅ Processing happens on Mac Mini

**Router Impact:** Minimal (just event stream output)

### Option 4B: Live Without It

**Reality Check:**
- Only used in "Connection History" and "Top Destination IPs" panels
- Can be replaced with DNS query data (shows domains accessed)
- Connection count can be approximated from bandwidth data

**Recommendation:** Skip it initially, see if anyone misses it.

---

## Method 5: DPI / Application Detection

### Option 5A: ntopng on Mac Mini

**You already have this in docker-compose.yml!**
```yaml
ntopng:
  image: ntop/ntopng:latest
  container_name: ntopng
  restart: unless-stopped
  network_mode: host
  volumes:
    - ntopng_data:/var/lib/ntopng
  command: >
    --interface en0
    --http-port 3001
```

**Enable it:**
```bash
cd /Users/kirkl/src/network-monitoring
podman-compose up -d ntopng
```

**Configure ntopng to export to InfluxDB:**
```
# In ntopng web UI (http://localhost:3001)
Settings → Data Export → InfluxDB
  Host: localhost:8086
  Database: network
  Token: <your-token>
```

**Benefits:**
- ✅ Full DPI on Mac Mini (zero router impact)
- ✅ Better application detection than netifyd
- ✅ Web UI for troubleshooting
- ✅ Already in your stack!

### Option 5B: Skip DPI Entirely

**Used in:** 1 panel ("Application Bandwidth Distribution")

**Alternative:** Use protocol field from `bandwidth` measurement
- `protocol="https"` shows HTTPS traffic
- `protocol="http"` shows HTTP traffic
- Good enough for most cases

---

## Implementation Plan

### Phase 1: Router Health (30 minutes)

1. **Enable prometheus-node-exporter on router:**
   ```bash
   ssh root@192.168.1.2 "/etc/init.d/prometheus-node-exporter-lua start"
   ssh root@192.168.1.2 "/etc/init.d/prometheus-node-exporter-lua enable"
   curl http://192.168.1.2:9100/metrics | head -20
   ```

2. **Add Telegraf scraper on Mac Mini:**
   - Edit `telegraf.conf`
   - Add `inputs.prometheus` section
   - Restart Telegraf
   - Verify data in InfluxDB

3. **Test dashboard:**
   - Open Infrastructure Status dashboard
   - Verify CPU, memory, WAN stats appear

**Expected time:** 30 minutes
**Router impact:** <5% CPU

---

### Phase 2: DNS Activity (1 hour)

**Decision needed:** Syslog-ng (more setup) vs Tail plugin (simpler)

**Recommended:** Tail plugin (simpler)

1. **Enable dnsmasq logging on router:**
   ```bash
   ssh root@192.168.1.2 "uci set dhcp.@dnsmasq[0].logqueries='1'; uci commit dhcp; /etc/init.d/dnsmasq restart"
   ```

2. **Add Telegraf tail input on Mac Mini:**
   - Edit `telegraf.conf`
   - Add `inputs.tail` with SSH path
   - Configure grok pattern
   - Restart Telegraf

3. **Test dashboard:**
   - Open DNS Activity dashboard
   - Verify queries appear

**Expected time:** 1 hour
**Router impact:** ~2% CPU (logging), 0% (Telegraf pulls via SSH)

---

### Phase 3: DPI (Optional - 30 minutes)

**Recommended:** Enable ntopng on Mac Mini

1. **Uncomment ntopng in docker-compose.yml**
2. **Start container:** `podman-compose up -d ntopng`
3. **Configure InfluxDB export** via web UI
4. **Map measurements** to match dashboard queries

**Expected time:** 30 minutes
**Router impact:** 0% (runs on Mac Mini)

---

## Expected Results

### Router Performance After Migration

**Before (with all scripts):**
- CPU: 90% (0% idle)
- Load: 3.24
- Memory: 453MB free
- DNS timeouts: 2,242 per domain

**After (Option A):**
- CPU: <15% (85% idle)
- Load: <0.5
- Memory: 800MB+ free
- DNS timeouts: 0

### Data Completeness

| Measurement | Before | After | Notes |
|-------------|--------|-------|-------|
| ping | ✅ | ✅ | No change (Telegraf on Mac) |
| router_stats | ✅ | ✅ | Prometheus exporter |
| bandwidth | ✅ | ✅ | Keep existing cron script |
| dns_query | ✅ | ✅ | Tail plugin or syslog-ng |
| connection_events | ✅ | ⚠️ Optional | Skippable |
| dpi_flow | ✅ | ✅ | ntopng on Mac Mini |

---

## Questions for Implementation

1. **DNS Method:** Tail plugin (simpler) or syslog-ng (more robust)?

2. **Connection Events:** Need it? Or live without "Connection History" panel?

3. **DPI:** Enable ntopng on Mac Mini? Or skip application detection?

4. **Timeline:** Implement Phase 1 now? Or all phases at once?

---

## Cost-Benefit Analysis

### Option A (Move to Mac Mini)

**Pros:**
- ✅ Router CPU drops from 90% → <15%
- ✅ Network stability restored
- ✅ Better DPI (ntopng > netifyd)
- ✅ Easier debugging (logs on Mac)
- ✅ More scalable (Mac has resources)

**Cons:**
- ⏱️ 2-3 hours implementation
- 📝 More complex Telegraf config
- 🔗 Dependency on Mac Mini uptime

**Verdict:** **Strong Recommend** - Fixes the root cause

---

### Option B (Efficient Router Scripts)

**Pros:**
- 📦 Self-contained on router
- 🔧 No external dependencies
- 💾 Familiar scripting

**Cons:**
- ⏱️ 4-6 hours to rewrite scripts efficiently
- 🐛 Custom code to maintain
- ⚠️ Still some router CPU impact (10-15%)
- 🚫 No DPI without netifyd

**Verdict:** Only if you can't use Mac Mini

---

## Recommendation

**Implement Option A (Move to Mac Mini) in 3 phases:**

1. **Phase 1:** Router health via prometheus-node-exporter (30 min)
2. **Phase 2:** DNS via Telegraf tail plugin (1 hour)
3. **Phase 3:** DPI via ntopng (30 min) - OPTIONAL

**Total time:** 2 hours for essential monitoring
**Router impact:** <5% CPU (vs 90% before)
**Dashboard compatibility:** 100%

Ready to implement Phase 1?
