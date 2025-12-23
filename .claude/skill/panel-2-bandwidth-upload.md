# Panel 2: Top 10 Bandwidth Users (Upload)

## Panel Overview
- **Panel ID:** 2
- **Title:** Top 10 Bandwidth Users (Upload)
- **Type:** Bar Gauge (Horizontal)
- **Grid Position:** x=12, y=0, width=12, height=8 (top-right)
- **Purpose:** Shows the top 10 clients by upload bandwidth usage

## Data Source

### Prometheus Query
```promql
sort_desc(topk(10, sum by (device_name) (rate(client_bandwidth_bytes_total{direction="tx"}[$__range]) * 8)))
```

### Metrics Used
- `client_bandwidth_bytes_total{direction="tx"}` - Total bytes uploaded per client
  - Labels: `device_name`, `ip`, `mac`, `protocol`, `direction`
  - Type: Counter (cumulative)

### Data Collection Flow
1. **Router (GL-MT2500A):** nlbwmon tracks per-IP bandwidth by protocol
2. **Export Script:** `/root/bin/export-client-bandwidth.sh`
   - Parses nlbwmon database (~19 seconds execution time)
   - Resolves device names via `/root/bin/resolve-device-name.sh`
   - Outputs Prometheus metrics format to stdout
3. **Lua Collector:** `/usr/lib/lua/prometheus-collectors/client_bandwidth.lua`
   - Invoked by prometheus-node-exporter-lua
   - Exports metrics on port 9100
4. **Prometheus:** Scrapes router:9100 every 30 seconds (25s timeout configured)
5. **Grafana:** Queries Prometheus and visualizes in bar gauge

## Current Configuration

### Thresholds & Colors
- Green: 0 - 999,999 bps (< 1 Mbps)
- Yellow: 1,000,000 - 4,999,999 bps (1-5 Mbps)
- Red: 5,000,000+ bps (> 5 Mbps)

**Note:** Upload thresholds are lower than download because typical home upload is ~10% of download bandwidth.

### Display Settings
- **Unit:** bps (bits per second)
- **Display Mode:** Gradient horizontal bar gauge
- **Show Unfilled:** Yes
- **Legend Format:** `{{device_name}}`
- **Query Type:** Instant (snapshot)

### Time Range
- Uses: dashboard time range variable `$__range`
- Default: Last 1 hour
- Auto-refresh: Every 30 seconds

## What's Working Well
- ✅ Device names are meaningful (90+ devices identified)
- ✅ Lower thresholds appropriate for upload monitoring
- ✅ Color-coded alerts for abnormal upload activity
- ✅ Real-time updates every 30 seconds
- ✅ Direction-specific (TX) clearly indicates upload

## Current Gaps
- ❌ No drill-down links to device detail dashboard
- ❌ No baseline comparison - can't tell if upload is abnormal for that device
- ❌ No download/upload ratio analysis (upload should be ~10% of download)
- ❌ No data exfiltration detection patterns
- ❌ No IoT device upload alerts (IoT upload should be minimal)
- ❌ No C2 beaconing detection (regular interval uploads)

## Potential Improvements

### 1. Add Upload/Download Ratio Analysis
**What:** Show upload as percentage of download to detect anomalies
**How:** Add second query showing ratio:
```promql
(
  sum by (device_name) (rate(client_bandwidth_bytes_total{direction="tx"}[$__range]))
  /
  sum by (device_name) (rate(client_bandwidth_bytes_total{direction="rx"}[$__range]))
) * 100
```
Display as annotation: "Upload is X% of download"
**Impact:** Detect data exfiltration - normal ratio is <10%, suspicious if >50%

### 2. Add Drill-Down Link to Device Detail
**What:** Click device → navigate to device-specific dashboard
**How:** Add data link in panel JSON:
```json
{
  "dataLinks": [{
    "title": "Device Detail",
    "url": "http://localhost:3000/d/66bdd5ca-674b-46db-b177-59920156e784/device-detail?var-device=${__field.labels.device_name}"
  }]
}
```
**Impact:** Quick investigation of suspicious upload patterns

### 3. Add IoT Device Upload Alert
**What:** Highlight IoT devices with >10 Mbps upload (abnormal)
**How:**
- Tag devices as IoT in device registry
- Create alert rule for IoT upload >10 Mbps
- Add panel override for IoT devices showing red threshold at 10 Mbps instead of 5 Mbps
**Impact:** Early detection of compromised IoT devices (cameras, sensors)

### 4. Add Baseline Comparison
**What:** Compare current upload to device's 7-day average
**How:** Add second query:
```promql
(
  sum by (device_name) (rate(client_bandwidth_bytes_total{direction="tx"}[1h]) * 8)
  /
  avg_over_time(sum by (device_name) (rate(client_bandwidth_bytes_total{direction="tx"}[1h]) * 8)[7d:1h])
) * 100 - 100
```
**Impact:** Detect sudden upload spikes (>300% of baseline = suspicious)

### 5. Add Beaconing Detection Annotation
**What:** Detect regular interval uploads (C2 communication pattern)
**How:** (Advanced - requires analysis script)
- Analyze upload patterns for regularity (every 5 min, 10 min, etc.)
- Flag devices with highly periodic upload behavior
- Annotate panel with beaconing warning
**Impact:** Detect compromised devices communicating with C2 servers

## Related Panels
- **Panel 1:** Top Bandwidth Users (Download) - Compare ratios (upload should be ~10% of download)
- **Panel 3:** Bandwidth Over Time - See temporal upload patterns
- **Panel 4:** Top DNS Query Clients - Correlate upload with DNS activity
- **Panel 7:** Client Activity Table - See full device profile
- **Panel 9:** Top Domains - See what domains device is uploading to

## Investigation Workflow
When you see suspicious high upload activity:
1. **Identify** the device name and note current upload bandwidth
2. **Check Panel 1** (Download) - Calculate ratio: upload/download. If >50%, suspicious
3. **Check Panel 3** (Over Time) - Is upload pattern regular (beaconing)? Or bursty (large file upload)?
4. **Check Panel 4** (DNS) - High DNS + high upload = scanning or data exfiltration
5. **Check Panel 9** (Domains) - What is device uploading to? Check for suspicious domains
6. **Check Panel 8** (Connections) - High connections + high upload = likely compromise
7. **Historical Context** - Compare to device's normal upload behavior

## Common Scenarios & Responses

### Scenario 1: IoT Device with High Upload
**Signs:** Camera, sensor, or smart home device uploading >10 Mbps
**Investigation:**
1. IoT devices should have minimal upload (<2 Mbps typically, cameras <5 Mbps)
2. Check if upload aligns with device function (security camera recording to cloud = normal)
3. Check domains - should only be manufacturer cloud (e.g., wyze.com, ring.com)
4. If not manufacturer domain or excessive for device type, likely compromised
5. **Action:** Isolate to IoT VLAN immediately, investigate further

### Scenario 2: Workstation with Unusually High Upload
**Signs:** Desktop/laptop uploading >50 Mbps sustained
**Investigation:**
1. Normal workstation upload: <10 Mbps (web browsing, email, chat)
2. High upload could be:
   - Legitimate: Cloud backup, video call, file upload to cloud storage
   - Suspicious: Data exfiltration, compromised system uploading stolen data
3. **Check timing:** Off-hours (2-6 AM) = very suspicious
4. **Check domains:** Cloud providers (dropbox, gdrive) = possibly legitimate
5. **Check upload/download ratio:** If upload >> download, suspicious

### Scenario 3: Regular Interval Upload Pattern (Beaconing)
**Signs:** Device uploading small amounts at exact intervals (every 5 min, 10 min)
**Investigation:**
1. Beaconing is C2 (Command & Control) communication pattern
2. Compromised devices check in with attacker server regularly
3. **Check Panel 3 (Over Time):** Look for perfectly regular spikes
4. **Check Panel 9 (Domains):** Check destination - if unknown/suspicious domain, confirmed compromise
5. **Action:** Isolate device immediately, block destination domain at firewall

### Scenario 4: Smart TV with Upload Spike
**Signs:** LG TV, Apple TV, etc. suddenly uploading >20 Mbps
**Investigation:**
1. Smart TVs typically have minimal upload (<5 Mbps)
2. Common causes:
   - Firmware update attempt (check Panel 9 for update.lge.com, etc.)
   - Telemetry/analytics data collection (privacy concern but not malicious)
   - Compromised TV (rare but possible)
3. **Check Panel 9:** If accessing known TV manufacturer domains, likely legitimate
4. **Consider:** Block telemetry domains for privacy (e.g., samba.lge.com)

## Files Referenced
- **Dashboard JSON:** `grafana-dashboards/client-monitoring.json` (lines 50-95, Panel ID 2)
- **Prometheus Config:** `prometheus.yml` (scrape config for router:9100)
- **Router Export Script:** `/root/bin/export-client-bandwidth.sh` (on GL-MT2500A)
- **Router Device Registry:** `/root/etc/device-registry.conf` (manual device naming)
- **Router Name Resolution:** `/root/bin/resolve-device-name.sh` (device ID system)
- **Lua Collector:** `/usr/lib/lua/prometheus-collectors/client_bandwidth.lua` (on router)
- **Python Report:** `/Users/kirkl/bin/generate-client-report` (similar Prometheus queries)
