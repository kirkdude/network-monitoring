# Panel 8: Connection Count by Client

## Panel Overview

- **Panel ID:** 8
- **Title:** Connection Count by Client (Top ${top_n})
- **Type:** Time Series (Line Graph)
- **Grid Position:** x=0, y=34, width=12, height=8 (left half of fifth row)
- **Purpose:** Shows the top N clients by active connection count over time

## Critical Updates (2025-12-26)

1. **Added top_n variable support** - respects dashboard selector (5-50 devices)
2. **Uses security-focused scoring** - same algorithm as Panels 3 & 11
3. **Fixed single device bug** - added `group()` before `findColumn()`

**Working Query Pattern:**

```flux
selectedDevices = from(bucket: "network")
  |> range(start: v.timeRangeStart, stop: v.timeRangeStop)
  |> filter(fn: (r) => r._measurement == "bandwidth")  // Uses bandwidth for scoring
  |> drop(columns: ["_time"])
  |> group(columns: ["device_name", "direction"])
  |> sum()
  |> pivot(rowKey: ["device_name"], columnKey: ["direction"], valueColumn: "_value")
  |> map(fn: (r) => ({...calculate score...}))
  |> group()  // CRITICAL: Ungroup before findColumn
  |> sort(columns: ["score"], desc: true)
  |> limit(n: ${top_n})
  |> findColumn(fn: (key) => true, column: "device_name")

from(bucket: "network")
  |> range(start: v.timeRangeStart, stop: v.timeRangeStop)
  |> filter(fn: (r) => r._measurement == "connection_state")
  |> filter(fn: (r) => contains(value: r.device_name, set: selectedDevices))
  |> group(columns: ["device_name"])
  |> aggregateWindow(every: v.windowPeriod, fn: sum, createEmpty: false)
```

**Key Feature:** Shows connection trends for the SAME devices selected in bandwidth panels (Panels 3 & 11), enabling correlation:

- High bandwidth + High connections = Normal heavy usage
- Low bandwidth + High connections = 🚨 Port scanning, C2 beaconing

## Data Source

### Prometheus Query

```promql
topk(10, sum by (device_name) (client_connections_total))
```

### Metrics Used

- `client_connections_total` - Number of active TCP/UDP connections per client
  - Labels: `device_name`, `ip`
  - Type: Gauge (current count of active connections)

### Data Collection Flow

1. **Router (GL-MT2500A):** Tracks active connections via netstat/conntrack
2. **Export Script:** Connection data collected as part of router metrics export
3. **Lua Collector:** Exports connection counts on port 9100
4. **Prometheus:** Scrapes router:9100 every 30 seconds
5. **Grafana:** Queries time series and displays top 10 as line graph

## Current Configuration

### Display Settings

- **Unit:** short (count)
- **Draw Style:** Line with smooth interpolation
- **Legend:** Device names
- **Query Type:** Range (time series)

### Time Range

- Uses: dashboard time range variable `$__range`
- Default: Last 1 hour
- Auto-refresh: Every 30 seconds

## What's Working Well

- ✅ Time series shows connection pattern trends
- ✅ Top 10 keeps graph readable
- ✅ Smooth lines make patterns easy to spot
- ✅ Real-time updates capture connection changes
- ✅ Device names are meaningful

## Current Gaps

- ❌ No baseline comparison (can't see if connection count is abnormal)
- ❌ No connection type breakdown (TCP vs UDP, inbound vs outbound)
- ❌ No port scanning detection patterns
- ❌ No failed connection tracking (connection attempts that failed)
- ❌ No drill-down to see what connections exist
- ❌ No device type context (expected ranges differ)
- ❌ No correlation with bandwidth (high connections + low bandwidth = scanning)

## Potential Improvements

### 1. Add Baseline Comparison Overlay

**What:** Show 7-day average connection count as reference line
**How:** Add second query:

```promql
avg_over_time(sum by (device_name) (client_connections_total)[7d:5m])
```

Display as dashed line
**Impact:** Detect sudden spikes in connection count

### 2. Add Expected Range Bands by Device Type

**What:** Visual bands showing expected connection ranges for device types
**How:**

- Mobile: 50-200 connections (many apps)
- Workstation: 100-500 connections (browsing, apps)
- IoT: 5-20 connections (minimal)
- Smart TV: 10-50 connections (streaming services)
- Server: 500-2000 connections (depends on services)
Add as threshold bands on graph
**Impact:** Quickly spot devices outside normal range

### 3. Add Port Scanning Detection Alert

**What:** Annotate graph when scanning pattern detected
**How:** Detect patterns:

- Sudden spike in connections (>3x baseline in 5 minutes)
- High connection count + low bandwidth (Panel 1/2)
- High failed connections
Add annotation: "⚠️ Possible port scan at [time]"
**Impact:** Real-time scanning detection

### 4. Add Connection Type Breakdown Panel

**What:** Separate panel showing TCP vs UDP, inbound vs outbound
**How:** Create stacked area chart with queries:

```promql
client_connections_tcp_total
client_connections_udp_total
client_connections_inbound_total
client_connections_outbound_total
```

**Impact:** Understand connection patterns - all UDP = gaming or VoIP, all TCP = web/services

### 5. Add Failed Connection Counter

**What:** Track connection attempts that failed (refused, timeout)
**How:** Add metric from router: `client_failed_connections_total`
Display as separate series or annotation
**Impact:** High failed connections = scanning, blocked malware, or network issues

## Related Panels

- **Panel 1/2:** Bandwidth - High connections + low bandwidth = scanning
- **Panel 4/5:** DNS - High connections + high DNS = reconnaissance
- **Panel 6:** Protocol Distribution - Correlate connections with protocols used
- **Panel 7:** Client Activity Table - See connection count alongside other metrics

## Investigation Workflow

When you see unusual connection patterns:

### Step 1: Identify Pattern Type

**Pattern 1: Sudden Spike**

- Connections jump from 50 to 500 in 5 minutes
- **Likely:** Port scanning, malware activation, DDoS participation
- **Action:** Investigate immediately

**Pattern 2: Gradual Increase**

- Connections slowly increasing over hours/days
- **Likely:** Legitimate app growth, or slow-spreading malware
- **Action:** Monitor and investigate if continues

**Pattern 3: High Steady State**

- Device consistently has many connections
- **Likely:** Normal for device type (workstation, server) or malware
- **Action:** Compare to baseline and device type expectations

**Pattern 4: Regular Periodic Spikes**

- Connections spike at regular intervals (every 5 min, 15 min)
- **Likely:** Scheduled task (legitimate) or beaconing (malware)
- **Action:** Investigate timing and correlation with other metrics

### Step 2: Check Device Type Context

1. **Identify device:** Mobile, workstation, IoT, server?
2. **Expected connection counts:**
   - Mobile: 50-200 = normal
   - Workstation: 100-500 = normal
   - IoT: 5-20 = normal (cameras/sensors should have few connections)
   - Smart TV: 10-50 = normal
   - Server: Varies by services running
3. **Flag:** Devices >3x expected for type

### Step 3: Correlate with Bandwidth (Panel 1/2)

**Key Analysis: Connections per Bandwidth Ratio**

**High Connections + Low Bandwidth:**

- Many connections but little data transfer
- **Interpretation:** Scanning, reconnaissance, connection attempts
- **Example:** 500 connections but only 5 Mbps bandwidth = scanning
- **Action:** Investigate for scanning tools or compromise

**High Connections + High Bandwidth:**

- Many connections with significant data transfer
- **Interpretation:** Normal for data-heavy applications
- **Example:** 300 connections with 200 Mbps = normal (browsing, streaming, downloads)
- **Action:** Likely normal, verify with user if needed

**Low Connections + High Bandwidth:**

- Few connections but heavy data transfer
- **Interpretation:** Streaming, large downloads, normal
- **Example:** 15 connections with 400 Mbps = normal (4K streaming)
- **Action:** Normal behavior

### Step 4: Correlate with DNS (Panel 4/5)

**High Connections + High DNS:**

- Many connections and many DNS queries
- **Interpretation:** Scanning network, reconnaissance
- **Action:** Check Panel 5 (unique domains) and Panel 9 (which domains)

**High Connections + Low DNS:**

- Many connections but few DNS queries
- **Interpretation:** Either cached IPs or direct IP connections (suspicious)
- **Action:** Investigate what connections are to (may be botnet C2 via IP)

### Step 5: Determine Action

- **Normal:** Device within expected range for type, bandwidth proportional
- **Monitor:** Slight increase, within 2x baseline
- **Investigate:** 3x baseline, or IoT device with high connections
- **Isolate:** Port scanning detected, compromised IoT, botnet activity

## Common Scenarios & Responses

### Scenario 1: Workstation with 800 Connections

**Pattern:** Laptop shows 800 active connections (normally 150)
**Investigation:**

1. 5x normal = suspicious
2. **Check Panel 1/2:** If bandwidth also high = maybe legitimate (P2P, torrents, many browser tabs)
3. **Check Panel 4:** If DNS also high = scanning
4. **Timing:** Work hours = possibly legitimate, off-hours (3 AM) = suspicious
5. **Action:** Investigate what processes are creating connections

### Scenario 2: IoT Camera with 150 Connections

**Pattern:** Wyze camera with 150 connections (normally 5-10)
**Investigation:**

1. IoT devices should have minimal connections
2. 15x normal = highly suspicious
3. **Likely:** Compromised camera, botnet activity
4. **Check Panel 1/2:** Also likely high bandwidth
5. **Action:** Isolate to IoT VLAN immediately, check for botnet

### Scenario 3: Mobile Device with Periodic Spikes

**Pattern:** iPhone connections spike to 200 every 15 minutes, then drop to 50
**Investigation:**

1. Periodic pattern = automated task
2. 15-minute interval = background app sync (common on mobile)
3. **Likely:** Legitimate app background refresh (email, social media, cloud sync)
4. **Action:** Normal behavior for mobile devices

### Scenario 4: Server with Sudden Connection Drop

**Pattern:** Server connections drop from 800 to 50 suddenly
**Investigation:**

1. Sudden drop = service stopped or crashed
2. **Check:** What service runs on server?
3. **Action:** Investigate server health, service status

### Scenario 5: Unknown Device with High Connections at 3 AM

**Pattern:** New device "a0:66:2b" shows 500 connections at 3:00 AM
**Investigation:**

1. Unknown device + off-hours + high connections = critical
2. **Likely:** Compromised device performing scanning
3. **Action:** Identify device via MAC, isolate immediately, investigate

## Files Referenced

- **Dashboard JSON:** `grafana-dashboards/client-monitoring.json` (lines 338-365, Panel ID 8)
- **Prometheus Config:** `prometheus.yml` (scrape config)
- **Router Connection Tracking:** netstat/conntrack on GL-MT2500A
- **Lua Collector:** Connection metrics export on port 9100
- **Device Registry:** `/root/etc/device-registry.conf` (device naming)
