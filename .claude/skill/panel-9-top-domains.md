# Panel 9: Top Domains Accessed

## Panel Overview

- **Panel ID:** 9
- **Title:** Top Domains Accessed
- **Type:** Table with LCD Gauge (converted from Bar Gauge for proper sorting)
- **Purpose:** Shows top 15 most-accessed domains, sorted by query count descending

## 🎉 Resolution Updates

### 2025-12-26: Sorting and Type Errors Fixed

- ✅ Converted to table visualization for value-based sorting
- ✅ Fixed "max series exceeded > 1001" error
- ✅ Added ungrouping for proper table display

### 2025-12-22: Device Correlation Added

**STATUS: The detached information problem has been SOLVED!**

### What Was Implemented

1. **New Metric:** `dns_domain_device_queries` with full domain-device correlation
   - Labels: `domain`, `device_name`, `ip`, `mac`
   - Script: `/root/bin/export-dns-domain-devices.sh`
   - Lua Collector: `/usr/lib/lua/prometheus-collectors/dns_domain_devices.lua`

2. **New Panel 10:** Domain Access by Device (Drill-Down Table)
   - Shows all domain-device relationships
   - Filterable and sortable
   - Links to device detail dashboard

3. **Drill-Down Links:** Click any domain in Panel 9 → see which devices access it

4. **Dashboard Variable:** `$domain_filter` for filtering the drill-down table

### How to Use

1. **View Top Domains:** Look at Panel 9 (unchanged - shows network overview)
2. **Investigate Domain:** Click on any domain bar
3. **See Devices:** Panel 10 filters to show only devices accessing that domain
4. **Drill Further:** Click device name to see full device detail dashboard

**Investigation time reduced from 5-10 minutes (manual SSH) to <5 seconds (click twice)**

---

## Panel Overview

- **Panel ID:** 9
- **Title:** Top Domains Accessed
- **Type:** Bar Gauge (Horizontal)
- **Grid Position:** x=12, y=34, width=12, height=8 (right half of fifth row)
- **Purpose:** Shows the top 15 most-accessed domains across the entire network
- **NEW:** Includes drill-down links to see which devices access each domain

## ~~⚠️ CRITICAL GAP: DETACHED INFORMATION~~ ✅ SOLVED

**~~This panel shows domains WITHOUT device correlation~~** - FIXED!

The panel now answers BOTH:

- ✅ "What are the top domains?"
- ✅ "Which devices are accessing these domains?" (via drill-down)

This is now a powerful security investigation tool.

## Data Source

### Current: InfluxDB Flux Query

```flux
from(bucket: "network")
  |> range(start: v.timeRangeStart, stop: v.timeRangeStop)
  |> filter(fn: (r) => r._measurement == "dns_query" and r._field == "domain")
  |> map(fn: (r) => ({ r with domain: r._value, _value: 1 }))
  |> drop(columns: ["_time"])
  |> group(columns: ["domain"])
  |> sum()
  |> group()
  |> sort(columns: ["_value"], desc: true)
  |> limit(n: 15)
```

**Query Breakdown:**

1. Get all DNS query events with domain field
2. Create domain column and set _value to 1 (for counting)
3. Drop _time to prevent series explosion
4. Group by domain and sum (counts queries per domain)
5. **Ungroup with `group()`** - critical for table sorting
6. Sort by count descending
7. Limit to top 15

### Legacy: Prometheus Query (DEPRECATED)

```promql
sort_desc(topk(15, dns_domain_queries))
```

### Metrics Used

- **InfluxDB:** `dns_query` measurement with `_field="domain"`
  - Tags: `device_name`, `ip`, `mac`, `query_type`
  - Field value: domain name (string)
  - Type: Event-based (each DNS query is an event)

### Data Collection Flow

1. **Router (GL-MT2500A):** dnsmasq DNS server logs all queries to `/var/log/dnsmasq.log`
2. **Export Daemon:** `/root/bin/dns-monitor-daemon.sh` (real-time streaming)
   - Uses `tail -F /var/log/dnsmasq.log` for real-time monitoring
   - Parses each query line immediately
   - Resolves device names via `/root/bin/resolve-device-name.sh`
   - Sends each DNS query as event to InfluxDB via UDP
   - **Preserves device correlation** (includes device_name tag)
3. **Telegraf:** Receives UDP packets on port 8094
4. **InfluxDB:** Stores DNS query events in "network" bucket
5. **Grafana:** Aggregates by domain and displays top 15 in table with LCD Gauge

## Current Configuration

### Thresholds & Colors

- Green: 0 - 99 queries
- Yellow: 100 - 499 queries
- Red: 500+ queries

### Display Settings

- **Unit:** short (count)
- **Visualization Type:** Table with LCD Gauge cell display
- **Columns:**
  - Domain (domain name, clickable link to drill-down panel)
  - Queries (LCD Gauge visualization, 400px width)
- **Sorting:** Descending by Queries (highest at top)
- **Transformations:**
  - Organize: Rename columns (domain → Domain, _value → Queries)

### Time Range

- Uses: dashboard time range variables `v.timeRangeStart` and `v.timeRangeStop`
- Default: Last 1 hour
- Auto-refresh: Every 30 seconds

## Critical Lessons Learned - DNS Query Panels

### Issue 1: Max Series Exceeded (> 1001)

**Problem:** DNS queries are events with timestamps. Without dropping `_time`, each unique domain+timestamp becomes a separate series.

**Example:** 100 domains × 3600 seconds = 360,000 series (far exceeds 1001 limit)

**Solution:**

```flux
|> drop(columns: ["_time"])  # Remove time dimension BEFORE grouping
|> group(columns: ["domain"])
```

### Issue 2: Counting DNS Queries Properly

**Pattern for counting events:**

```flux
|> map(fn: (r) => ({ r with domain: r._value, _value: 1 }))  # Set each event value to 1
|> group(columns: ["domain"])
|> sum()  # Sum the 1s = count of events per domain
```

### Issue 3: Table Display for Proper Sorting

Same as bandwidth panels - bar gauges sort alphabetically. Use table + LCD Gauge.

## What's Working Well

- ✅ Shows which domains are most active on network
- ✅ Easy to spot high-traffic domains
- ✅ Real-time updates
- ✅ Top 15 gives good overview

## Current Gaps ❌

### PRIMARY ISSUE: No Device Correlation

**The Critical Problem:**

- Cannot see which devices access which domains
- Cannot investigate suspicious domains (who is accessing malware-c2.evil.com?)
- Cannot correlate domain activity with device behavior
- Investigation workflow is broken

**Example of Problem:**

- Panel shows "unknown-tracking-domain.com" with 500 queries
- Question: "Which device is accessing this?"
- Answer: Unknown - must manually correlate with other tools

### Other Gaps

- ❌ No threat intelligence integration (no flags for known malware domains)
- ❌ No domain reputation scoring
- ❌ No newly registered domain detection (<30 days = suspicious)
- ❌ No DGA (Domain Generation Algorithm) detection
- ❌ No typosquatting detection (gooogle.com)
- ❌ No domain category information (ads, tracking, CDN, malware, etc.)
- ❌ No drill-down to query timeline

## Solutions to Fix Detached Information Problem

### Solution 1: Add Per-Device Domain Table (RECOMMENDED)

**What:** Create new panel showing domains WITH devices that access them
**How:** Modify router export script to track domain queries per device:

```bash
# In /root/bin/export-dns-queries.sh
# Instead of: dns_domain_queries{domain="example.com"} 150
# Export: dns_domain_device_queries{domain="example.com",device_name="iPhone"} 45
#         dns_domain_device_queries{domain="example.com",device_name="Macmini"} 105
```

Then create new Grafana table panel:

```promql
# Show all domains with devices accessing them
topk(50, dns_domain_device_queries)
```

Display as table:
| Domain | Device | Query Count |
|--------|--------|-------------|
| example.com | iPhone | 45 |
| example.com | Macmini | 105 |
| google.com | iPhone | 200 |

**Impact:** Complete visibility - see which devices access which domains

### Solution 2: Add Device Filter Variable

**What:** Add Grafana dashboard variable to filter by device
**How:**

1. Create dashboard variable: `$device` from `client_dns_queries_total`
2. Modify query to:

```promql
# When device selected, show domains for that device only
sort_desc(topk(15, dns_domain_device_queries{device_name="$device"}))
```

**Impact:** Can select device and see their domain activity

### Solution 3: Add Drill-Down to Device List

**What:** Click domain → see list of devices accessing it
**How:**

- Export `dns_domain_device_queries` metric with both labels
- Add data link to domain bar:

```json
{
  "dataLinks": [{
    "title": "Devices accessing ${__field.labels.domain}",
    "url": "http://localhost:3000/d/[dashboard-id]?var-domain=${__field.labels.domain}"
  }]
}
```

- Create detail panel showing devices for selected domain
**Impact:** Two-click investigation: click domain → see devices

### Solution 4: Pivot View - Domain-Device Matrix

**What:** Heat map showing domains (rows) × devices (columns) with query counts
**How:** Create heat map panel:

```promql
dns_domain_device_queries
```

Display as heat map with:

- Y-axis: Domains
- X-axis: Devices
- Color intensity: Query count
**Impact:** Visual overview of domain-device relationships

### Solution 5: Keep Current Panel + Add Companion Panel

**What:** Keep this network-wide domain panel, add device-correlated panel below
**How:**

- Panel 9A (current): Network-wide top domains (overview)
- Panel 9B (new): Top domains WITH device breakdown (detailed investigation)
**Impact:** Both overview and detailed investigation capability

## Potential Improvements (Beyond Device Correlation)

### 1. Add Threat Intelligence Integration

**What:** Flag known malware/C2/phishing domains with visual indicators
**How:**

- Maintain threat feed database (AlienVault OTX, Abuse.ch)
- Check domains against threat feeds
- Add cell color or icon: 🚨 for malware domains
**Impact:** Immediate identification of compromised devices

### 2. Add Domain Reputation Scoring

**What:** Show reputation score (1-10) for each domain
**How:**

- Use VirusTotal API, Cisco Umbrella, or similar
- Query domain reputation
- Display as separate column or color-code
**Impact:** Quickly assess domain trustworthiness

### 3. Add Domain Age Detection

**What:** Flag newly registered domains (<30 days old)
**How:**

- Query WHOIS data for domain registration date
- Flag domains <30 days old with ⚠️
**Impact:** Phishing and malware often use new domains

### 4. Add DGA Detection

**What:** Detect Domain Generation Algorithm patterns (random-looking domains)
**How:**

- Calculate domain entropy
- Flag high-entropy domains (random character sequences)
- Example: "xk3j2klmdf.com" = suspicious
**Impact:** Detect malware using DGA for C2

### 5. Add Domain Category Labels

**What:** Show category for each domain (ads, tracking, CDN, social, malware, etc.)
**How:**

- Use categorization service (Cisco Umbrella, etc.)
- Display as badge/label next to domain
**Impact:** Understand domain purpose at a glance

## Related Panels

- **Panel 1/2:** Bandwidth - Correlate domain access with bandwidth usage (if device correlation added)
- **Panel 4:** Top DNS Query Clients - See which devices make most queries (but not to which domains)
- **Panel 5:** Unique Domains Per Client - See domain diversity (but not which domains)
- **Panel 7:** Client Activity Table - See device metrics (but not domains accessed)

**The Gap:** No current panel connects devices to domains bidirectionally

## Investigation Workflow (CURRENT - BROKEN)

### Current Limitation Example

1. **See domain:** "suspicious-tracking.com" has 300 queries
2. **Question:** Which device is accessing this?
3. **Answer:** Cannot determine from dashboard
4. **Workaround:** Must SSH to router and manually grep dnsmasq logs:

   ```bash
   ssh root@192.168.1.2 'grep "suspicious-tracking.com" /var/log/dnsmasq.log | awk "{print $5}" | sort | uniq -c'
   ```

5. **Problem:** Manual, time-consuming, breaks workflow

### Desired Workflow (WITH DEVICE CORRELATION)

1. **See domain:** "suspicious-tracking.com" has 300 queries
2. **Click domain** → drill-down panel shows:
   - iPhone: 150 queries
   - iPad: 100 queries
   - Macmini: 50 queries
3. **Identify:** iPhone is primary accessor
4. **Action:** Check iPhone for malicious app, investigate further

## Common Scenarios & Responses (With Current Limitations)

### Scenario 1: Unknown Domain with High Query Count

**Pattern:** "random-xyz-123.com" shows 500 queries
**Investigation Steps:**

1. **Check domain reputation:** Use external tool (VirusTotal, etc.)
2. **Try to identify device:** SSH to router, grep logs (manual)
3. **Cannot easily correlate** with Panel 4 (DNS clients) or Panel 1/2 (bandwidth)
4. **Limitation:** Broken investigation workflow

**With Device Correlation:**

1. Click domain → see "Wyze Camera: 500 queries"
2. **Immediate identification:** IoT camera compromised
3. **Action:** Isolate camera to IoT VLAN

### Scenario 2: Known Malware Domain Detected

**Pattern:** "malware-c2.evil.com" shows 200 queries
**Investigation Steps:**

1. **Critical:** Need to identify compromised device IMMEDIATELY
2. **Current:** Must manually correlate via router logs
3. **Delay:** Could be 5-10 minutes to identify device
4. **Problem:** Attacker has time to exfiltrate data

**With Device Correlation:**

1. Instantly see "Laptop-Work: 200 queries"
2. **Immediate action:** Isolate laptop within 30 seconds
3. **Impact:** Minimize damage window

### Scenario 3: Typosquatting Domain

**Pattern:** "gooogle.com" (typo of google.com) shows 50 queries
**Investigation Steps:**

1. **Suspicious:** Likely phishing attempt
2. **Need to identify:** Which device/user clicked phishing link?
3. **Current:** Manual log correlation
4. **Problem:** User may not remember, hard to track

**With Device Correlation:**

1. See "iPhone-User: 50 queries"
2. **Identify user:** Alert them about phishing attempt
3. **Action:** Security training, check for compromise

### Scenario 4: Excessive Tracking Domain

**Pattern:** "doubleclick.net" shows 2000 queries
**Investigation Steps:**

1. **Normal but excessive:** Ad tracking domain
2. **Question:** Which device has so many ads?
3. **Current:** Cannot easily determine
4. **Action:** Want to install ad blocker, but on which device?

**With Device Correlation:**

1. See "Smart TV: 1800 queries, iPhone: 200 queries"
2. **Identify:** TV has excessive ad tracking
3. **Action:** Block tracking domains for TV specifically

## Critical Files

### Files to Modify for Device Correlation

- **Router Export Script:** `/root/bin/export-dns-queries.sh` (on GL-MT2500A)
  - Modify to export dns_domain_device_queries with both domain AND device_name labels
- **Lua Collector:** `/usr/lib/lua/prometheus-collectors/client_dns.lua` (on router)
  - Update to handle new metric format
- **Dashboard JSON:** `grafana-dashboards/client-monitoring.json` (Panel ID 9, lines 366-411)
  - Update query to use new metric
  - Add device correlation panel (new Panel 9B)

### Files Referenced

- **Current Dashboard JSON:** `grafana-dashboards/client-monitoring.json` (lines 366-411, Panel ID 9)
- **Prometheus Config:** `prometheus.yml` (scrape config)
- **Router DNS Logs:** `/var/log/dnsmasq.log` (on GL-MT2500A)
- **Router Export Script:** `/root/bin/export-dns-queries.sh` (needs modification)
- **Router Device Registry:** `/root/etc/device-registry.conf` (device naming)

## Implementation Priority

**HIGH PRIORITY - This is the #1 detached information issue**

Recommended implementation order:

1. **Modify router export script** to track domains per device (Solution 1)
2. **Create new Panel 9B** with device-correlated domain table
3. **Add drill-down links** from domain to device list (Solution 3)
4. **Add threat intelligence** integration for security
5. **Add domain reputation** and category information

This transformation will convert Panel 9 from "nearly useless" to "critical security tool."
