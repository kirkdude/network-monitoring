# Streaming Panel 13: Recent DNS Queries (Streaming Domains)

## Panel Overview

- **Panel ID:** 8
- **Title:** Recent DNS Queries (Streaming Domains)
- **Type:** Table
- **Grid Position:** x=0, y=50, width=24, height=10 (full width, bottom of dashboard)
- **Purpose:** Activity log showing the 100 most recent DNS queries to streaming domains, providing timeline context for troubleshooting and correlation with bandwidth/QoS events

## Data Source

### Current: InfluxDB Flux Query

```flux
from(bucket: "network")
  |> range(start: v.timeRangeStart, stop: v.timeRangeStop)
  |> filter(fn: (r) => r._measurement == "dns_query" and r._field == "domain")
  |> filter(fn: (r) => r._value =~ /netflix|disney|amazon|hulu|hbo|youtube|googlevideo|twitch|spotify|apple.*tv|paramount|peacock|pluto|roku/)
  |> group()
  |> keep(columns: ["_time", "device_name", "_value", "query_type"])
  |> sort(columns: ["_time"], desc: true)
  |> limit(n: 100)
```

**Query Breakdown:**

1. **Filter streaming domain DNS queries** using regex
2. **Keep essential columns:** Time, Device, Domain, Query Type
3. **Sort by time** descending (newest first)
4. **Limit to 100** most recent queries

## Current Configuration

### Display Settings

- **Visualization:** Table
- **Columns:**
  - Time (_time) → "Time"
  - Device (device_name) → "Device"
  - Domain (_value) → "Domain"
  - Query Type (query_type) → "Query Type"
- **Sorting:** By time descending (most recent first)
- **Show Header:** true
- **Footer:** hidden

### Column Overrides

All column renames applied via field overrides for clean display.

## Critical Lessons Learned

### Issue 1: Real-Time Log vs Historical Analysis

**Current:** Shows last 100 queries within time range

**Behavior:**

- 5-minute window: May show <100 queries (low activity)
- 1-hour window: Always 100 queries (high activity)
- Oldest query shown depends on activity level

**Use case specific:**

- Real-time monitoring: Use 5-15 minute window
- Historical investigation: Use hours/days

### Issue 2: Query Type Information

**A Records:** Standard IPv4 lookups (most common)
**AAAA Records:** IPv6 lookups
**Both:** Indicates modern dual-stack device

**Minimal impact on streaming**, but useful for network topology understanding

### Issue 3: Domain Granularity

**Examples:**

- nflxvideo.net (Netflix CDN)
- googlevideo.com (YouTube CDN)
- cloudfront.net (Amazon CDN)

**Value:** Specific domains show CDN selection and failover

## What's Working Well

- ✅ Real-time activity log for streaming
- ✅ Shows device-to-domain correlation
- ✅ Timestamp precision for event correlation
- ✅ 100 query limit provides good historical window
- ✅ Filtered to streaming domains (noise reduction)
- ✅ Clean table format easy to scan

## Current Gaps

- ❌ No query response time per query (only Panel 6 aggregates)
- ❌ No indication of query success/failure
- ❌ No correlation with bandwidth events
- ❌ Limited to 100 queries (may miss events in high-activity networks)
- ❌ No search/filter capability in table

## Potential Improvements

### 1. Add Response Time Column

**What:** Show DNS resolution time for each query
**How:** Include query_time_ms field in keep() columns

**Impact:** See which specific queries were slow

### 2. Add Bandwidth Context

**What:** Show if query correlated with streaming session start
**How:** Join with bandwidth data from Panel 2

**Impact:** Distinguish streaming queries from background app activity

### 3. Increase to 500 Queries

**What:** Show more history, especially for busy networks
**How:** Change limit(n: 500)

**Tradeoff:** More data, slower panel rendering

### 4. Add Query Result Column

**What:** Show resolved IP address
**How:** Capture DNS response data

**Impact:** See CDN node selection, detect failovers

## Related Panels

- **Panel 8:** Streaming Service Detection - Aggregated view of this data
- **Panel 2:** Streaming Bandwidth Timeline - Correlate query timing with bandwidth
- **Panel 1:** Active Streaming Sessions - Verify devices with queries are streaming
- **Panel 6:** DNS Resolution Time - Aggregated timing metrics
- **Panel 9:** CDN Connection Health - CDN identification from domain patterns

## Investigation Workflow

### Workflow 1: Buffering Event Timeline Correlation

**When investigating buffering at specific time:**

1. **Note buffering time** from Panel 10 or user report
2. **Filter this table to that time** (adjust dashboard time range)
3. **Look for queries immediately before buffering:**
   - New CDN domain queries? CDN failover attempt
   - Repeated queries? DNS resolution problems
   - No queries? Using cached DNS, not DNS-related
4. **Check domain pattern:**
   - Multiple different CDN domains? Connection instability
   - Same domain repeatedly? Retries due to failure
5. **Cross-reference Panel 6:** Was DNS slow at that time?

### Workflow 2: Service Start Investigation

**When stream takes long to start:**

1. **Find first DNS query** for that service/device in this table
2. **Note timestamp** of query
3. **Check Panel 6:** DNS resolution time at that moment
4. **Check Panel 2:** When did bandwidth start flowing?
5. **Calculate delay:**
   - DNS query time → Bandwidth start time
   - Total = DNS + connection + initial buffer
6. **Identify bottleneck:**
   - Long DNS time (Panel 6)? DNS is bottleneck
   - Quick DNS, long delay to bandwidth? CDN connection slow
   - Quick everything, still slow start? App/device issue

### Workflow 3: CDN Failover Detection

**When detecting CDN node changes:**

1. **Look for domain pattern changes:**
   - Initially: nflx-video-123.netflix.com
   - Later: nflx-video-456.netflix.com
   - Indicates: CDN node change
2. **Correlate with QoS events:**
   - Check Panel 3: Was old node high latency?
   - Check Panel 4: Was old node experiencing loss?
3. **Verify performance improvement:**
   - Check Panel 2: Did bandwidth improve after domain change?
   - Indicates: Successful failover to better CDN node

### Workflow 4: Unexpected Service Usage Detection

**When monitoring for unexpected activity:**

1. **Scan table for unusual patterns:**
   - Devices that shouldn't stream (IoT, printers, etc.)
   - Services not subscribed to (HBO when no subscription)
   - Unusual timing (3 AM activity)
2. **Investigate suspicious entries:**
   - Check device type - should it stream?
   - Check time - does it match household schedule?
   - Check service - is subscription active?
3. **Cross-reference Panel 8:**
   - High query count? Active use, not just single query
4. **Determine if legitimate:**
   - Legitimate: Document as baseline
   - Suspicious: Investigate for compromise or unauthorized access

## Common Scenarios & Responses

### Scenario 1: Rapid Query Sequence (Multiple Queries in Seconds)

**Pattern:** Same device showing 5-10 queries to Netflix domains in 10-20 seconds

**Analysis:** App startup or content browsing

**Interpretation:**

- Normal app behavior
- App resolving multiple CDN nodes
- User browsing content catalog

**Action:** None needed - normal streaming app behavior

### Scenario 2: Query Timing Matches Buffering Event

**Pattern:** DNS query to new Netflix domain at exact time Panel 10 shows bandwidth drop

**Interpretation:**

- CDN failover occurring
- Old CDN node failing, app switching to new node
- Brief interruption during switchover

**Expected Behavior:**

- Bandwidth drop briefly
- DNS query to new domain
- Bandwidth recovers (to same or better level)

**Action:**

- If recovers: CDN failover successful, no action
- If doesn't recover: CDN issue affecting multiple nodes

### Scenario 3: Query Without Bandwidth

**Pattern:** Device shows DNS query to Netflix, but Panel 2 shows no bandwidth increase

**Analysis:** DNS query doesn't mean streaming started

**Possible Causes:**

1. App opening, checking for content
2. Background metadata refresh
3. DNS pre-resolution (before user selects content)
4. App auto-refresh

**Action:** Don't assume streaming just from DNS query - verify with Panel 2 bandwidth

### Scenario 4: Repeated Queries to Same Domain

**Pattern:** Same device querying netflix.com every 30-60 seconds

**Interpretation:** Either:

- DNS caching disabled or very short TTL
- App repeatedly resolving (unusual, possible bug)
- Connection failing, retrying

**Investigation:**

1. Check if normal for that device
2. Check Panel 2: Is streaming stable despite repeated queries?
3. If stable: Quirk of app/device, acceptable
4. If unstable: Connection issues causing retries

**Action:**

- If stable streaming: No action
- If connection issues: Investigate network stability

### Scenario 5: Unusual Timing (Off-Hours Queries)

**Pattern:** DNS queries at 3 AM from devices that shouldn't be active

**Analysis:** Possibly suspicious

**Investigation:**

1. **Check device type:** Smart TV, mobile, computer?
2. **Check query count:** Single query or many?
3. **Check Panel 2 bandwidth:** Streaming activity or just query?
4. **Determine cause:**
   - Smart TV auto-play: Normal (Netflix episode queue)
   - Mobile device: User awake or app refresh
   - Computer: Background process or potential compromise

**Actions:**

- Smart TV: Check auto-play settings
- Mobile: Likely normal, user awake
- Computer: Investigate for scheduled tasks or malware
- IoT: Very suspicious, investigate immediately

## Files Referenced

- **Dashboard JSON:** `/Users/kirkl/src/network-monitoring/grafana-dashboards/streaming-monitor.json` (Panel ID 8)
- **Router DNS Daemon:** `/root/bin/dns-monitor-daemon.sh` (real-time DNS logging)
- **Router DNS Logs:** `/var/log/dnsmasq.log` (source of DNS events)

## Streaming Quality Metrics

### DNS Query Frequency by Activity Type

| Activity | Queries/Minute | Pattern |
|----------|----------------|---------|
| Streaming video | 0.5-2 | Sparse, CDN queries |
| Browsing catalog | 5-15 | Burst, many metadata domains |
| App startup | 10-30 | Initial burst, then sparse |
| Background refresh | 1-5 | Periodic, low frequency |
| Idle/closed app | 0 | No queries |

### Using Query Timing for Event Correlation

**Stream start detection:**

1. First DNS query to service = Stream initiation
2. Time to first bandwidth (Panel 2) = Connection setup time
3. Should be <5 seconds typically

**Stream quality change detection:**

1. New CDN domain query during stream = CDN switch
2. May indicate quality adaptation or node failover
3. Check Panel 2 for bandwidth change

**Stream end detection:**

1. Last DNS query to service = Approximate end
2. Actually: Bandwidth stop (Panel 2) = definitive end
3. No queries for >5 minutes = App likely closed

## Buffering Detection Patterns

### Pattern 1: DNS Query Burst During Active Stream

**Signature:** Device streaming (Panel 2 shows bandwidth), suddenly 5-10 DNS queries

**Interpretation:**

- App attempting CDN failover
- Current CDN node failing
- App searching for better node

**Buffering Likelihood:** High - failover usually triggered by quality issues

**Investigation:**

1. Check Panel 3: Is CDN latency elevated?
2. Check Panel 4: Is packet loss present?
3. Check Panel 2: Does bandwidth recover after queries?

### Pattern 2: No Recent Queries But Streaming Active

**Signature:** Panel 2 shows device streaming, but no DNS queries in last 100

**Interpretation:**

- DNS cached from earlier
- Using long-lived connection
- Normal for sustained streaming sessions

**Not a problem:** DNS only needed at start and for failover

### Pattern 3: Query Timing Matches Bandwidth Gaps

**Signature:** Bandwidth goes to zero (Panel 2), DNS query appears, bandwidth resumes

**Interpretation:**

- Connection interruption
- App reconnecting
- DNS resolution needed for new connection

**Buffering:** Definitely occurred during gap

## CDN Performance Analysis

### CDN Node Identification from Domains

**Netflix CDN patterns:**

- nflxvideo.net → Netflix OCA (Open Connect Appliance)
- akamai.net → Akamai CDN
- llnwd.net → Limelight CDN (older content)

**YouTube CDN patterns:**

- googlevideo.com → Google Global Cache
- Multiple numbered subdomains → Different cache servers

**Amazon CDN patterns:**

- cloudfront.net → CloudFront
- amazonaws.com → AWS infrastructure

**Using this panel:**

- Identify specific CDN nodes from domain names
- Track CDN node changes over time
- Detect geographic routing changes

### Query Patterns Indicating CDN Issues

**Pattern:** Device queries multiple different CDN subdomains rapidly

**Example:**

```
12:00:01 - Device: LG TV - nflx-video-123.net
12:00:15 - Device: LG TV - nflx-video-456.net
12:00:30 - Device: LG TV - nflx-video-789.net
```

**Interpretation:**

- Device trying multiple CDN nodes
- First nodes failing or slow
- App searching for working node

**Action:**

- Check Panel 3 (Latency) and Panel 4 (Loss) for CDN issues
- This pattern confirms CDN problems
