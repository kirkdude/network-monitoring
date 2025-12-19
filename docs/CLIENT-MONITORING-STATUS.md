# Client Monitoring Status Report
**Date:** 2025-12-19
**Status:** Ready to implement comprehensive client monitoring

---

## Current State Assessment ✅

### What's Already Working

#### 1. nlbwmon (Bandwidth Monitoring) ✅ **OPERATIONAL**
- **Status:** Running and collecting data
- **Database:** `/var/lib/nlbwmon/`
- **Refresh Interval:** 30 seconds
- **Commit Interval:** 24 hours
- **Data Retention:** 10 generations (10 days)

**Currently Tracking:**
- Per-device bandwidth (download/upload)
- Protocol breakdown (HTTPS, QUIC, HTTP, DNS, etc.)
- Connection counts per device
- Packet counts per device
- Layer 7 application identification

**Active Devices Found:** 90+ clients on the network

**Sample Data:**
```
IPv4    192.168.1.109 (80:f5:05)  QUIC       315      3.61 GB (2.78 M)   236.78 MB (1.49 M)
IPv4    192.168.1.171 (a0:66:2b)  other      309      1.53 GB (1.20 M)    57.36 MB (287.20 K)
IPv4    192.168.1.190 (64:cc:4d)  QUIC       968    330.03 MB (274.24 K)   5.08 MB (15.73 K)
```

#### 2. AdGuard Home Query Logging ✅ **OPERATIONAL**
- **Status:** Enabled and logging to file
- **Log File:** `/root/adguard-logs/querylog.json` (25.6 MB)
- **Interval:** 24 hour rotation
- **Memory Buffer:** 1000 queries

**Data Available:**
- DNS queries per client IP
- Domains accessed by each device
- Query timestamps (precise to microseconds)
- Query types (A, AAAA, PTR, etc.)
- Upstream DNS servers used
- Query response times

**Sample Entry:**
```json
{
  "T": "2025-12-19T15:57:49.092815857-07:00",
  "QH": "rdz-rbcloud.rainbird.com",
  "QT": "A",
  "IP": "192.168.1.X",
  "Upstream": "1.1.1.3:53",
  "Elapsed": 26359358
}
```

#### 3. DHCP Client Database ✅ **OPERATIONAL**
- **Lease File:** `/tmp/dhcp.leases` (90 active leases)
- **Client DB:** `/etc/oui-tertf/client.db` (SQLite database)
- **Static Reservations:** 12 configured

**Available Data:**
- MAC address to IP mappings
- Hostname identification
- Lease times
- Device vendor information (via OUI lookup)

---

## What You Can Monitor Now

### Per-Device Visibility
For **each client** on your network, you can track:

1. **Bandwidth Usage**
   - Total download/upload volumes
   - Rates over time
   - Protocol breakdown (HTTPS, QUIC, HTTP, DNS, mDNS, etc.)
   - Application-level traffic (Netflix, YouTube, Apple services, etc.)

2. **Connection Activity**
   - Number of active connections
   - Connection patterns over time
   - Most frequent connection protocols

3. **DNS Queries (Where They're Connecting)**
   - Every domain accessed
   - Query frequency per domain
   - Time of day patterns
   - Blocked vs. allowed queries

4. **Device Identification**
   - IP address
   - MAC address
   - Hostname (when available)
   - Vendor identification

---

## Top Bandwidth Users (Current Period)

| Rank | IP | MAC | Download | Upload | Connections | Primary Protocol |
|------|-------|---------|----------|--------|-------------|------------------|
| 1 | 192.168.1.109 | 80:f5:05 | 3.61 GB | 236.78 MB | 315 | QUIC |
| 2 | 192.168.1.171 | a0:66:2b | 1.53 GB | 57.36 MB | 309 | other |
| 3 | 192.168.1.190 | 64:cc:4d | 330.03 MB | 5.08 MB | 968 | QUIC |
| 4 | 192.168.1.34 | 65:22:41 | 244.36 MB | 54.42 MB | 4.62K | HTTPS |
| 5 | 192.168.1.126 | 22:74:9c | 135.23 MB | 21.51 MB | 7.47K | HTTPS |

---

## What Needs to Be Built

To expose this data in Grafana and daily reports, we need:

### 1. Router Export Scripts
- **nlbwmon JSON exporter** - Convert nlbwmon data to Prometheus-compatible format
- **AdGuard DNS query aggregator** - Parse and aggregate DNS queries per client
- **Combined client metrics exporter** - Merge bandwidth + DNS + DHCP data

### 2. Prometheus Integration
- New scrape job for client metrics endpoint
- Custom metrics format:
  - `client_bandwidth_bytes{ip="X.X.X.X", mac="XX:XX:XX", direction="rx|tx"}`
  - `client_connections_total{ip="X.X.X.X", protocol="https|quic|dns"}`
  - `client_dns_queries_total{ip="X.X.X.X", domain="example.com", result="allowed|blocked"}`

### 3. Grafana Dashboard
- Per-client bandwidth graphs
- Top talkers table
- DNS query heatmap by client
- Protocol distribution pie charts
- Client activity timeline
- Top domains per client

### 4. Daily Reports
- Client activity summaries
- Bandwidth rankings
- Unusual activity detection
- New device notifications
- Top domains per client

---

## Implementation Plan

### Phase 3A: Data Export Layer (2-3 hours)

**Task 1: Build nlbwmon exporter script** (1 hour)
- Parse `nlbw -c show` output
- Convert to structured JSON
- Include client identification (IP, MAC, hostname)
- Export as Prometheus metrics format

**Task 2: Build AdGuard DNS aggregator** (1 hour)
- Parse `/root/adguard-logs/querylog.json`
- Aggregate queries per client IP
- Count queries per domain
- Track blocked vs. allowed
- Export metrics

**Task 3: Combine and expose metrics** (30 min)
- Create unified client metrics endpoint
- Serve on router port (e.g., 9101)
- Update every 30 seconds to match nlbwmon refresh

### Phase 3B: Prometheus & Grafana (1-2 hours)

**Task 4: Configure Prometheus scraping** (15 min)
- Add new scrape job to `prometheus.yml`
- Target: `192.168.1.2:9101`
- Scrape interval: 30s

**Task 5: Create Grafana dashboard** (1 hour)
- Import/adapt existing network monitoring dashboards
- Add per-client panels:
  - Bandwidth time series by client
  - Top talkers table (sortable by download/upload)
  - Protocol distribution stacked area chart
  - DNS queries per client bar chart
  - Connection count heat map
  - Client device table with identification

**Task 6: Test and refine** (30 min)
- Verify all metrics flowing
- Check dashboard responsiveness
- Tune refresh rates
- Fix any data mapping issues

### Phase 3C: Reporting & Automation (2-3 hours)

**Task 7: Daily client report generator** (2 hours)
- Parse client metrics from Prometheus
- Generate markdown report with:
  - Top bandwidth users
  - Most active devices
  - Unusual activity alerts
  - New devices detected
  - Top domains per client
  - Protocol usage breakdown

**Task 8: Integrate with daily-status** (30 min)
- Add client monitoring section
- Show top 5 clients by bandwidth
- Flag any anomalies
- Link to full report

**Task 9: Set up alerting** (30 min)
- Alert on new devices
- Alert on excessive bandwidth
- Alert on unusual connection patterns
- Alert on connections to suspicious domains

---

## Success Criteria

When complete, you will have:

✅ Real-time per-client bandwidth tracking
✅ DNS query visibility for every device
✅ Connection tracking per client
✅ Historical data for all clients (1 year retention)
✅ Grafana dashboard with:
  - Live bandwidth graphs per client
  - Top talkers identification
  - Protocol breakdowns
  - DNS query analytics
  - Client identification table
✅ Daily reports showing:
  - Which devices used the most bandwidth
  - What domains each device accessed
  - How many connections each device made
  - Any unusual activity patterns
✅ Automated alerting for anomalies

---

## Example Questions You'll Be Able to Answer

- "Which device downloaded the most data yesterday?"
- "What websites is the LG TV trying to reach?"
- "How many connections is my iPhone making per hour?"
- "Which device is using the most QUIC traffic?"
- "What domains is IP 192.168.1.109 accessing?"
- "Has any new device joined the network?"
- "Which clients are the noisiest?"
- "What's the bandwidth usage of MAC 80:f5:05 over the past week?"

---

## Technical Architecture

```
┌─────────────────────────────────────────────────────────────┐
│ Router (192.168.1.2)                                        │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐  │
│  │ Data Collectors                                       │  │
│  │  - nlbwmon (bandwidth per client)                    │  │
│  │  - AdGuard Home (DNS queries per client)             │  │
│  │  - DHCP leases (client identification)               │  │
│  │  - Client DB (MAC vendor lookup)                     │  │
│  └──────────────┬───────────────────────────────────────┘  │
│                 │                                            │
│                 ▼                                            │
│  ┌──────────────────────────────────────────────────────┐  │
│  │ Export Scripts (NEW)                                  │  │
│  │  - nlbwmon JSON exporter                             │  │
│  │  - AdGuard DNS aggregator                            │  │
│  │  - Combined metrics endpoint                         │  │
│  │  - Port 9101 (Prometheus format)                     │  │
│  └──────────────┬───────────────────────────────────────┘  │
└─────────────────┼───────────────────────────────────────────┘
                  │ HTTP scrape every 30s
                  ▼
┌─────────────────────────────────────────────────────────────┐
│ Mac Mini (Monitoring Server)                                │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐  │
│  │ Prometheus                                            │  │
│  │  - Scrapes router port 9100 (system metrics)         │  │
│  │  - Scrapes router port 9101 (client metrics) ◄─ NEW  │  │
│  │  - 1 year retention                                   │  │
│  │  - Evaluates alerting rules                          │  │
│  └──────────────┬───────────────────────────────────────┘  │
│                 │                                            │
│                 ▼                                            │
│  ┌──────────────────────────────────────────────────────┐  │
│  │ Grafana                                               │  │
│  │  - Router health dashboard (existing)                │  │
│  │  - Client monitoring dashboard ◄─ NEW                │  │
│  │  - Per-device graphs and tables                      │  │
│  │  - DNS query analytics                               │  │
│  └─────────────────────────────────────────────────────┘  │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐  │
│  │ Daily Reports ◄─ NEW                                  │  │
│  │  - Client activity summaries                          │  │
│  │  - Bandwidth rankings                                 │  │
│  │  - Top domains per client                            │  │
│  │  - Anomaly detection                                  │  │
│  └──────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

---

## Next Steps

**Ready to proceed?** Say "yes" and I'll start building:

1. **nlbwmon JSON exporter script** on the router
2. **AdGuard DNS aggregator script** on the router
3. **Combined metrics HTTP endpoint** exposing client data
4. **Prometheus configuration** to scrape the new endpoint
5. **Grafana dashboard** for comprehensive client monitoring
6. **Daily report generator** with client activity summaries

**Total implementation time:** 4-6 hours
**Result:** Complete visibility into every device on your network

---

**Current Phase:** Phase 2 Complete ✅
**Next Phase:** Phase 3A - Client Monitoring Implementation
**Data Sources:** All operational and collecting data ✅
**Ready to Build:** YES ✅
