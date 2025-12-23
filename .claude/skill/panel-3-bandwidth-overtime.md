# Panel 3: Bandwidth Over Time (Top 5 Clients)

## Panel Overview
- **Panel ID:** 3
- **Title:** Bandwidth Over Time (Top 5 Clients)
- **Type:** Time Series (Line Graph)
- **Grid Position:** x=0, y=8, width=24, height=8 (full width, second row)
- **Purpose:** Shows bandwidth trends over time for the top 5 clients with download and upload visualization

## Data Source

### Prometheus Queries
**Query A - Download:**
```promql
topk(5, sum by (device_name) (rate(client_bandwidth_bytes_total{direction="rx"}[$__range]) * 8))
```
Legend: `{{device_name}} Download`

**Query B - Upload (Negated for waterfall effect):**
```promql
topk(5, sum by (device_name) (rate(client_bandwidth_bytes_total{direction="tx"}[$__range]) * -8))
```
Legend: `{{device_name}} Upload`

**Note:** Upload is multiplied by -8 to create a "waterfall" effect showing download above zero and upload below zero on the same graph.

### Metrics Used
- `client_bandwidth_bytes_total{direction="rx"}` - Download bytes
- `client_bandwidth_bytes_total{direction="tx"}` - Upload bytes
  - Labels: `device_name`, `ip`, `mac`, `protocol`, `direction`
  - Type: Counter (cumulative)

### Data Collection Flow
1. **Router (GL-MT2500A):** nlbwmon tracks per-IP bandwidth by protocol
2. **Export Script:** `/root/bin/export-client-bandwidth.sh` (runs ~19 seconds)
3. **Lua Collector:** `/usr/lib/lua/prometheus-collectors/client_bandwidth.lua`
4. **Prometheus:** Scrapes router:9100 every 30 seconds (25s timeout)
5. **Grafana:** Queries time series data and visualizes with smooth lines

## Current Configuration

### Display Settings
- **Unit:** bps (bits per second)
- **Draw Style:** Line with smooth interpolation
- **Fill Opacity:** 10%
- **Legend:** Shows device names with "Download" or "Upload" suffix
- **Query Type:** Range (time series)

### Time Range
- Uses: dashboard time range variable `$__range`
- Default: Last 1 hour
- Auto-refresh: Every 30 seconds

## What's Working Well
- ✅ Shows both download and upload on single graph for easy comparison
- ✅ Smooth line interpolation makes trends easy to spot
- ✅ Top 5 keeps graph readable (not cluttered with all devices)
- ✅ Real-time updates every 30 seconds capture trends
- ✅ Waterfall effect (upload negative) visually separates directions

## Current Gaps
- ❌ No spike annotations (can't see why bandwidth suddenly increased)
- ❌ No off-hours highlighting (2-6 AM activity not called out)
- ❌ No baseline comparison overlay (can't see if pattern is normal)
- ❌ No anomaly detection markers
- ❌ No correlation with events (e.g., "LG TV firmware update attempt at 14:15")
- ❌ No drill-down to specific time ranges

## Potential Improvements

### 1. Add Spike Annotations
**What:** Automatically annotate significant bandwidth spikes (>3x previous 5-minute average)
**How:** Add annotation query:
```promql
# Detect spikes
rate(client_bandwidth_bytes_total{direction="rx"}[5m]) / rate(client_bandwidth_bytes_total{direction="rx"}[5m] offset 5m) > 3
```
Configure annotation to show device name and spike magnitude
**Impact:** Instant visibility into what caused bandwidth changes

### 2. Add Off-Hours Overlay
**What:** Highlight time ranges 2 AM - 6 AM with different background color
**How:** Add Grafana time region annotation for hours 2-6
**Impact:** Quickly spot suspicious off-hours activity

### 3. Add Baseline Comparison Line
**What:** Overlay 7-day average bandwidth as reference line
**How:** Add Query C:
```promql
avg_over_time(sum by (device_name) (rate(client_bandwidth_bytes_total{direction="rx"}[5m]) * 8)[7d:5m])
```
Display as dashed line labeled "7-day average"
**Impact:** See if current usage is within normal range

### 4. Add Event Correlation
**What:** Show related events (firmware updates, backups, streaming sessions) as annotations
**How:**
- Parse router logs for known events
- Create annotation datasource from events
- Correlate events with bandwidth spikes
**Impact:** Understand causality - "Spike at 14:15 was LG TV update attempt (blocked)"

### 5. Add Drill-Down Time Selection
**What:** Click on spike → zoom to that 15-minute window with more detail
**How:** Configure time range link:
```json
{
  "dataLinks": [{
    "title": "Zoom to spike",
    "url": "http://localhost:3000/d/c49d4df6-1edc-4998-bb71-95b81a909ece?from=${__from}&to=${__to}&var-device=${__field.labels.device_name}"
  }]
}
```
**Impact:** Quick investigation of specific incidents

## Related Panels
- **Panel 1:** Top Bandwidth Download - See who's currently in top 10 download
- **Panel 2:** Top Bandwidth Upload - See who's currently in top 10 upload
- **Panel 7:** Client Activity Table - See full metrics for devices shown here
- **Panel 8:** Connection Count - Correlate bandwidth with connection patterns

## Investigation Workflow
When you see unusual patterns in bandwidth over time:

### Pattern 1: Sudden Spike
1. **Identify** when spike occurred and which device
2. **Check amplitude:** How many times higher than normal?
3. **Check duration:** Brief (seconds) vs sustained (minutes/hours)
4. **Check Panel 9 (Domains):** What was device accessing during spike?
5. **Check Panel 8 (Connections):** Did connections also spike?
6. **Correlate timing:** Does it align with known events (backups, streaming)?

### Pattern 2: Gradual Increase Over Days
1. **Measure rate:** How much increase per day?
2. **Check device type:** Legitimate growth (new apps) or suspicious (data collection)?
3. **Check Panel 4 (DNS):** Has DNS activity also increased?
4. **Check Panel 5 (Unique Domains):** Accessing more domains over time?
5. **Possible causes:**
   - Legitimate: New service adoption, increased usage
   - Suspicious: Malware slowly exfiltrating data

### Pattern 3: Regular Periodic Spikes
1. **Measure interval:** Every 5 min? 15 min? 1 hour?
2. **Measure magnitude:** How high are the spikes?
3. **Check consistency:** Perfectly regular = likely automated
4. **Possible causes:**
   - Legitimate: Scheduled backups, sync operations
   - Suspicious: C2 beaconing, data exfiltration
5. **Investigation:** Check Panel 9 for destination domains

### Pattern 4: Off-Hours Activity (2-6 AM)
1. **Identify device:** Which device is active at night?
2. **Check device type:** Workstation at 3 AM = suspicious, backup server = normal
3. **Check activity type:** High download = updates?, high upload = exfiltration?
4. **Check Panel 9:** What domains accessed during off-hours?
5. **Action:** For workstations/mobile devices, investigate for compromise

## Common Scenarios & Responses

### Scenario 1: Sharp Download Spike on Streaming Device
**Pattern:** Apple TV or similar shows sudden 400 Mbps download spike
**Investigation:**
1. Check time of spike - evening (7-10 PM) = likely streaming start
2. Duration - sustained for 1-2 hours = 4K movie/show
3. **Action:** Normal behavior, no investigation needed

### Scenario 2: Upload Spike on Workstation
**Pattern:** Laptop shows 100 Mbps upload spike at 2 PM
**Investigation:**
1. Check duration - 10-15 minutes = likely file upload
2. Check Panel 9 - accessing dropbox.com or similar = cloud storage
3. **Action:** Likely legitimate, but verify with user if sustained or frequent

### Scenario 3: Periodic Upload Spikes Every 10 Minutes
**Pattern:** Unknown device shows small upload spikes at exact 10-minute intervals
**Investigation:**
1. Perfectly regular pattern = automated process
2. Check Panel 9 - if unknown/suspicious domain = C2 beaconing
3. Check device type - IoT device with beaconing = likely compromised
4. **Action:** Isolate device, block destination domain, investigate for malware

### Scenario 4: Gradual Bandwidth Increase Over Week
**Pattern:** Workstation bandwidth increasing 20% per day for 5 days
**Investigation:**
1. Abnormal growth rate = suspicious
2. Check Panel 5 (Unique Domains) - also increasing? = reconnaissance
3. Check Panel 4 (DNS) - excessive queries? = scanning
4. **Action:** Likely compromised, investigate immediately

## Files Referenced
- **Dashboard JSON:** `grafana-dashboards/client-monitoring.json` (lines 96-128, Panel ID 3)
- **Prometheus Config:** `prometheus.yml` (scrape config)
- **Router Export Script:** `/root/bin/export-client-bandwidth.sh` (on GL-MT2500A)
- **Lua Collector:** `/usr/lib/lua/prometheus-collectors/client_bandwidth.lua` (on router)
- **Device Registry:** `/root/etc/device-registry.conf` (on router)
