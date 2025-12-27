# Panel 6: Protocol Distribution

## Panel Overview

- **Panel ID:** 6
- **Title:** Protocol Distribution
- **Type:** Pie Chart
- **Grid Position:** x=16, y=16, width=8, height=8 (right third of third row)
- **Purpose:** Shows the distribution of network bandwidth across different protocols (HTTPS, QUIC, HTTP, DNS, etc.)

## Critical Fix Applied (2025-12-26)

**Issue:** Type conflict (float != int) in bandwidth rate calculation

**Solution:** Added `float(v: r._value)` conversion:

```flux
|> map(fn: (r) => ({ r with _value: float(v: r._value) * 8.0 / (float(v: uint(v: v.timeRangeStop) - uint(v: v.timeRangeStart)) / 1000000000.0) }))
```

**Key:** Pie charts aggregate by protocol instead of device_name, but same type conversion needed.

## Data Source

### Prometheus Query

```promql
sum by (protocol) (rate(client_bandwidth_bytes_total{direction="rx"}[$__range]))
```

### Metrics Used

- `client_bandwidth_bytes_total{direction="rx"}` - Download bytes per protocol
  - Labels: `device_name`, `ip`, `mac`, `protocol`, `direction`
  - Type: Counter (cumulative)
  - Common protocols: HTTPS, QUIC, HTTP, DNS, NTP, SSH, etc.

### Data Collection Flow

1. **Router (GL-MT2500A):** nlbwmon tracks bandwidth by protocol (via port/pattern matching)
2. **Export Script:** `/root/bin/export-client-bandwidth.sh`
   - Parses nlbwmon database (~19 seconds)
   - Aggregates by protocol across all clients
3. **Lua Collector:** `/usr/lib/lua/prometheus-collectors/client_bandwidth.lua`
   - Exports on port 9100
4. **Prometheus:** Scrapes router:9100 every 30 seconds
5. **Grafana:** Queries Prometheus, aggregates by protocol, displays as pie chart

## Current Configuration

### Display Settings

- **Unit:** Bps (bytes per second)
- **Type:** Pie chart
- **Legend:** Table showing protocol name, value, and percentage
- **Legend Placement:** Right side of chart
- **Legend Values:** Value + Percent

### Time Range

- Uses: dashboard time range variable `$__range`
- Default: Last 1 hour
- Auto-refresh: Every 30 seconds

## What's Working Well

- ✅ Easy visualization of protocol mix across entire network
- ✅ Percentage display helps understand relative usage
- ✅ Table legend shows exact values
- ✅ Helps identify unexpected protocols quickly (visual pie slice)

## Current Gaps

- ❌ Network-wide only - cannot see per-device protocol breakdown
- ❌ No suspicious protocol highlighting (Tor, unusual ports)
- ❌ No baseline comparison (is current distribution normal?)
- ❌ No device correlation (which device is using which protocol?)
- ❌ No port-level detail (protocol detection may be imperfect)
- ❌ No drill-down to devices using specific protocol
- ❌ Missing protocols are not shown (zero bandwidth protocols invisible)

## Potential Improvements

### 1. Add Per-Device Protocol Breakdown Panel

**What:** New panel showing protocol distribution per device (not just network-wide)
**How:** Create new table panel with query:

```promql
sum by (device_name, protocol) (rate(client_bandwidth_bytes_total{direction="rx"}[1h]))
```

Display as table with devices as rows, protocols as columns
**Impact:** Identify which devices use which protocols - key for security analysis

### 2. Add Suspicious Protocol Alert Overlay

**What:** Highlight suspicious protocols with warning indicators
**How:** Add alert annotations for:

- **Tor (port 9050):** Anonymization - requires investigation
- **IRC (port 6667):** Legacy botnet C2 channel
- **Bitcoin mining (port 8333):** Unauthorized mining
- **Unusual high ports (> 50000):** Potentially malicious
- **Non-standard SSH (not port 22):** Backdoor access
**Impact:** Immediate visibility into security-relevant protocols

### 3. Add Expected Protocol Distribution Baseline

**What:** Overlay showing typical/expected protocol mix
**How:**

- Track 7-day average protocol distribution
- Display as annotation: "Normal: HTTPS 70%, QUIC 20%, HTTP 5%, Other 5%"
- Highlight deviations >20% from normal
**Impact:** Detect protocol shift attacks or compromise

### 4. Add Drill-Down to Devices Using Protocol

**What:** Click protocol slice → see devices using that protocol
**How:** Configure data link on pie chart:

```json
{
  "dataLinks": [{
    "title": "Devices using ${__field.name}",
    "url": "http://localhost:3000/d/c49d4df6-1edc-4998-bb71-95b81a909ece?var-protocol=${__field.name}"
  }]
}
```

Create device list panel filtered by protocol
**Impact:** Investigate unexpected protocol usage

### 5. Add Protocol Timeline Panel

**What:** Show protocol distribution changes over time (stacked area chart)
**How:** Create separate panel with query:

```promql
sum by (protocol) (rate(client_bandwidth_bytes_total{direction="rx"}[5m]))
```

Display as stacked area chart over last 24 hours
**Impact:** See when protocol mix changed - correlate with events

## Related Panels

- **Panel 1/2:** Bandwidth Users - See which devices have high bandwidth
- **Panel 7:** Client Activity Table - See full device profile
- **Panel 8:** Connection Count - High connections + unusual protocol = scanning

## Investigation Workflow

When you see unexpected protocol distribution:

### Step 1: Identify Expected Protocol Mix

**Normal home network:**

- **HTTPS:** 60-80% (most web traffic, streaming)
- **QUIC:** 10-20% (YouTube, Chrome, modern web)
- **HTTP:** <5% (legacy sites, firmware updates)
- **DNS:** 1-2% (name resolution)
- **NTP:** <1% (time synchronization)
- **SSH/RDP:** <1% (remote access if used)
- **Other:** <5%

### Step 2: Check for Suspicious Protocols

**Red flags:**

- **Tor (port 9050):** Anonymization - could be legitimate privacy tool or malicious activity
- **IRC (port 6667):** Legacy protocol, often used by botnets
- **Bitcoin mining (port 8333):** Unauthorized mining on your devices
- **Unusual high ports:** Custom protocols, potentially malicious
- **Non-standard SSH ports:** Backdoors often use alternate ports

### Step 3: Investigate Protocol Changes

1. **Sudden appearance of new protocol:**
   - Which device(s) started using it?
   - When did it start?
   - Is it legitimate (new app) or suspicious?

2. **Significant shift in existing protocol:**
   - HTTPS dropped from 75% to 40% = what's replacing it?
   - HTTP increased from 3% to 25% = downgrade attack?

### Step 4: Correlate with Device Behavior

1. **Check Panel 7 (Client Activity Table):**
   - Sort by bandwidth, identify high-bandwidth devices
   - Likely these devices are driving protocol distribution
2. **Create per-device protocol query:**

   ```promql
   sum by (device_name, protocol) (rate(client_bandwidth_bytes_total{direction="rx"}[1h]))
   ```

3. Identify which device uses suspicious protocol

### Step 5: Determine Action

- **Expected protocols in normal distribution:** No action
- **Tor detected:** Investigate which device, determine if authorized
- **IRC detected:** Likely botnet, isolate device immediately
- **Unusual ports:** Investigate device for malware
- **Protocol downgrade:** Check for MITM attack or misconfiguration

## Common Scenarios & Responses

### Scenario 1: Tor Protocol Detected (Port 9050)

**Investigation:**

1. Tor provides anonymization - could be legitimate privacy tool or malicious
2. **Check:** Which device is using Tor?

   ```promql
   client_bandwidth_bytes_total{protocol="tor"}
   ```

3. **Evaluate:**
   - Workstation with Tor Browser = likely legitimate privacy use
   - IoT device with Tor = compromised (IoT shouldn't need Tor)
   - Server with Tor = could be legitimate Tor relay or malicious
4. **Action:** Verify authorization with user, block if unauthorized

### Scenario 2: IRC Protocol Detected (Port 6667)

**Investigation:**

1. IRC is legacy chat protocol, rarely used legitimately in modern networks
2. Common botnet C2 (Command & Control) communication method
3. **Check:** Which device(s) using IRC?
4. **Likely:** Compromised device part of botnet
5. **Action:** Isolate device immediately, scan for malware, reinstall OS if needed

### Scenario 3: HTTP Increased to 30% (Was 3%)

**Investigation:**

1. HTTP is unencrypted, should be minimal in modern networks
2. Sudden increase could indicate:
   - **Downgrade attack:** Attacker forcing HTTP instead of HTTPS
   - **Legacy device/firmware:** Old IoT device with unencrypted traffic
   - **Local network service:** Device accessing local HTTP server
3. **Check Panel 7:** Which devices have high bandwidth?
4. **Check Panel 9:** What domains are being accessed via HTTP?
5. **Action:** Investigate devices, ensure HTTPS is used where possible

### Scenario 4: Unknown Protocol at Port 4444

**Investigation:**

1. Port 4444 is Metasploit default reverse shell port
2. Presence of traffic on this port = likely compromise
3. **Check:** Which device has traffic on port 4444?
4. **Likely:** Device is compromised with reverse shell backdoor
5. **Action:** Isolate device immediately, investigate for compromise, block port at firewall

### Scenario 5: QUIC Suddenly Increased to 60% (Was 15%)

**Investigation:**

1. QUIC is modern protocol (YouTube, Chrome, HTTP/3)
2. Sudden increase could indicate:
   - Normal: Users watching more YouTube
   - Normal: Chrome browser updates using QUIC
   - Check timing: Evening increase = streaming = normal
3. **Action:** Likely normal behavior, monitor

## Files Referenced

- **Dashboard JSON:** `grafana-dashboards/client-monitoring.json` (lines 203-235, Panel ID 6)
- **Prometheus Config:** `prometheus.yml` (scrape config)
- **Router Export Script:** `/root/bin/export-client-bandwidth.sh` (on GL-MT2500A)
- **Lua Collector:** `/usr/lib/lua/prometheus-collectors/client_bandwidth.lua` (on router)
- **nlbwmon:** Router bandwidth monitor that detects protocols by port/pattern
