# Panel 5: Unique Domains Per Client

## Panel Overview

- **Panel ID:** 5
- **Title:** Unique Domains Per Client
- **Type:** Table with LCD Gauge (converted from Bar Gauge - 2025-12-26)
- **Grid Position:** x=8, y=16, width=8, height=8 (middle third of third row)
- **Purpose:** Shows the top 10 clients by number of unique domains accessed, sorted descending

## Critical Fixes Applied (2025-12-26)

1. **Converted to table** with LCD Gauge for proper value-based sorting
2. **Added ungrouping** with `group()` after `count()` to create single sortable table
3. **Added `drop(columns: ["_time"])`** to prevent max series exceeded error

**Working Query Pattern:**

```flux
from(bucket: "network")
  |> range(start: v.timeRangeStart, stop: v.timeRangeStop)
  |> filter(fn: (r) => r._measurement == "dns_query" and r._field == "domain")
  |> drop(columns: ["_time"])
  |> group(columns: ["device_name"])
  |> distinct(column: "_value")  # Get unique domains
  |> count()                      # Count how many unique
  |> group()                      # Ungroup for table
  |> sort(columns: ["_value"], desc: true)
  |> limit(n: 10)
```

## Data Source

### Prometheus Query

```promql
sort_desc(topk(10, client_dns_unique_domains))
```

### Metrics Used

- `client_dns_unique_domains` - Count of unique domains accessed per client
  - Labels: `device_name`, `ip`
  - Type: Gauge (current count)

### Data Collection Flow

1. **Router (GL-MT2500A):** dnsmasq DNS server logs all queries
2. **Export Script:** `/root/bin/export-dns-queries.sh`
   - Parses dnsmasq logs
   - Counts unique domains per client IP (distinct domain names)
   - Resolves device names via `/root/bin/resolve-device-name.sh`
   - Execution time: < 5 seconds
3. **Lua Collector:** `/usr/lib/lua/prometheus-collectors/client_dns.lua`
   - Exports metrics on port 9100
4. **Prometheus:** Scrapes router:9100 every 30 seconds
5. **Grafana:** Queries Prometheus and visualizes in bar gauge

## Current Configuration

### Thresholds & Colors

- Green: 0 - 99 unique domains
- Yellow: 100 - 499 unique domains
- Red: 500+ unique domains

**Note:** Thresholds are same as Panel 4 (query count) but meaning is different - high unique domains could indicate scanning.

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

- ✅ Shows domain diversity per device
- ✅ Helps identify scanning/reconnaissance behavior
- ✅ Device names are meaningful
- ✅ Real-time updates
- ✅ Simple metric easy to understand

## Current Gaps

- ❌ No device type context (mobile vs IoT expected ranges differ greatly)
- ❌ No baseline comparison (sudden increase in unique domains = scanning)
- ❌ No correlation with total query count (high unique domains + low queries = suspicious)
- ❌ No drill-down to see which domains
- ❌ No newly-seen domain tracking (first time accessing domain)
- ❌ No domain category breakdown (ads, CDN, social, malware, etc.)

## Potential Improvements

### 1. Add Device Type Expected Range Overlay

**What:** Show expected unique domain ranges based on device type
**How:**

- Tag devices with type in registry
- Add visual indicators:
  - **Mobile devices:** 100-500 unique domains (many apps, services)
  - **Workstations:** 50-200 unique domains (browsing, work tools)
  - **IoT devices:** 5-20 unique domains (should only contact manufacturer)
  - **Smart TVs:** 10-30 unique domains (streaming services, updates)
  - **Servers:** Varies based on purpose
- Color-code based on deviation from expected range
**Impact:** Immediately spot anomalies - IoT with 200 unique domains = likely compromised

### 2. Add Query Count Ratio Analysis

**What:** Show unique domains as percentage of total queries
**How:** Add second visualization showing ratio:

```promql
client_dns_unique_domains / client_dns_queries_total{query_type="all"} * 100
```

- **High ratio (>50%):** Each query is to different domain = scanning
- **Low ratio (<10%):** Repeated queries to same domains = normal or beaconing
**Impact:** Detect reconnaissance behavior

### 3. Add Baseline Comparison

**What:** Compare current unique domains to device's 7-day average
**How:** Add query:

```promql
(
  client_dns_unique_domains
  /
  avg_over_time(client_dns_unique_domains[7d])
) * 100 - 100
```

**Impact:** Detect sudden increases (>200% = suspicious)

### 4. Add Domain Category Breakdown

**What:** Show categories of domains accessed (ads, social, CDN, unknown, etc.)
**How:** (Requires domain categorization)

- Maintain domain category database
- Track unique domains per category per device
- Export metrics: `client_unique_domains_by_category{category="ads"}`
**Impact:** Understand device behavior - high ads category = normal browsing, high unknown = suspicious

### 5. Add New Domain Tracker

**What:** Track first-time domain accesses (never seen before)
**How:**

- Track historical domains per device
- Flag domains accessed for first time
- Export metric: `client_new_domains_count`
**Impact:** Sudden spike in new domains = reconnaissance or compromise

## Related Panels

- **Panel 4:** Top DNS Query Clients - Compare query count to unique domain count
- **Panel 1/2:** Bandwidth - High unique domains + high bandwidth = data collection
- **Panel 7:** Client Activity Table - See full device metrics
- **Panel 9:** Top Domains - See which specific domains are being accessed

## Investigation Workflow

When you see high unique domain count:

### Step 1: Check Device Type

1. **Identify device:** Mobile, workstation, IoT, server?
2. **Expected unique domains:**
   - Mobile: 100-500 = normal (many apps)
   - Workstation: 50-200 = normal (browsing + tools)
   - IoT: 5-20 = normal (limited function)
   - Smart TV: 10-30 = normal (streaming services)
   - Server: Varies

### Step 2: Calculate Query-to-Unique-Domain Ratio

1. **Check Panel 4:** How many total DNS queries?
2. **Calculate ratio:** unique_domains / total_queries
3. **Interpret:**
   - **> 50% ratio:** Each query is to different domain = scanning/reconnaissance
   - **10-50% ratio:** Some repeated queries = normal with variety
   - **< 10% ratio:** Mostly repeated queries = normal or beaconing

### Step 3: Correlate with Other Metrics

1. **Check Panel 1/2 (Bandwidth):**
   - High unique domains + high bandwidth = data collection (normal or malicious)
   - High unique domains + low bandwidth = reconnaissance scanning
2. **Check Panel 8 (Connections):**
   - High unique domains + high connections = scanning for open services
   - High unique domains + low connections = normal app behavior

### Step 4: Check Panel 9 for Actual Domains

1. See what domains are being accessed
2. Look for patterns:
   - Many similar domains (cdn1.example.com, cdn2.example.com) = normal CDN
   - Random-looking domains = DGA malware
   - Newly registered domains = suspicious
3. Check domain categories

### Step 5: Determine Action

- **Normal:** Mobile device with 200 unique domains to known services/apps
- **Investigate:** IoT device with >50 unique domains
- **Monitor:** Workstation with sudden increase in unique domains
- **Isolate:** Device with high unique domains to suspicious/unknown domains

## Common Scenarios & Responses

### Scenario 1: iPhone with 300 Unique Domains

**Investigation:**

1. Mobile devices access many services (apps, ads, analytics, CDNs)
2. 300 unique domains = normal for active smartphone
3. **Check Panel 9:** Should see mix of common services (apple.com, google.com, facebook.com, ads, CDNs)
4. **Action:** Normal behavior

### Scenario 2: Wyze Camera with 100 Unique Domains

**Investigation:**

1. IoT cameras should only contact manufacturer (wyze.com) and maybe CDNs
2. 100 unique domains = 5-10x normal = highly suspicious
3. **Possible causes:**
   - Compromised camera used for reconnaissance
   - Botnet scanning for targets
   - Malware installed on camera
4. **Check Panel 9:** If not all wyze.com related = compromised
5. **Action:** Isolate to IoT VLAN immediately, investigate firmware

### Scenario 3: Workstation with High Ratio (80%)

**Investigation:**

1. 80% of queries are to unique domains = each query is different domain
2. This is scanning pattern, not normal browsing
3. **Check Panel 4:** Likely also high total query count
4. **Check Panel 9:** Look for patterns:
   - Sequential IPs (1.1.1.1, 1.1.1.2, 1.1.1.3) = IP scanning
   - Random subdomains = scanning subdomains
   - Random domains = DGA malware
5. **Action:** Investigate workstation for malware or unauthorized scanning tool

### Scenario 4: Smart TV with Sudden Increase

**Investigation:**

1. Note previous average (e.g., 15 unique domains)
2. Current count (e.g., 80 unique domains) = 5x increase
3. **Possible causes:**
   - New app installed (legitimate)
   - Firmware update checking multiple CDNs (legitimate but noisy)
   - Compromised TV (malicious)
4. **Check Panel 9:** Are new domains related to known services/CDNs?
5. **Check timing:** If increase during known firmware update time = likely legitimate
6. **Action:** Monitor, consider blocking non-essential domains for privacy

## Files Referenced

- **Dashboard JSON:** `grafana-dashboards/client-monitoring.json` (lines 175-202, Panel ID 5)
- **Prometheus Config:** `prometheus.yml` (scrape config)
- **Router Export Script:** `/root/bin/export-dns-queries.sh` (on GL-MT2500A)
- **Router DNS Logs:** dnsmasq logs (source data)
- **Router Device Registry:** `/root/etc/device-registry.conf` (device naming)
- **Lua Collector:** `/usr/lib/lua/prometheus-collectors/client_dns.lua` (on router)
