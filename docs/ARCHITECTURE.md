# Network Monitoring Architecture

Pure InfluxDB event-based monitoring for home network with real-time data collection.

## Architecture Overview

**Important:** This system uses **Pure InfluxDB** architecture. We do NOT use Prometheus server. We previously migrated from Prometheus to InfluxDB due to time-range filtering issues.

### Data Flow

```
┌─────────────────────────────────────────────────────────────┐
│  Router (GL-MT2500A @ 192.168.1.2)                         │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ Data Collectors:                                     │   │
│  │ • nlbwmon (bandwidth tracking)                       │   │
│  │ • dnsmasq (DNS logging)                              │   │
│  │ • prometheus-node-exporter-lua (router health)       │   │
│  └─────────────────────────────────────────────────────┘   │
│                     │                                        │
│                     │ Lightweight exports only               │
│                     │ (UDP push, HTTP endpoints, syslog)    │
└─────────────────────┼────────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────┐
│  Mac Mini (192.168.1.126) - Processing Hub                 │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ Telegraf (Collector)                                 │   │
│  │ • inputs.socket_listener (UDP:8094 - bandwidth)      │   │
│  │ • inputs.syslog (UDP:514 - DNS logs)                 │   │
│  │ • inputs.prometheus (HTTP:9100 - router health)      │   │
│  │ • inputs.ping (infrastructure health)                │   │
│  │ • inputs.execd (CDN pinging, fault analysis)         │   │
│  └──────────┬──────────────────────────────────────────┘   │
│             │                                               │
│             ▼                                               │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ InfluxDB 2.7 (Single Source of Truth)               │   │
│  │ • Bucket: network                                    │   │
│  │ • All metrics stored here                            │   │
│  └──────────┬──────────────────────────────────────────┘   │
│             │                                               │
│             ▼                                               │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ Grafana (Visualization)                              │   │
│  │ • Data source: InfluxDB (Flux queries)               │   │
│  │ • Dashboards for infrastructure, streaming, devices  │   │
│  └─────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

**Key Point:** prometheus-node-exporter-lua is just a **metrics exporter** (like a JSON API). It exposes router stats in Prometheus format via HTTP. Telegraf scrapes this endpoint and stores the data in InfluxDB. We do NOT use Prometheus server or database.

## Stack

- **Router:** OpenWrt GL-MT2500A (192.168.1.2) - Lightweight data collection
- **Collector:** Telegraf - Scrapes, receives, and processes metrics
- **Database:** InfluxDB 2.7 (192.168.1.126:8086) - Time-series storage (single source of truth)
- **Visualization:** Grafana - Dashboard UI with Flux queries

## Data Collection Methods

### Currently Active ✅

#### 1. Bandwidth Tracking (Router Cron)

**Script:** `/root/bin/send-bandwidth-to-influx.sh`
**Method:** Query nlbwmon database → calculate deltas → send via UDP
**Frequency:** Every 60 seconds (cron)
**Router CPU:** <1%
**Data:** `bandwidth,device_name=X,ip=Y,mac=Z,protocol=HTTPS,direction=rx bytes=1048576i timestamp`

#### 2. Infrastructure Health (Mac Mini)

**Method:** Telegraf inputs.ping
**Targets:** Routers (192.168.1.2, 192.168.2.1), Starlink Dishy (192.168.100.1), WAN (8.8.8.8, 1.1.1.1)
**Frequency:** 10-30 seconds
**Data:** Latency, packet loss, availability

#### 3. CDN Monitoring - Opportunistic (Mac Mini)

**Script:** `scripts/streaming-ping-orchestrator.py`
**Method:** Query InfluxDB for streaming activity → conditionally ping CDN hosts
**Frequency:** Every 30 seconds (only when streaming detected)
**Data:** CDN latency to Netflix, YouTube, Amazon, Cloudflare

### Planned Additions 🔄

#### 4. Router Health Monitoring

**Method:** prometheus-node-exporter-lua on router → Telegraf inputs.prometheus
**Endpoint:** http://192.168.1.2:9100/metrics
**Frequency:** Every 60 seconds
**Router CPU:** 2-5%
**Data:** Router CPU, memory, interface stats, uptime

#### 5. DNS Query Logging

**Method:** dnsmasq query logging → syslog → Telegraf inputs.syslog
**Frequency:** Real-time (every DNS query)
**Router CPU:** <1%
**Data:** DNS queries per device, query types, domains accessed

### Disabled (Previous CPU Overload) ❌

The following scripts were disabled due to causing 90% router CPU usage:

- `/root/bin/dns-monitor-daemon.sh` - Real-time DNS parsing (duplicate of dnsmasq logging)
- `/root/bin/stream-dns-events.sh` - Duplicate DNS monitoring
- `/root/bin/connections-monitor-daemon.sh` - Connection state tracking
- `/root/bin/monitor-connection-flows.sh` - Connection flow details with reverse DNS
- netifyd service - Deep packet inspection (341MB RAM, 15-25% CPU)

These are replaced by lightweight alternatives (syslog for DNS, inference for connections).

## Dashboard Panels (All InfluxDB)

### Bandwidth Monitoring

1. **Top 10 Bandwidth (Download)** - Table with LCD gauge, device name first
2. **Top 10 Bandwidth (Upload)** - Table with LCD gauge, device name first
3. **Bandwidth Over Time (Download)** - Time series with security-focused scoring

### DNS & Network Activity

4. **Top DNS Clients** - Event count per device
5. **Unique Domains** - distinct() domains per device
6. **Protocol Distribution** - Pie chart by protocol tag
7. **Activity Table** - 4-query merge: bandwidth + connections + DNS, device name first

### Connection Analysis

8. **Connection Count** - Time series by device with security scoring
9. **Top Domains** - Event count per domain (drill-down enabled)

### Advanced Correlation

10. **Domain-Device Drill-Down** - Cross-correlation for security investigations
11. **Upload Bandwidth Over Time** - Time series companion to Panel 3

All queries use Flux, respect time-range selection, query in <500ms.

## Performance

- Router CPU: ~5-7% average
- Network: ~15-30 KB/s to InfluxDB
- InfluxDB writes: 50-200/minute
- Storage: ~1.7 GB/day (~620 GB/year compressed)

## Key Features

✅ Real-time DNS query visibility
✅ Time-range filtering works (was broken in Prometheus)
✅ Event-based model (proper unique counts, drill-downs)
✅ Single database (no Prometheus/InfluxDB hybrid)
✅ Device name resolution via `/root/bin/resolve-device-name.sh`
