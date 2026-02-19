# Data Collection Methods

**Purpose:** Explain how data flows from the router to Grafana dashboards

**Architecture:** Pure InfluxDB (no Prometheus server)

---

## Overview

This system collects network monitoring data from a GL-MT2500A OpenWrt router and processes it on a Mac Mini. All data flows through Telegraf into InfluxDB (single source of truth), then visualized in Grafana.

**Key Principle:** Keep router CPU low by doing minimal work on the router and processing data on the Mac Mini.

---

## Data Flow Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│  Router (GL-MT2500A @ 192.168.1.2)                              │
│  - 2-core MediaTek MT7621A @ 880 MHz                            │
│  - 1 GB RAM                                                     │
│  - Must stay <15% CPU average                                   │
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │ Lightweight Data Collectors:                             │  │
│  │                                                          │  │
│  │ 1. nlbwmon (kernel module)                              │  │
│  │    └─ Per-device bandwidth tracking                     │  │
│  │    └─ Queried by cron script every 60s                  │  │
│  │                                                          │  │
│  │ 2. dnsmasq (DNS server)                                 │  │
│  │    └─ DNS query logging                                 │  │
│  │    └─ Sends to syslog                                   │  │
│  │                                                          │  │
│  │ 3. prometheus-node-exporter-lua                         │  │
│  │    └─ HTTP endpoint exposing router health              │  │
│  │    └─ CPU, memory, interfaces, uptime                   │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                  │
│         │ UDP         │ syslog        │ HTTP                    │
│         │ :8094       │ :514          │ :9100                   │
└─────────┼─────────────┼───────────────┼──────────────────────────┘
          │             │               │
          ▼             ▼               ▼
┌─────────────────────────────────────────────────────────────────┐
│  Mac Mini (192.168.1.126) - Processing Hub                      │
│  - 6-core Intel Core i7 @ 3.2 GHz                              │
│  - 64 GB RAM                                                    │
│  - 2TB SSD                                                      │
│  - Can handle all heavy processing                              │
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │ Telegraf (Data Collector)                                │  │
│  │                                                          │  │
│  │ Inputs:                                                  │  │
│  │ • inputs.socket_listener (UDP:8094) - bandwidth data    │  │
│  │ • inputs.syslog (UDP:514) - DNS logs                    │  │
│  │ • inputs.prometheus (HTTP:9100) - router health         │  │
│  │ • inputs.ping - infrastructure & WAN health             │  │
│  │ • inputs.execd - CDN pinging, fault analysis            │  │
│  │                                                          │  │
│  │ Processing:                                              │  │
│  │ • Parses, enriches, and batches data                    │  │
│  │ • Adds tags, resolves names                             │  │
│  │ • Rate limiting, buffering                              │  │
│  └──────────────────────┬───────────────────────────────────┘  │
│                         │                                       │
│                         ▼ InfluxDB line protocol                │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │ InfluxDB 2.7 (Time-Series Database)                     │  │
│  │ • Bucket: "network"                                      │  │
│  │ • Retention: 1 year                                      │  │
│  │ • Single source of truth (Pure InfluxDB)                │  │
│  └──────────────────────┬───────────────────────────────────┘  │
│                         │                                       │
│                         ▼ Flux queries                          │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │ Grafana (Visualization)                                  │  │
│  │ • Dashboards: infrastructure, streaming, devices        │  │
│  │ • Data source: InfluxDB only (no Prometheus)            │  │
│  └──────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

---

## Collection Method 1: UDP Push (Bandwidth)

**Status:** ✅ Currently Active

**How It Works:**
1. Router runs cron job every 60 seconds: `send-bandwidth-to-influx.sh`
2. Script queries nlbwmon database (kernel module, very efficient)
3. Calculates bandwidth deltas since last run
4. Formats as InfluxDB line protocol
5. Sends via UDP to Mac Mini:8094 (fire-and-forget, non-blocking)

**Router CPU:** <1%

**Data Format:**
```
bandwidth,device_name=MacBook,ip=192.168.1.100,mac=AA:BB:CC:DD:EE:FF,protocol=https,direction=rx bytes=1048576i 1609459200000000000
```

**Why UDP?**
- Fire-and-forget (no blocking if Mac Mini is down)
- Minimal router overhead
- Natural batching via cron interval

---

## Collection Method 2: Syslog (DNS Queries)

**Status:** 🔄 Planned (Phase 3)

**How It Works:**
1. dnsmasq on router logs DNS queries
2. Queries sent to syslog
3. Syslog forwards to Mac Mini via UDP:514
4. Telegraf inputs.syslog receives and parses logs
5. Grok pattern extracts: query type, domain, client IP
6. Telegraf sends to InfluxDB

**Router CPU:** <1%

**Data Format:**
```
dns_query,device_name=MacBook,ip=192.168.1.100,query_type=A domain="google.com" 1609459200000000000
```

**Why Syslog?**
- Built into OpenWrt
- Robust, proven protocol
- Low overhead on router
- Parsing happens on Mac Mini

---

## Collection Method 3: HTTP Scraping (Router Health)

**Status:** 🔄 Planned (Phase 2)

**How It Works:**
1. prometheus-node-exporter-lua runs on router (HTTP server on port 9100)
2. Exposes router metrics in Prometheus format (like a JSON API)
3. Telegraf inputs.prometheus scrapes endpoint every 60 seconds
4. Telegraf converts Prometheus format to InfluxDB format
5. Stores in InfluxDB (Pure InfluxDB architecture maintained)

**Router CPU:** 2-5%

**Data Format (Prometheus → InfluxDB):**
```
# Prometheus format from router:
node_cpu_seconds_total{cpu="0",mode="idle"} 98765.43

# Converted to InfluxDB by Telegraf:
router_stats,device=glmt2500a,cpu=0,mode=idle value=98765.43 1609459200000000000
```

**Why HTTP Scraping?**
- Pull-based (router doesn't initiate connections)
- Easy to debug (curl http://192.168.1.2:9100/metrics)
- Standard format
- Lightweight HTTP server

**Important:** This does NOT use Prometheus server. prometheus-node-exporter is just a way to expose metrics. Telegraf scrapes it and stores everything in InfluxDB.

---

## Collection Method 4: Ping Monitoring (Infrastructure)

**Status:** ✅ Currently Active

**How It Works:**
1. Telegraf inputs.ping on Mac Mini
2. Sends ICMP pings to targets every 10-30 seconds:
   - Routers: 192.168.1.2, 192.168.2.1
   - Starlink Dishy: 192.168.100.1
   - WAN: 8.8.8.8, 1.1.1.1
3. Measures latency, packet loss, availability
4. Stores directly in InfluxDB

**Router CPU:** 0% (Mac Mini does the pinging)

**Data Format:**
```
ping,type=infrastructure,url=192.168.1.2 average_response_ms=1.2,packet_loss=0.0 1609459200000000000
```

**Why Ping from Mac Mini?**
- Zero router overhead
- More reliable (Mac Mini always on)
- Can ping external targets without router involvement

---

## Collection Method 5: Exec Scripts (Custom Logic)

**Status:** ✅ Currently Active (CDN pinging) + 🔄 Planned (fault analysis)

**How It Works:**
1. Telegraf inputs.execd runs Python scripts on Mac Mini
2. Scripts execute custom logic (query InfluxDB, analyze data, ping CDNs)
3. Scripts output InfluxDB line protocol to stdout
4. Telegraf ingests the output
5. Data stored in InfluxDB

**Examples:**

### CDN Monitoring (Active)
```python
# scripts/streaming-ping-orchestrator.py
# 1. Query InfluxDB for streaming device bandwidth
# 2. If streaming detected (>1 MB in last 60s), ping CDNs
# 3. Output: ping,type=cdn,target=netflix.com latency=25.3
```

### Fault Analysis (Planned)
```python
# scripts/streaming-fault-analyzer.py
# 1. Query router CPU from InfluxDB
# 2. Query CDN latency from InfluxDB
# 3. Query WAN packet loss from InfluxDB
# 4. Calculate confidence scores for each fault source
# 5. Output: streaming_fault,source=router_overload confidence=90
```

**Router CPU:** 0% (scripts run on Mac Mini)

---

## Why This Architecture?

### Previous Problem: Router CPU Overload (90%)

**What Caused It:**
- Multiple monitoring scripts running on router simultaneously
- Real-time processing of every DNS query
- Running `conntrack -L` hundreds of times per second
- DPI engine (netifyd) consuming 341MB RAM and 15-25% CPU
- No batching, no rate limiting

**Result:**
- Router CPU: 90% (0% idle)
- DNS timeouts: 2,242 per domain in 30 days
- Complete network outages

### Current Solution: Move Processing to Mac Mini

**Router Work:**
- nlbwmon: Kernel module (very efficient)
- dnsmasq: Just logging (built-in feature)
- node-exporter: Lightweight HTTP server
- **Total Router CPU: 5-8%** (down from 90%)

**Mac Mini Work:**
- All parsing, enrichment, aggregation
- Heavy queries, analysis scripts
- DPI (if needed, via ntopng)
- **Mac Mini CPU: Negligible** (currently 32%, plenty of headroom)

---

## Data Collection Frequency Summary

| Data Type | Method | Frequency | Router CPU | Where Processed |
|-----------|--------|-----------|------------|-----------------|
| **Bandwidth** | UDP push | 60s | <1% | Router (cron) |
| **DNS queries** | Syslog | Real-time | <1% | Mac Mini (Telegraf) |
| **Router health** | HTTP scrape | 60s | 2-5% | Mac Mini (Telegraf) |
| **Infrastructure ping** | ICMP | 10-30s | 0% | Mac Mini (Telegraf) |
| **CDN ping** | Exec script | 30s (conditional) | 0% | Mac Mini (Python) |
| **Fault analysis** | Exec script | 30s | 0% | Mac Mini (Python) |

**Total Router CPU: 5-8%** (vs previous 90%)

---

## What We're NOT Using

### ❌ Prometheus Server
- We migrated FROM Prometheus TO Pure InfluxDB
- Reason: Time-range filtering was broken in Prometheus
- Status: Prometheus server completely removed

### ❌ NetFlow / sFlow
- Too much overhead for home network (3-8% router CPU)
- Current approach (bandwidth + DNS) provides sufficient visibility
- NetFlow would be overkill

### ❌ netifyd (DPI on Router)
- Caused 90% CPU usage crisis
- 341MB RAM consumption (34% of 1GB router RAM)
- If DPI needed, use ntopng on Mac Mini instead

### ❌ Real-time Router Scripts
- Previous `dns-monitor-daemon.sh`, `connections-monitor-daemon.sh` disabled
- Caused CPU thrashing with real-time processing
- Replaced with batched/sampled approaches

---

## Troubleshooting Data Flow

### Check if data is flowing from router to Mac Mini:

**1. Bandwidth (UDP:8094):**
```bash
# On Mac Mini - check if Telegraf is receiving data
podman logs telegraf | grep bandwidth | tail -20

# On router - check if script is running
ssh root@192.168.1.2 "crontab -l | grep bandwidth"
```

**2. DNS (Syslog:514):**
```bash
# On Mac Mini - check syslog listener
podman logs telegraf | grep dns_query | tail -20

# On router - check if dnsmasq logging enabled
ssh root@192.168.1.2 "uci show dhcp.@dnsmasq[0].logqueries"
```

**3. Router Health (HTTP:9100):**
```bash
# Test router endpoint directly
curl http://192.168.1.2:9100/metrics | head -20

# Check if Telegraf is scraping
podman logs telegraf | grep prometheus | tail -20
```

**4. Check InfluxDB has data:**
```bash
# Enter InfluxDB container
podman exec -it influxdb influx

# Query for recent bandwidth data
from(bucket: "network")
  |> range(start: -1h)
  |> filter(fn: (r) => r._measurement == "bandwidth")
  |> limit(n: 10)
```

---

## Future Enhancements

**Potential additions (not planned yet):**
- Connection tracking via `conntrack -E` event stream (low overhead)
- eero mesh monitoring (see docs/FEATURE-eero-monitoring.md)
- Application inference via DNS domain mapping
- Alerting via Grafana alerts or external service

**Principle:** Only add if benefits outweigh router CPU cost
