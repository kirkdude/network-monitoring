# Panel 1: Top 10 Bandwidth Users (Download)

## Panel Overview

- **Panel ID:** 1
- **Title:** Top 10 Bandwidth Users (Download)
- **Type:** Table with LCD Gauge (was Bar Gauge - converted for proper sorting)
- **Grid Position:** x=0, y=0, width=12, height=8 (top-left)
- **Purpose:** Shows the top 10 clients by download bandwidth usage, sorted by value

## Data Source

### Current: InfluxDB Flux Query

```flux
from(bucket: "network")
  |> range(start: v.timeRangeStart, stop: v.timeRangeStop)
  |> filter(fn: (r) => r._measurement == "bandwidth" and r.direction == "rx")
  |> drop(columns: ["_time"])
  |> group(columns: ["device_name"])
  |> sum(column: "_value")
  |> group()
  |> map(fn: (r) => ({ device_name: r.device_name, _value: float(v: r._value) * 8.0 / (float(v: uint(v: v.timeRangeStop) - uint(v: v.timeRangeStart)) / 1000000000.0) }))
  |> sort(columns: ["_value"], desc: true)
  |> limit(n: 10)
```

### Metrics Used

- **InfluxDB:** `bandwidth` measurement with `direction="rx"` tag
  - Tags: `device_name`, `ip`, `mac`, `protocol`, `direction`
  - Field: `bytes` (integer - delta values sent every minute)
  - Type: Event-based (deltas, not cumulative counters)

### Data Collection Flow

1. **Router (GL-MT2500A):** nlbwmon tracks per-IP bandwidth by protocol
   - **CRITICAL:** nlbwmon commit_interval MUST be 1 minute (not 24h) for real-time data
   - Run: `uci set nlbwmon.@nlbwmon[0].commit_interval="1m" && uci commit && /etc/init.d/nlbwmon restart`
2. **Export Script:** `/root/bin/send-bandwidth-to-influx.sh` (runs every minute via cron)
   - Parses nlbwmon database with `nlbw -c show`
   - Calculates deltas from previous run (only sends non-zero changes)
   - Resolves device names via `/root/bin/resolve-device-name.sh`
   - **CRITICAL:** Has PID lock file to prevent concurrent runs
   - **CRITICAL:** Must send to correct IP (192.168.1.124 with static DHCP for Mac mini)
3. **Telegraf:** Receives UDP packets on port 8094 (InfluxDB line protocol)
4. **InfluxDB:** Stores bandwidth events in "network" bucket
5. **Grafana:** Queries InfluxDB and visualizes in table with LCD Gauge

## Current Configuration

### Thresholds & Colors

- Green: 0 - 999,999 bps (< 1 Mbps)
- Yellow: 1,000,000 - 9,999,999 bps (1-10 Mbps)
- Red: 10,000,000+ bps (> 10 Mbps)

### Display Settings

- **Unit:** bps (bits per second)
- **Visualization Type:** Table with LCD Gauge cell display
- **Columns (in order):**
  1. Device (device name, clickable link to device detail) - First column
  2. Bandwidth (LCD Gauge visualization, 400px width) - Second column
- **Sorting:** Descending by Bandwidth value (highest at top)
- **Transformations:**
  - Organize: Rename columns, hide Time field
  - **Note:** Column order is determined by Flux query's `keep()` function, NOT by indexByName

### Time Range

- Uses: dashboard time range variables `v.timeRangeStart` and `v.timeRangeStop`
- Default: Last 1 hour
- Auto-refresh: Every 30 seconds
- **Works with all time ranges:** 5 minutes to days (requires nlbwmon 1-minute commits)

## Critical Lessons Learned - Flux Query Best Practices

### Issue 1: Type Conflict (float != int)

**Problem:** `sum()` returns integer, but division creates float. Mixing types causes error.

**Solution:** Explicitly convert to float BEFORE arithmetic:

```flux
|> map(fn: (r) => ({ r with _value: float(v: r._value) * 8.0 / ... }))
```

**NEVER use:** `int(v: r._value * 8.0 / ...)` - this causes the type conflict!

### Issue 2: Bar Gauge Sorts Alphabetically, Not By Value

**Problem:** Grafana bar gauges display series in alphabetical order by label, ignoring Flux `sort()`.

**Root Cause:** When data is grouped (`group(columns: ["device_name"])`), each device becomes a separate table/series. Grafana renders series alphabetically.

**Failed Attempts:**

- ❌ `sort()` in Flux query alone - ignored by Grafana
- ❌ `sortBy` transformation alone - doesn't work with grouped data
- ❌ `seriesToRows` + `sortBy` - labels break or still alphabetical

**Working Solution:** Convert to TABLE visualization with LCD Gauge cell display

1. Change panel type from `bargauge` to `table`
2. Use `group()` to ungroup data into single table AFTER aggregation
3. Configure table `sortBy` option to sort by value column
4. Add field override for value column with `custom.cellOptions: {type: "gauge", mode: "lcd"}`

**Result:** Table displays with proper value sorting + gauge visualization

### Issue 3: Max Series Exceeded (> 1001)

**Problem:** Too many time series created from event-based data

**Solution:** Drop `_time` column BEFORE grouping:

```flux
|> drop(columns: ["_time"])
|> group(columns: ["device_name"])
```

This prevents creating separate series for each timestamp.

### Issue 4: Proper Ungrouping for Tables

**Key Pattern for Table Panels:**

```flux
|> group(columns: ["device_name"])  # Group for aggregation
|> sum(column: "_value")             # Aggregate
|> group()                           # CRITICAL: Ungroup into single table
|> sort(columns: ["_value"], desc: true)  # Sort within single table
```

Without the final `group()`, you get separate tables per device that Grafana can't sort properly.

## What's Working Well

- ✅ Device names are meaningful (90+ devices identified via registry + DHCP + OUI)
- ✅ Color-coded thresholds provide quick visual indicators of heavy users
- ✅ Top 10 focus keeps dashboard uncluttered
- ✅ Real-time updates every 30 seconds for near-instant visibility
- ✅ Direction-specific (RX) provides clarity on download vs upload

## Current Gaps

- ✅ Drill-down links to device detail dashboard (IMPLEMENTED)
- ❌ No baseline comparison (can't see if usage is abnormal for that device)
- ❌ No time-of-day context (off-hours usage not highlighted)
- ❌ No device type indicators (can't distinguish IoT from workstations from streaming devices)
- ❌ No trust scoring or IOC detection
- ❌ New devices appear without historical context

## Complete Working Panel Configuration

### Panel JSON Structure

```json
{
  "type": "table",
  "options": {
    "showHeader": true,
    "sortBy": [
      {
        "displayName": "Bandwidth",
        "desc": true
      }
    ]
  },
  "fieldConfig": {
    "overrides": [
      {
        "matcher": {"id": "byName", "options": "Bandwidth"},
        "properties": [
          {
            "id": "custom.cellOptions",
            "value": {"type": "gauge", "mode": "lcd"}
          },
          {"id": "custom.width", "value": 400}
        ]
      }
    ]
  },
  "transformations": [
    {
      "id": "organize",
      "options": {
        "excludeByName": {"Time": true},
        "renameByName": {
          "device_name": "Device",
          "_value": "Bandwidth"
        }
      }
    }
  ]
}
```

## Troubleshooting

### No Data Appearing

**Check 1: nlbwmon commit interval**

```bash
ssh root@192.168.1.2 'uci show nlbwmon | grep commit'
```

Should be `commit_interval='1m'` (not 24h)

**Check 2: Bandwidth script running**

```bash
ssh root@192.168.1.2 'crontab -l | grep bandwidth'
```

Should show: `* * * * * /root/bin/send-bandwidth-to-influx.sh`

**Check 3: Data reaching InfluxDB**

```bash
curl -X POST 'http://localhost:8086/api/v2/query?org=home' \
  -b /tmp/influx_cookies.txt \
  -H 'Content-Type: application/vnd.flux' \
  --data-binary 'from(bucket: "network") |> range(start: -5m) |> filter(fn: (r) => r._measurement == "bandwidth") |> count()'
```

**Check 4: Router sending to correct IP**

```bash
ssh root@192.168.1.2 'grep INFLUX_HOST /root/bin/send-bandwidth-to-influx.sh'
```

Should be 192.168.1.124 (with static DHCP reservation for Mac mini)

### Panel Shows "No Data" for Short Time Ranges

**Cause:** Only devices with active bandwidth in that time window appear

- Most devices idle in 5-15 minute windows
- Normal behavior: 3-5 devices in 5 min, 10-20 in 1 hour, 50+ in 24 hours

**Solution:** This is correct - panel shows real-time bandwidth usage, not device inventory

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
**How:** Add second Flux query to panel (as Query B) to calculate 7-day average and compare
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
- Store in separate InfluxDB measurement: `device_trust_score` with `device_name` tag
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
- **Telegraf Config:** UDP listener on port 8094 for InfluxDB line protocol
- **Router Export Script:** `/root/bin/send-bandwidth-to-influx.sh` (on GL-MT2500A)
- **Router Device Registry:** `/root/etc/device-registry.conf` (manual device naming)
- **Router Name Resolution:** `/root/bin/resolve-device-name.sh` (device ID system)
