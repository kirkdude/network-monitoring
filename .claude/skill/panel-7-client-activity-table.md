# Panel 7: Client Activity Table

## Panel Overview

- **Panel ID:** 7
- **Title:** Client Activity Table
- **Type:** Table
- **Grid Position:** x=0, y=24, width=24, height=10 (full width, fourth row)
- **Purpose:** Comprehensive table showing all clients with 4 key metrics: download, upload, connections, and DNS queries

## Critical Fix Applied (2025-12-26)

**Issue:** Table showing only one device instead of all devices

**Root Cause:** After grouping by `device_name` and aggregating, each device was a separate table. Grafana merge transformation only combined first table from each query.

**Solution:** Add `group()` to ungroup AFTER aggregation in ALL 4 queries:

```flux
|> drop(columns: ["_time"])     # Prevent series explosion
|> group(columns: ["device_name"])
|> sum() or count()
|> group()                       # CRITICAL: Ungroup into single table
```

**Result:** All devices now appear in a single merged table with 4 columns

## Data Source

### InfluxDB Flux Queries (4 metrics merged)

**Query A - Download Bandwidth**
**Query B - Upload Bandwidth**
**Query C - Active Connections**
**Query D - DNS Queries**

All use similar pattern with `group()` after aggregation to create single table per query.

### Metrics Used

All 4 primary metrics combined:

- **InfluxDB:** `bandwidth` measurement - Download/upload bandwidth
- **InfluxDB:** `connections` measurement - Active connection count
- **InfluxDB:** `dns_query` measurement - DNS query count

### Data Collection Flow

1. **Router (GL-MT2500A):**
   - nlbwmon tracks bandwidth
   - Connection tracking via netstat/conntrack
   - dnsmasq logs DNS queries
2. **Export Scripts:** Multiple scripts send events to InfluxDB
3. **Telegraf:** Receives UDP packets on port 8094 (InfluxDB line protocol)
4. **InfluxDB:** Stores all metrics in "network" bucket
5. **Grafana:** Merges 4 Flux queries into single table view

## Current Configuration

### Display Settings

- **Format:** Table with sortable columns
- **Units:**
  - Download: bps (bits per second)
  - Upload: bps (bits per second)
  - Connections: short (count)
  - DNS Queries: short (count)
- **Default Sort:** Download (bps), descending
- **Filterable:** Yes - columns can be filtered
- **Excluded Columns:** Time, instance, job (hidden for clarity)

### Data Transformations Applied

1. **Merge:** Combines all 4 query results
2. **Organize:** Excludes internal labels, renames columns
3. **Rename:** Maps query results to friendly column names

### Time Range

- Uses: dashboard time range variable `$__range`
- Default: Last 1 hour
- Auto-refresh: Every 30 seconds

## What's Working Well

- ✅ Comprehensive view - all key metrics in one place
- ✅ Sortable columns - easy to find top users by any metric
- ✅ Filterable - can search for specific devices
- ✅ Shows ALL devices (not just top 10)
- ✅ Real-time updates
- ✅ Clean column names and units

## Current Gaps

- ❌ No trust scoring or risk indicators
- ❌ No cross-metric correlation analysis (e.g., high DNS + low bandwidth = suspicious)
- ❌ No baseline comparison (can't see if values are abnormal)
- ❌ No device type indicators
- ❌ No drill-down links to device detail dashboard
- ❌ No color-coding for suspicious patterns
- ❌ No upload/download ratio column
- ❌ No "last seen" timestamp

## Potential Improvements

### 1. Add Trust Score Column

**What:** Add trust score (1-10) for each device based on behavior
**How:** Calculate trust score from:

- Baseline adherence (40%): How close to normal behavior
- Threat intel clean (30%): No connections to known bad IPs/domains
- Device age (20%): Established devices higher trust
- Segmentation compliance (10%): In correct VLAN
Create new metric: `device_trust_score`
**Impact:** Instant visibility into which devices need investigation

### 2. Add Anomaly Indicators Column

**What:** Visual indicators for suspicious patterns
**How:** Add column showing:

- 🚨 High upload/download ratio (>50%)
- ⚠️ High DNS + low bandwidth (reconnaissance pattern)
- ⚠️ High connections + low bandwidth (scanning pattern)
- ⚠️ Device >3x baseline in any metric
Use cell color-coding or icon
**Impact:** Quickly spot compromised devices

### 3. Add Upload/Download Ratio Column

**What:** Show upload as percentage of download
**How:** Add query:

```promql
(
  sum by (device_name) (rate(client_bandwidth_bytes_total{direction="tx"}[$__range]))
  /
  sum by (device_name) (rate(client_bandwidth_bytes_total{direction="rx"}[$__range]))
) * 100
```

Display as "Upload %"
Normal: <10%, Suspicious: >50%
**Impact:** Detect data exfiltration patterns

### 4. Add Device Type and Category Columns

**What:** Show device type (IoT, Mobile, Workstation) and category (Camera, TV, Laptop)
**How:**

- Add device_type to `/root/etc/device-registry.conf`
- Include in metric labels
- Display as separate columns
**Impact:** Context for expected behavior - understand if metrics are normal for device type

### 5. Add Drill-Down Row Click

**What:** Click any row → navigate to device detail dashboard for that device
**How:** Configure table data link:

```json
{
  "dataLinks": [{
    "title": "Device Detail",
    "url": "http://localhost:3000/d/66bdd5ca-674b-46db-b177-59920156e784/device-detail?var-device=${__data.fields.device_name}"
  }]
}
```

**Impact:** One-click deep dive investigation

### 6. Add Baseline Deviation Columns

**What:** Show percent deviation from 7-day baseline for each metric
**How:** Add 4 more queries calculating deviation:

```promql
(current - avg_over_time(current[7d])) / avg_over_time(current[7d]) * 100
```

Display as "+X%" or "-X%" in separate columns or cell coloring
**Impact:** Immediately see which devices are behaving abnormally

## Related Panels

This is the **comprehensive overview panel** - it relates to all other panels:

- **Panel 1/2:** Bandwidth leaders shown here with all other metrics
- **Panel 3:** Time series trends summarized here as current values
- **Panel 4/5:** DNS metrics shown alongside bandwidth and connections
- **Panel 6:** Protocol distribution not shown per-device (gap)
- **Panel 8:** Connection count shown as column
- **Panel 9:** Domain information not correlated here (gap)

## Investigation Workflow

Use this table as the starting point for investigation:

### Step 1: Sort and Identify Outliers

1. **Sort by Download:** Find bandwidth hogs
2. **Sort by Upload:** Find potential exfiltration
3. **Sort by Connections:** Find scanning/botnet activity
4. **Sort by DNS:** Find reconnaissance or excessive queries

### Step 2: Cross-Metric Correlation Analysis

Look for suspicious combinations:

**Pattern 1: High DNS + Low Bandwidth**

- **Interpretation:** Device querying many domains but not downloading much
- **Likely:** Reconnaissance, scanning, DNS tunneling
- **Action:** Check Panel 5 (unique domains) and Panel 9 (which domains)

**Pattern 2: High Upload + High Connections**

- **Interpretation:** Device uploading to many destinations
- **Likely:** Data exfiltration, compromised device, botnet
- **Action:** Check Panel 9 (domains), investigate immediately

**Pattern 3: Low DNS + High Bandwidth**

- **Interpretation:** Downloading a lot but few DNS queries
- **Likely:** Either (1) streaming from cached/known IPs, or (2) direct IP connections (suspicious)
- **Action:** Check Panel 3 (over time) and Panel 9 (domains)

**Pattern 4: High Connections + Low Bandwidth + High DNS**

- **Interpretation:** Making many connections, querying many domains, but low data transfer
- **Likely:** Network scanning, port scanning, reconnaissance
- **Action:** Isolate device, check for scanning tools

### Step 3: Device Type Context

1. Compare metrics against expected values for device type:
   - **Mobile:** High DNS, moderate bandwidth, moderate connections = normal
   - **IoT:** Low DNS, low bandwidth, few connections = normal
   - **Workstation:** Moderate all metrics = normal
   - **Streaming:** High download, low upload, low DNS = normal
2. Flag devices outside expected ranges

### Step 4: Identify Priority Investigations

Create investigation list based on risk:

1. **Critical:** High upload + high connections (data exfiltration)
2. **High:** IoT device with high any metric (compromised)
3. **Medium:** Workstation with high DNS (scanning)
4. **Low:** Streaming device with high download (normal but worth checking)

## Common Scenarios & Responses

### Scenario 1: IoT Device with High Metrics

**Pattern:** Wyze Camera with 50 Mbps download, 20 Mbps upload, 150 connections, 200 DNS queries
**Expected:** <10 Mbps download, <5 Mbps upload, <20 connections, <20 DNS queries
**Analysis:** All metrics 5-10x normal = compromised
**Action:** Isolate to IoT VLAN immediately, investigate for botnet

### Scenario 2: Workstation with High Upload/Download Ratio

**Pattern:** Laptop with 20 Mbps download, 15 Mbps upload (75% ratio)
**Expected:** Ratio <10%
**Analysis:** Upload nearly equal to download = suspicious
**Action:** Check Panel 9 for upload destinations, investigate for exfiltration

### Scenario 3: Unknown Device in Table

**Pattern:** Device "a0:66:2b" (partial MAC) appears with high bandwidth
**Analysis:** New/unidentified device
**Action:**

1. Check router DHCP leases for full MAC
2. Lookup MAC OUI for manufacturer
3. Add to device registry if legitimate
4. Move to guest network if unidentified

### Scenario 4: Mobile Device with Normal-Looking Metrics

**Pattern:** iPhone with 30 Mbps download, 3 Mbps upload, 120 connections, 250 DNS queries
**Analysis:** All metrics within normal range for mobile device
**Action:** No investigation needed

### Scenario 5: Server with All Metrics High

**Pattern:** Macmini (server) with 100 Mbps download, 80 Mbps upload, 500 connections, 1000 DNS queries
**Analysis:** Server metrics depend on function
**Action:** Verify this is expected for server role (e.g., running services, backups)

## Files Referenced

- **Dashboard JSON:** `grafana-dashboards/client-monitoring.json` (lines 236-337, Panel ID 7)
- **Telegraf Config:** UDP listener on port 8094 for InfluxDB line protocol
- **Router Export Scripts:** Multiple scripts on GL-MT2500A
  - `/root/bin/send-bandwidth-to-influx.sh` (bandwidth)
  - `/root/bin/send-dns-to-influx.sh` (DNS)
  - Connection tracking script sending to InfluxDB
- **Device Registry:** `/root/etc/device-registry.conf` (device naming)
- **Python Report:** `/Users/kirkl/bin/generate-client-report` (similar table structure)
