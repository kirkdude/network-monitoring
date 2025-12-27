# Panel 4: Top DNS Query Clients

## Panel Overview

- **Panel ID:** 4
- **Title:** Top DNS Query Clients
- **Type:** Table with LCD Gauge (converted from Bar Gauge - 2025-12-26)
- **Grid Position:** x=0, y=16, width=8, height=8 (left third of third row)
- **Purpose:** Shows the top 10 clients by total DNS query count, sorted by value descending

## Critical Fixes Applied (2025-12-26)

1. **Converted to table** with LCD Gauge for proper value-based sorting (bar gauges sort alphabetically)
2. **Added ungrouping** with `group()` after `count()` to create single sortable table
3. **Added `drop(columns: ["_time"])`** to prevent max series exceeded error

**Working Query Pattern:**

```flux
from(bucket: "network")
  |> range(start: v.timeRangeStart, stop: v.timeRangeStop)
  |> filter(fn: (r) => r._measurement == "dns_query")
  |> drop(columns: ["_time"])
  |> group(columns: ["device_name"])
  |> count()
  |> group()  # Ungroup for table display
  |> sort(columns: ["_value"], desc: true)
  |> limit(n: 10)
```

## Data Source

### Prometheus Query

```promql
sort_desc(topk(10, client_dns_queries_total{query_type="all"}))
```

### Metrics Used

- `client_dns_queries_total{query_type="all"}` - Total DNS queries per client
  - Labels: `device_name`, `ip`, `query_type`
  - Type: Counter (cumulative)
  - Query types: A, AAAA, PTR, CNAME, MX, TXT, etc.

### Data Collection Flow

1. **Router (GL-MT2500A):** dnsmasq DNS server logs all queries
2. **Export Script:** `/root/bin/export-dns-queries.sh`
   - Parses dnsmasq logs
   - Aggregates queries per client IP
   - Resolves device names via `/root/bin/resolve-device-name.sh`
   - Execution time: < 5 seconds
3. **Lua Collector:** `/usr/lib/lua/prometheus-collectors/client_dns.lua`
   - Invoked by prometheus-node-exporter-lua
   - Exports metrics on port 9100
4. **Prometheus:** Scrapes router:9100 every 30 seconds
5. **Grafana:** Queries Prometheus and visualizes in bar gauge

## Current Configuration

### Thresholds & Colors

- Green: 0 - 99 queries
- Yellow: 100 - 499 queries
- Red: 500+ queries

### Display Settings

- **Unit:** short (count)
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
- ✅ Color-coded thresholds highlight excessive DNS activity
- ✅ Top 10 focus on highest-activity devices
- ✅ Real-time updates capture DNS patterns
- ✅ Query count gives good indicator of device activity level

## Current Gaps

- ❌ No drill-down to see which domains are being queried
- ❌ No threat intelligence integration (no check against known malware domains)
- ❌ No DNS tunneling detection (long subdomains, high entropy)
- ❌ No DGA (Domain Generation Algorithm) detection
- ❌ No device type context (mobile vs IoT expected query counts differ)
- ❌ No query type breakdown (A vs AAAA vs PTR)
- ❌ No failed query tracking (NXDOMAIN responses)

## Potential Improvements

### 1. Add Drill-Down to Queried Domains

**What:** Click device → see top domains queried by that device
**How:** Add data link:

```json
{
  "dataLinks": [{
    "title": "View DNS Activity",
    "url": "http://localhost:3000/d/c49d4df6-1edc-4998-bb71-95b81a909ece?var-device=${__field.labels.device_name}"
  }]
}
```

And create DNS detail panel filtered by device
**Impact:** Investigate what specific domains high-query devices are accessing

### 2. Add Device Type Expected Range Overlay

**What:** Show expected DNS query ranges for device type
**How:**

- Tag devices with type in registry (mobile, iot, workstation)
- Add annotation showing typical ranges:
  - Mobile: 100-500 queries/hour (many apps)
  - Workstation: 50-200 queries/hour
  - IoT: 5-20 queries/hour (should be minimal)
  - Smart TV: 10-30 queries/hour
**Impact:** Quickly spot anomalies - IoT device with 500 queries = compromised

### 3. Add Failed Query Counter

**What:** Show count of NXDOMAIN (domain not found) responses
**How:** Add second metric from router:

```promql
client_dns_failed_queries_total
```

Display as overlay or separate column
**Impact:** High failed queries = DGA malware, typosquatting, or misconfiguration

### 4. Add DNS Tunneling Detection

**What:** Flag devices with suspicious DNS patterns (tunneling exfiltration)
**How:** (Requires router-side analysis)

- Detect queries with:
  - Very long subdomains (>50 chars)
  - High entropy in subdomain (random-looking)
  - Unusual query frequency to single domain
- Export as separate metric: `dns_tunneling_score`
**Impact:** Detect data exfiltration via DNS (bypasses firewall)

### 5. Add Threat Intelligence Integration

**What:** Flag devices querying known malware/C2 domains
**How:** (Requires threat feed integration)

- Maintain list of known bad domains (AlienVault OTX, Abuse.ch)
- Check queried domains against list
- Export metric: `client_malicious_dns_queries_total`
- Add to panel with critical threshold
**Impact:** Immediate detection of compromised devices

## Related Panels

- **Panel 1:** Top Bandwidth Download - High DNS + high bandwidth = scanning or data collection
- **Panel 2:** Top Bandwidth Upload - High DNS + high upload = possible exfiltration
- **Panel 5:** Unique Domains Per Client - Compare query count to unique domain count
- **Panel 7:** Client Activity Table - See full device profile with all metrics
- **Panel 9:** Top Domains Accessed - See what domains are being queried most

## Investigation Workflow

When you see excessive DNS queries:

### Step 1: Identify Device Type

1. **Check device name:** Is it mobile, workstation, IoT, or server?
2. **Expected queries:**
   - Mobile (iPhone, Android): 100-500/hour = normal
   - Workstation (laptop, desktop): 50-200/hour = normal
   - IoT (camera, sensor, smart home): 5-20/hour = normal
   - Server: 500-2000/hour = depends on function

### Step 2: Correlate with Other Metrics

1. **Check Panel 5 (Unique Domains):**
   - High queries + high unique domains = scanning/reconnaissance
   - High queries + low unique domains = repeated queries to same domain (beaconing?)
2. **Check Panel 1/2 (Bandwidth):**
   - High DNS + low bandwidth = DNS tunneling (exfiltration via DNS)
   - High DNS + high bandwidth = normal data-heavy application
3. **Check Panel 8 (Connections):**
   - High DNS + high connections = scanning
   - High DNS + low connections = normal app with many service dependencies

### Step 3: Check Panel 9 for Queried Domains

1. See what domains the device is querying
2. Check for:
   - Known malware domains
   - Newly registered domains (<30 days old)
   - Random-looking domains (DGA pattern)
   - Typosquatting domains (gooogle.com)
3. Check domain categories - advertising, analytics, CDN, social media, etc.

### Step 4: Determine Action

- **Normal:** Mobile device, queries to known app/service domains
- **Investigate:** IoT device with >50 queries/hour, unknown domains
- **Isolate:** Any device querying known malware domains
- **Monitor:** Workstation with increased queries over time

## Common Scenarios & Responses

### Scenario 1: iPhone with 400 DNS Queries/Hour

**Investigation:**

1. Mobile devices make many DNS queries (apps, background services, ads)
2. 400 queries/hour = normal for active mobile device
3. **Check Panel 5:** Should have 100-300 unique domains (many apps)
4. **Action:** Normal behavior, no investigation needed

### Scenario 2: IoT Camera with 200 DNS Queries/Hour

**Investigation:**

1. IoT devices should have minimal DNS activity (5-20 queries/hour)
2. 200 queries = 10x normal = highly suspicious
3. **Check Panel 9:** Should only query manufacturer domain (wyze.com, ring.com)
4. If querying many domains or unknown domains = compromised
5. **Action:** Isolate to IoT VLAN immediately, investigate for botnet

### Scenario 3: Workstation with Suddenly Increased DNS Queries

**Investigation:**

1. Note previous average (e.g., 100 queries/hour)
2. Current queries (e.g., 500 queries/hour) = 5x increase
3. **Possible causes:**
   - Malware performing network scanning
   - DNS tunneling exfiltration
   - DGA malware generating random domains
4. **Check Panel 5 (Unique Domains):** If also increased = scanning
5. **Check Panel 9:** Look for random-looking domains or known bad domains
6. **Action:** Investigate workstation for compromise

### Scenario 4: New Device with High DNS, Zero Unique Domains

**Investigation:**

1. High queries to same domain repeatedly = suspicious
2. Could be:
   - Beaconing to C2 server
   - DNS tunneling (using DNS queries to exfiltrate data)
   - Misconfigured application
3. **Check Panel 9:** What domain is being queried?
4. **Action:** Investigate domain reputation, monitor or block

## Files Referenced

- **Dashboard JSON:** `grafana-dashboards/client-monitoring.json` (lines 129-174, Panel ID 4)
- **Prometheus Config:** `prometheus.yml` (scrape config for router:9100)
- **Router Export Script:** `/root/bin/export-dns-queries.sh` (on GL-MT2500A)
- **Router DNS Logs:** dnsmasq logs on router (source data)
- **Router Device Registry:** `/root/etc/device-registry.conf` (device naming)
- **Lua Collector:** `/usr/lib/lua/prometheus-collectors/client_dns.lua` (on router)
- **Python Report:** `/Users/kirkl/bin/generate-client-report` (similar queries)
