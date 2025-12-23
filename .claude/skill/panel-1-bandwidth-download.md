# Panel 1: Top 10 Bandwidth Users (Download)

## Panel Overview
- **Panel ID:** 1
- **Title:** Top 10 Bandwidth Users (Download)
- **Type:** Bar Gauge (Horizontal)
- **Grid Position:** x=0, y=0, width=12, height=8 (top-left)
- **Purpose:** Shows the top 10 clients by download bandwidth usage

## Data Source

### Prometheus Query
```promql
sort_desc(topk(10, sum by (device_name) (rate(client_bandwidth_bytes_total{direction="rx"}[$__range]) * 8)))
```

### Metrics Used
- `client_bandwidth_bytes_total{direction="rx"}` - Total bytes downloaded per client
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
- Yellow: 1,000,000 - 9,999,999 bps (1-10 Mbps)
- Red: 10,000,000+ bps (> 10 Mbps)

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
- ✅ Device names are meaningful (90+ devices identified via registry + DHCP + OUI)
- ✅ Color-coded thresholds provide quick visual indicators of heavy users
- ✅ Top 10 focus keeps dashboard uncluttered
- ✅ Real-time updates every 30 seconds for near-instant visibility
- ✅ Direction-specific (RX) provides clarity on download vs upload

## Current Gaps
- ❌ No drill-down links to device detail dashboard
- ❌ No baseline comparison (can't see if usage is abnormal for that device)
- ❌ No time-of-day context (off-hours usage not highlighted)
- ❌ No device type indicators (can't distinguish IoT from workstations from streaming devices)
- ❌ No trust scoring or IOC detection
- ❌ New devices appear without historical context

## Potential Improvements

### 1. Add Drill-Down Link to Device Detail
**What:** Click device → navigate to device-specific dashboard with full metrics
**How:** Add data link in panel JSON configuration:
```json
{
  "dataLinks": [{
    "title": "Device Detail",
    "url": "http://localhost:3000/d/66bdd5ca-674b-46db-b177-59920156e784/device-detail?var-device=${__field.labels.device_name}"
  }]
}
```
**Impact:** Enables one-click investigation workflow when suspicious activity detected

### 2. Add Baseline Comparison Overlay
**What:** Show current usage vs 7-day average as percent deviation
**How:** Add second query to panel (as Query B):
```promql
(
  sum by (device_name) (rate(client_bandwidth_bytes_total{direction="rx"}[1h]) * 8)
  /
  avg_over_time(sum by (device_name) (rate(client_bandwidth_bytes_total{direction="rx"}[1h]) * 8)[7d:1h])
) * 100 - 100
```
Then transform to show both current and deviation
**Impact:** Detect anomalies - devices >200% of baseline are suspicious

### 3. Add Time-of-Day Annotation
**What:** Highlight off-hours usage (2-6 AM) with special annotation or color
**How:** Either:
- Add Grafana annotation query for time ranges
- Create separate panel specifically for off-hours bandwidth leaders
- Use panel overrides to change bar color based on hour() function
**Impact:** Detect suspicious activity timing (data exfiltration, compromised devices)

### 4. Add Device Type Labels
**What:** Show [IoT], [Mobile], [Streaming], [Workstation] tags next to device names
**How:**
- Add device_type field to `/root/etc/device-registry.conf` on router
- Modify export script to include device_type in labels
- Update legend format to: `{{device_name}} [{{device_type}}]`
**Impact:** Context for expected behavior - IoT downloading 400 Mbps is suspicious, streaming device is normal

### 5. Add Trust Score Indicator
**What:** Show trust score (1-10) or risk indicator next to devices
**How:** (Future enhancement - requires trust scoring system)
- Calculate trust scores based on: baseline adherence, threat intel clean, device age
- Store in separate metric: `device_trust_score{device_name}`
- Add as second series or table column
**Impact:** Immediate visibility into which devices need investigation

## Related Panels
- **Panel 2:** Top Bandwidth Users (Upload) - Compare download vs upload ratios
- **Panel 3:** Bandwidth Over Time - See temporal patterns for these devices
- **Panel 4:** Top DNS Query Clients - Correlate high bandwidth with DNS activity
- **Panel 7:** Client Activity Table - See full device profile with all metrics
- **Panel 9:** Top Domains - See what these high-bandwidth devices are accessing

## Investigation Workflow
When you see suspicious high download activity:
1. **Identify** the device name and note current bandwidth
2. **Check Panel 2** (Upload) - Is upload also high? Upload > 10% of download is suspicious
3. **Check Panel 4** (DNS) - Excessive DNS queries alongside high bandwidth = data exfiltration or scanning
4. **Check Panel 9** (Domains) - What domains is device accessing? Look for unknown/suspicious domains
5. **Check Panel 8** (Connections) - High connections + high bandwidth = potential compromise
6. **Use Device Detail Dashboard** - Click drill-down for complete device analysis
7. **Historical Context** - Compare to device's normal behavior (need baseline for this)

## Common Scenarios & Responses

### Scenario 1: New Unknown Device in Top 10
**Signs:** Device with partial MAC (a0:66:2b), high bandwidth, no historical data
**Investigation:**
1. Check router DHCP leases: `ssh root@192.168.1.2 'cat /tmp/dhcp.leases'`
2. Check MAC OUI: First 6 chars of MAC identify manufacturer
3. Add to device registry if legitimate: `/root/etc/device-registry.conf`
4. Move to guest network if unidentified or untrusted

### Scenario 2: Known IoT Device with Excessive Download
**Signs:** Camera, sensor, or smart home device downloading >50 Mbps
**Investigation:**
1. IoT devices should have minimal download (<10 Mbps typically)
2. Check domains accessed - should only be manufacturer cloud
3. Likely compromised - isolate to IoT VLAN immediately
4. Check for botnet activity (Panel 8 - excessive connections)

### Scenario 3: Smart TV with High Bandwidth
**Signs:** LG TV, Apple TV, or similar with 200-500 Mbps download
**Investigation:**
1. This is typically normal (4K streaming)
2. Check if activity aligns with usage (evenings = normal, 3 AM = suspicious)
3. Verify domains are content CDNs (netflix, youtube, etc.)
4. Watch for excessive upload (Panel 2) - TVs should barely upload

## Files Referenced
- **Dashboard JSON:** `grafana-dashboards/client-monitoring.json` (lines 3-48, Panel ID 1)
- **Prometheus Config:** `prometheus.yml` (scrape config for router:9100)
- **Router Export Script:** `/root/bin/export-client-bandwidth.sh` (on GL-MT2500A)
- **Router Device Registry:** `/root/etc/device-registry.conf` (manual device naming)
- **Router Name Resolution:** `/root/bin/resolve-device-name.sh` (device ID system)
- **Lua Collector:** `/usr/lib/lua/prometheus-collectors/client_bandwidth.lua` (on router)
- **Python Report:** `/Users/kirkl/bin/generate-client-report` (similar Prometheus queries)
