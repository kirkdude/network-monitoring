# Network Monitoring Stack

Pure InfluxDB event-based monitoring for home network with real-time data collection.

> **Note:** This project uses **Podman** (not Docker). All commands use `podman-compose` instead of `docker-compose`.

## Architecture

**Pure InfluxDB Stack** - No Prometheus server. We migrated from Prometheus to InfluxDB to fix time-range filtering issues.

```
Router (GL-MT2500A @ 192.168.1.2)      Mac Mini (192.168.1.126)
=====================================   ================================
Lightweight Data Export:                Data Processing Hub:

• nlbwmon (bandwidth)  ──UDP:8094───► Telegraf (Collector)
• dnsmasq (DNS)        ──syslog────►    │
• node-exporter        ──HTTP:9100─►    │
  (router health)                        ├──► InfluxDB 2.7 ──► Grafana
                                        │     (single source
Infrastructure pings  ◄────────────────┘      of truth)
CDN monitoring        ◄────────────────┘
```

### Stack Components

- **InfluxDB 2.7**: Time-series database (Pure InfluxDB, single source of truth)
- **Telegraf**: Collector (UDP listener, HTTP scraper, ping monitor, exec scripts)
- **Grafana**: Visualization dashboards (Flux queries)
- **Router Exports**: Lightweight data collection (bandwidth via UDP, health via HTTP)

## Quick Start

### Start Services

```bash
cd ~/src/network-monitoring
podman-compose up -d
podman-compose ps
```

### Access Services

| Service | Port | URL | Credentials |
|---------|------|-----|-------------|
| Grafana | 3000 | <http://localhost:3000> | admin / changeme123 |
| InfluxDB | 8086 | <http://localhost:8086> | admin / changeme123 |

### View Dashboards

1. Open Grafana: <http://localhost:3000>
2. Navigate to **Dashboards** → **Client Monitoring**
3. Select time range (1h, 6h, 24h, 7d, 30d)
4. All panels update in real-time with proper time-range filtering

## Data Sources

### Currently Active ✅

#### Bandwidth Tracking (Router → Mac Mini)

- **Script:** `/root/bin/send-bandwidth-to-influx.sh` (cron every 60s)
- **Method:** Query nlbwmon → send via UDP:8094
- **Router CPU:** <1%
- **Data:** Per-device, per-protocol bandwidth

#### Infrastructure Health (Mac Mini)

- **Method:** Telegraf inputs.ping
- **Targets:** Routers, Starlink Dishy, WAN (8.8.8.8, 1.1.1.1)
- **Frequency:** 10-30 seconds

#### CDN Monitoring (Mac Mini)

- **Script:** `scripts/streaming-ping-orchestrator.py`
- **Method:** Opportunistic pinging when streaming detected
- **Frequency:** Every 30 seconds

### Planned Additions 🔄

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for planned additions:
- Router health monitoring (prometheus-node-exporter-lua)
- DNS query logging (dnsmasq syslog)
- Streaming fault diagnosis

### Disabled (Previous CPU Overload) ❌

The following router-side scripts were disabled due to causing 90% CPU usage:
- `dns-monitor-daemon.sh` - Real-time DNS parsing
- `connections-monitor-daemon.sh` - Connection state tracking
- `monitor-connection-flows.sh` - Connection flow details
- netifyd service - Deep packet inspection (341MB RAM)

## Dashboards

### Client Monitoring Dashboard (11 panels)

All panels use InfluxDB with Flux queries and real-time data visualization:

#### Bandwidth Monitoring

1. **Top 10 Bandwidth (Download)** - Table with LCD gauge, device name first
2. **Top 10 Bandwidth (Upload)** - Table with LCD gauge, device name first
3. **Bandwidth Over Time (Download)** - Time series with security-focused scoring algorithm

#### DNS & Network Activity

4. **Top DNS Clients** - Query count (time-range aware ✅)
5. **Unique Domains** - Distinct domains per client (time-range aware ✅)
6. **Protocol Distribution** - HTTPS, QUIC, DNS, etc. (pie chart)
7. **Client Activity Table** - Bandwidth + Connections + DNS per device, device name first

#### Connection Analysis

8. **Connection Count** - Time series by client with security scoring
9. **Top Domains** - Most accessed domains (drill-down enabled ✅)

#### Advanced Correlation

10. **Domain-Device Drill-Down** - Cross-correlation for security investigations
11. **Upload Bandwidth Over Time** - Time series companion to Panel 3 with same scoring algorithm

**Performance:** All queries <500ms

### Device Detail Dashboard

Drill-down from Client Monitoring for per-device analysis.

## Device Registry

Device names resolved via `/root/bin/resolve-device-name.sh` on router.

See `docs/DEVICE-REGISTRY-GUIDE.md` for management.

## Architecture Details

See `docs/ARCHITECTURE.md` for:

- Data collection methods
- InfluxDB line protocol formats
- Query patterns
- Performance metrics

## Key Features

✅ **Real-time events** - DNS queries appear instantly
✅ **Time-range filtering** - All panels respect selected time range
✅ **Event-based model** - Proper unique counts, drill-downs
✅ **Single database** - Pure InfluxDB (no Prometheus hybrid)
✅ **Auto-restart** - Daemons managed by procd
✅ **Low overhead** - ~5-7% router CPU, <30 KB/s network

## Troubleshooting

### No data in dashboard

```bash
# Check InfluxDB
podman exec influxdb influx query 'from(bucket: "network") |> range(start: -5m) |> count()' --org home

# Check Telegraf
podman logs --tail 50 telegraf

# Check router daemons
ssh root@192.168.1.2 "/etc/init.d/influxdb-monitors status"
```

### High router CPU

Adjust connection sampling interval:

```bash
# Edit /root/bin/connections-monitor-daemon.sh
INTERVAL=60  # Increase from 30 to 60 seconds
```

## Storage

- **Event volume:** ~50-200 writes/minute
- **Storage rate:** ~1.7 GB/day (~620 GB/year compressed)
- **Retention:** 365 days (configurable in InfluxDB)

## Migration Notes

This system was migrated from Prometheus to Pure InfluxDB to fix time-range filtering issues in DNS panels. All Prometheus components have been removed.

**Backup:** `grafana-dashboards/client-monitoring-prometheus-backup.json`
