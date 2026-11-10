# Router Monitoring Scripts Analysis

**Date:** 2026-01-04
**Issue:** Catastrophic network failures caused by monitoring overload
**Root Cause:** Router CPU exhaustion from inefficient monitoring scripts

---

## The Problem

The GL-MT2500A router was running **8 concurrent monitoring scripts** that caused:
- **90% CPU utilization** (0% idle)
- **Load average: 3.24** on a 2-core CPU
- **2,242 DNS timeout failures** per domain in 30 days
- Complete network outages (all eero devices going red)

---

## Script Inventory & Goals

### 1. **send-dpi-flows-to-influx.sh** (DPI Flow Streaming)
**Goal:** Track application-level traffic per device (Netflix, YouTube, etc.)

**Data Collected:**
- Device IP/MAC/name
- Application name (e.g., "netflix", "youtube")
- Protocol
- Byte counts per flow

**Method:**
- Reads from netifyd socket (continuous stream)
- For EACH flow event:
  - Runs `conntrack -L` (dumps entire connection table)
  - Spawns grep/head/cut to parse
  - Calls `resolve-device-name.sh`
  - Sends UDP packet to InfluxDB

**Frequency:** Real-time (hundreds of events per second during activity)

**CPU Impact:** 🔴 **CRITICAL** - `conntrack -L` on every flow event

---

### 2. **dns-monitor-daemon.sh** (DNS Query Logging - Version 1)
**Goal:** Track DNS queries per device

**Data Collected:**
- Device IP/MAC/name
- Domain queried
- Query type (A, AAAA, MX, etc.)

**Method:**
- Tails `/var/log/dnsmasq.log`
- Parses each line with shell string manipulation
- Looks up device name
- Sends to InfluxDB

**Frequency:** Real-time (every DNS query)

**CPU Impact:** 🟡 **MODERATE**

---

### 3. **stream-dns-events.sh** (DNS Query Logging - Version 2)
**Goal:** IDENTICAL to dns-monitor-daemon.sh

**Data Collected:** *Exactly the same as #2*

**Method:**
- Tails `/var/log/dnsmasq.log` (again)
- Parses with `jq` instead of shell
- Sends to InfluxDB

**Frequency:** Real-time (every DNS query)

**OVERLAP:** 🔴 **100% DUPLICATE** - Same log file, same data, different parser

**CPU Impact:** 🟡 **MODERATE** - jq is expensive on embedded devices

---

### 4. **connections-monitor-daemon.sh** (Connection State Tracking)
**Goal:** Track TCP/UDP connection states per device

**Data Collected:**
- Device IP/MAC/name
- Protocol (TCP/UDP/ICMP)
- Connection state (ESTABLISHED, TIME_WAIT, CLOSE_WAIT, etc.)
- Count of connections in each state

**Method:**
- Runs `conntrack -L` every 30 seconds
- Aggregates by device/protocol/state
- Sends counters to InfluxDB

**Frequency:** Every 30 seconds

**OVERLAP:** 🟡 **50%** - Conntrack data already available from #1 and #5

**CPU Impact:** 🟡 **MODERATE** - `conntrack -L` dumps entire table

---

### 5. **monitor-connection-flows.sh** (Connection Flow Details)
**Goal:** Track individual active connections with hostnames

**Data Collected:**
- Source IP → Destination IP
- Source port → Destination port
- Hostname (reverse DNS of destination)
- Protocol
- Bytes transferred

**Method:**
- Runs `conntrack -L` continuously
- Performs reverse DNS lookup for each destination
- Caches results in `/tmp/dns_cache.txt`
- Sends to InfluxDB

**Frequency:** Continuous loop

**OVERLAP:** 🔴 **80% DUPLICATE** - Same conntrack data as #4, adds expensive DNS lookups

**CPU Impact:** 🔴 **HIGH** - Continuous `conntrack -L` + reverse DNS

---

### 6. **router-stats-daemon.sh** (Router Resource Monitoring)
**Goal:** Track router CPU, memory, and WAN interface health

**Data Collected:**
- CPU usage (user/system/idle percentages)
- Memory usage (total/free/cached/buffers)
- WAN throughput (rx/tx bytes and packets)
- WAN error/drop counters

**Method:**
- Reads `/proc/stat` for CPU
- Reads `/proc/meminfo` for memory
- Reads `/sys/class/net/eth0/statistics/*` for WAN stats
- Calculates rates from deltas

**Frequency:** Every 60 seconds

**OVERLAP:** 🟢 **UNIQUE** - No other script provides router health metrics

**CPU Impact:** 🟢 **LOW** - Simple file reads

---

### 7. **throttle-detector.sh** (Bandwidth Anomaly Detection)
**Goal:** Detect ISP bandwidth throttling

**Data Collected:**
- WAN throughput (rolling average over 60 seconds)
- Throttle alert events (when bandwidth drops >50%)

**Method:**
- Reads `/sys/class/net/eth0/statistics` every 10 seconds
- Maintains rolling window of 6 samples
- Compares current to baseline
- Sends alerts to InfluxDB

**Frequency:** Every 10 seconds

**OVERLAP:** 🟡 **70%** - WAN stats already collected by #6, just adds detection logic

**CPU Impact:** 🟢 **LOW** - Simple file reads and math

---

### 8. **send-bandwidth-to-influx.sh** (Per-Device Bandwidth - KEPT)
**Goal:** Track upload/download bytes per device

**Data Collected:**
- Device IP/MAC/name
- Protocol
- Upload/download bytes (deltas between runs)

**Method:**
- Runs `nlbw -c show` (efficient, kernel-maintained)
- Calculates deltas from previous state
- Sends only changes to InfluxDB

**Frequency:** Every 60 seconds (cron)

**OVERLAP:** 🟢 **UNIQUE** - Only source of per-device bandwidth

**CPU Impact:** 🟢 **LOW** - nlbwmon is efficient

---

### 9. **netifyd** (DPI Engine Service)
**Goal:** Provide Deep Packet Inspection data source

**Data Collected:**
- Application detection (HTTP Host headers, TLS SNI, etc.)
- Protocol classification
- Flow metadata

**Method:**
- Kernel packet inspection
- libnetfilter_conntrack integration
- Maintains Unix socket for clients

**Frequency:** Continuous

**Resource Usage:**
- **341MB RAM** (34% of 1GB)
- Significant CPU during traffic bursts

**CPU Impact:** 🔴 **HIGH** - Real-time packet inspection

---

## Overlap Summary

| Script | Unique Data? | Overlaps With | Redundancy |
|--------|--------------|---------------|------------|
| 1. send-dpi-flows | ✅ Yes (app detection) | #5 (conntrack) | Medium |
| 2. dns-monitor-daemon | ✅ Yes (DNS queries) | #3 (100% duplicate) | **CRITICAL** |
| 3. stream-dns-events | ❌ No | #2 (100% duplicate) | **CRITICAL** |
| 4. connections-monitor | ⚠️ Partial | #1, #5 (conntrack) | High |
| 5. monitor-connection-flows | ⚠️ Partial | #1, #4 (conntrack) | High |
| 6. router-stats | ✅ Yes (router health) | #7 (WAN stats) | Low |
| 7. throttle-detector | ⚠️ Partial | #6 (WAN stats) | Medium |
| 8. send-bandwidth *(kept)* | ✅ Yes (per-device BW) | None | None |
| 9. netifyd | ✅ Yes (DPI engine) | None | None |

---

## Inefficiencies Identified

### 🔴 Critical Issues

1. **Duplicate DNS Monitoring**
   - Scripts #2 and #3 do EXACTLY the same thing
   - Both tail the same log file
   - Both send the same data to InfluxDB
   - **Impact:** 2x CPU waste, 2x network packets

2. **Triple Conntrack Querying**
   - Scripts #1, #4, and #5 all run `conntrack -L`
   - Each dumps the ENTIRE connection table (could be 1000+ entries)
   - Script #1 does it on EVERY flow event (hundreds/sec)
   - **Impact:** Catastrophic CPU waste

3. **Real-time vs Batch Processing**
   - Scripts process events one-by-one in real-time
   - No batching, no rate limiting
   - Each event spawns multiple processes (grep, awk, cut, jq)
   - **Impact:** CPU thrashing, context switching overhead

### 🟡 Major Issues

4. **Expensive DNS Lookups**
   - Script #5 does reverse DNS for every connection
   - Even with caching, creates DNS query storms
   - Blocks on slow DNS responses
   - **Impact:** CPU + network overhead

5. **Inefficient Parsing**
   - Shell string manipulation (slow)
   - jq for simple field extraction (overkill on embedded)
   - Multiple pipes per event
   - **Impact:** High CPU per event

6. **Log File Tailing**
   - dnsmasq logging disabled now, but was writing to disk constantly
   - Multiple `tail -F` processes reading same file
   - **Impact:** Disk I/O + CPU

---

## Proposed Consolidated Goals

### Core Monitoring Needs

1. **Device Network Usage** *(what are my devices doing?)*
   - Per-device bandwidth (upload/download)
   - Active connections count
   - Top applications (Netflix, YouTube, etc.)
   - **Current:** #1, #8 ✅ (keep #8, optimize #1)

2. **DNS Activity** *(what sites are being accessed?)*
   - DNS queries per device
   - Top domains
   - Query types
   - **Current:** #2, #3 (consolidate to one)

3. **Connection Health** *(are connections healthy?)*
   - Connection states per device
   - Failed connections
   - Connection duration
   - **Current:** #4, #5 (consolidate)

4. **Router Health** *(is the router overloaded?)*
   - CPU/memory usage
   - WAN throughput
   - Interface errors
   - **Current:** #6 ✅ (keep)

5. **Anomaly Detection** *(what's wrong?)*
   - Bandwidth throttling
   - High latency
   - DNS failures
   - **Current:** #7 (integrate into Grafana alerts)

---

## Recommended Efficient Solution

### Option A: Move Heavy Lifting Off-Router

**Best for:** Comprehensive monitoring without router impact

**Architecture:**
```
Router (GL-MT2500A)
  ├─ Send DNS via UDP (dnsmasq feature)
  ├─ Export prometheus-node-exporter metrics (HTTP)
  └─ Keep nlbwmon for per-device bandwidth

Mac Mini / Pi / NUC
  ├─ Telegraf scrapes router metrics
  ├─ Receives DNS events via UDP
  ├─ ntopng for DPI (span port or inline)
  └─ Processes/aggregates → InfluxDB
```

**Benefits:**
- Router only does lightweight exports
- Heavy processing on powerful hardware
- Full DPI without router impact

---

### Option B: Efficient On-Router Scripts

**Best for:** Keeping everything on router with minimal impact

**Consolidated Scripts:**

1. **network-monitor.sh** (runs every 30s)
   - Single `conntrack -L` call
   - Aggregates: connections per device, states, protocols
   - Calculates: new connections, closed connections
   - Batch sends to InfluxDB

2. **dns-collector.sh** (batching)
   - Uses dnsmasq's UDP export feature (--log-queries=extra)
   - Receives via netcat/socat
   - Batches 10 seconds of queries
   - Sends aggregate counts to InfluxDB

3. **router-health.sh** (runs every 60s) *(keep existing)*
   - CPU, memory, WAN stats
   - Lightweight file reads

4. **bandwidth-tracker.sh** (runs every 60s via cron) *(keep existing)*
   - Per-device bandwidth via nlbwmon

**DPI Options:**
- **Disable netifyd** - Saves 341MB RAM, huge CPU
- **Alternative:** Use ntopng on Mac Mini with port mirroring

**Estimated Impact:**
- CPU: <10% average, <30% peak
- Memory: ~50MB for scripts
- Network: 1-2 packets/second to InfluxDB

---

### Option C: Hybrid Approach

**Best for:** Balance between monitoring detail and router impact

**On Router:**
- Lightweight metrics (bandwidth, DNS counts, connection counts)
- Batch processing every 30-60 seconds
- No DPI

**Off Router (ntopng on Mac Mini):**
- Deep packet inspection
- Application detection
- Flow analysis
- Uses existing interface monitoring

---

## Implementation Recommendations

### Phase 1: Immediate (Done ✅)
- ✅ Disabled all monitoring scripts
- ✅ Stopped netifyd service
- ✅ Router CPU recovered (0% → 95% idle)
- ✅ DNS working
- ✅ Network stable

### Phase 2: Restore Essential Monitoring
1. Keep `send-bandwidth-to-influx.sh` (cron, already efficient)
2. Implement consolidated `network-monitor.sh` (30s batch)
3. Keep `router-stats-daemon.sh` (60s, lightweight)

### Phase 3: Optional DPI
- Set up ntopng on Mac Mini (you already have docker-compose entry)
- Configure interface monitoring on `en0`
- No router impact

### Phase 4: Advanced Features
- Implement alerting in Grafana (replaces throttle detector)
- DNS analytics from batch data
- Connection anomaly detection

---

## Lessons Learned

1. **Monitor the monitors** - Monitoring overhead was worse than the problems being monitored
2. **Batch over real-time** - Real-time is rarely needed, causes CPU thrashing
3. **One source of truth** - Multiple scripts reading same data (conntrack, logs) = waste
4. **Right tool for the job** - Embedded routers shouldn't do DPI while routing
5. **Start simple** - Add complexity only when proven necessary

---

## Questions for Next Steps

1. **What monitoring do you actually use?**
   - Which dashboards do you look at regularly?
   - What alerts do you need?

2. **DPI requirements?**
   - Do you need per-application tracking?
   - Or is per-device bandwidth enough?

3. **Historical data?**
   - How far back do you need data?
   - Can we reduce retention for high-frequency metrics?

4. **Preferred solution?**
   - Option A: Move to Mac Mini (best)
   - Option B: Efficient on-router (good)
   - Option C: Hybrid (balanced)
