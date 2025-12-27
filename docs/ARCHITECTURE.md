# Network Monitoring Architecture

Pure InfluxDB event-based monitoring for home network with real-time data collection.

## Stack

- **Router:** OpenWrt (192.168.1.2) - Data collection
- **Database:** InfluxDB 2.7 (192.168.1.126:8086) - Time-series storage
- **Ingestion:** Telegraf (UDP:8094) - Line protocol receiver
- **Visualization:** Grafana - Dashboard UI

## Data Collection (Router)

### DNS Queries - Real-time Daemon

**Script:** `/root/bin/dns-monitor-daemon.sh`
**Method:** `tail -F /var/log/dnsmasq.log` → parse → send immediately
**Data:** `dns_query,device_name=X,ip=Y,mac=Z,query_type=A domain="github.com" timestamp`

### Connections - 30s Sampling Daemon

**Script:** `/root/bin/connections-monitor-daemon.sh`
**Method:** `conntrack -L` every 30s → aggregate → send
**Data:** `connection_state,device_name=X,ip=Y,mac=Z,proto=tcp,state=ESTABLISHED count=42i timestamp`

### Bandwidth - 60s Cron

**Script:** `/root/bin/send-bandwidth-to-influx.sh`
**Method:** Query nlbwmon database → calculate deltas → send
**Data:** `bandwidth,device_name=X,ip=Y,mac=Z,protocol=HTTPS,direction=rx bytes=1048576i timestamp`

### Process Management

```bash
/etc/init.d/influxdb-monitors start|stop|restart
```

Daemons managed by procd (auto-restart on crash, boot persistence).

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
