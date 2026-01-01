# Streaming Panel 12: Connection States (Streaming Devices)

## Panel Overview

- **Panel ID:** 7
- **Title:** Connection States (Streaming Devices)
- **Type:** Timeseries
- **Grid Position:** x=12, y=42, width=12, height=8
- **Purpose:** Monitors active TCP/UDP connection counts for devices, helping distinguish streaming (few connections) from downloading (many connections) and detecting connection leaks or unusual network patterns

## Data Source

### Current: InfluxDB Flux Query

```flux
from(bucket: "network")
  |> range(start: v.timeRangeStart, stop: v.timeRangeStop)
  |> filter(fn: (r) => r._measurement == "connection_state")
  |> filter(fn: (r) => r.state == "ESTABLISHED" or r.state == "ACTIVE")
  |> group(columns: ["device_name"])
  |> aggregateWindow(every: 30s, fn: sum, createEmpty: false)
  |> filter(fn: (r) => r._value > 5)
```

**Query Breakdown:**

1. **Measurement:** `connection_state` from router
2. **Filter states:** ESTABLISHED (TCP) or ACTIVE (UDP/other)
3. **Group by device:** Show connections per device
4. **Aggregate:** 30-second windows
5. **Filter:** Show only devices with >5 connections (reduces noise)

### Metrics Used

- **InfluxDB:** `connection_state` measurement from router
  - Tags: `device_name`, `state`, `protocol`
  - Field: Connection count (integer)
  - Type: Periodic snapshot from router netstat/conntrack

### Data Collection Flow

1. **Router:** netstat or conntrack tracking active connections
2. **Export Script:** Captures connection states periodically
3. **UDP to Telegraf:** Port 8094
4. **InfluxDB:** Stores in "network" bucket
5. **Grafana:** Displays timelines per device

## Current Configuration

### Thresholds & Colors

**No thresholds configured** - uses default line colors

**Connection Count Interpretation:**

- 1-5: Minimal, likely single application
- 5-20: Light usage, typical streaming
- 20-50: Moderate usage, browsing + streaming
- 50-100: Heavy usage, many apps/tabs
- 100+: Very heavy usage or potential issue

### Display Settings

- **Unit:** short (count)
- **Visualization:** Timeseries
- **Display:** Line graph, smooth interpolation
- **Fill Opacity:** 10%
- **Legend:** List format, bottom placement

## Critical Lessons Learned

### Issue 1: Streaming vs Downloading Signatures

**Streaming signature:**

- Low connection count (1-10)
- High bandwidth (Panel 2)
- Sustained duration

**Downloading signature:**

- High connection count (20-100+)
- Variable bandwidth
- Often short duration

**Use:** This panel helps classify device activity type

### Issue 2: Connection Count Noise

**Problem:** Many devices have 1-3 background connections always

**Solution:** Filter >5 connections to show only meaningful activity

**Tradeoff:** May miss single-connection streaming (rare)

### Issue 3: Connection Leak Detection

**Pattern:** Connection count steadily rising over hours/days

**Indicates:** Application not closing connections (memory leak, bug)

**Impact:** Eventually affects performance, may crash app/device

## What's Working Well

- ✅ Distinguishes streaming from other activities
- ✅ Detects connection leaks
- ✅ Shows device activity level
- ✅ 30-second aggregation appropriate
- ✅ Filters noise (>5 connections only)

## Current Gaps

- ❌ No connection state breakdown (ESTABLISHED vs TIME_WAIT vs etc.)
- ❌ No protocol breakdown (TCP vs UDP)
- ❌ No destination information (which servers)
- ❌ No connection rate (new connections per second)
- ❌ No correlation with bandwidth per connection

## Potential Improvements

### 1. Add Connection Efficiency Metric

**What:** Show bandwidth per connection ratio
**How:** Join with Panel 2 bandwidth data

**Formula:** Mbps / connection_count = efficiency

**Interpretation:**

- High (>1 Mbps/connection): Streaming (efficient)
- Low (<0.1 Mbps/connection): Browsing/downloading (many small)

### 2. Add Connection State Breakdown

**What:** Show ESTABLISHED, TIME_WAIT, CLOSE_WAIT separately
**How:** Separate queries for each state

**Impact:** Diagnose connection handling issues (TIME_WAIT accumulation)

### 3. Add Protocol Breakdown

**What:** Show TCP vs UDP connections
**How:** Group by protocol tag

**Impact:** Understand traffic composition (streaming mostly TCP, gaming UDP, DNS UDP)

### 4. Add Threshold Alerts

**What:** Alert on >100 connections (potential issue)
**How:** Add threshold at 100 with red color

## Related Panels

- **Panel 1:** Active Streaming Sessions - Streaming devices should show low connection counts here
- **Panel 2:** Streaming Bandwidth Timeline - Low connections + high bandwidth = streaming
- **Panel 11:** Top Streaming Devices - Heavy bandwidth with low connections confirms streaming

## Investigation Workflow

### Workflow 1: Streaming vs Downloading Classification

**When classifying device activity:**

1. **Check connection count (this panel):**
   - <10 connections: Likely streaming
   - 10-30: Mixed usage
   - >30: Likely downloading/browsing
2. **Cross-reference Panel 2 (bandwidth):**
   - Low connections + high bandwidth = Streaming confirmed
   - High connections + high bandwidth = Downloading
   - High connections + low bandwidth = Browsing
3. **Verify with Panel 8 (Service Detection):**
   - Streaming services detected? Confirms streaming
   - No services? Confirms downloading/other

### Workflow 2: Connection Leak Investigation

**When connection count steadily rises:**

1. **Identify affected device**
2. **Check if connections eventually close:**
   - Count drops after peak? Normal behavior
   - Count continues rising? Leak confirmed
3. **Check Panel 2:** Is bandwidth affected?
4. **Identify application:**
   - Check device type
   - Common leaks: Streaming apps, browsers, smart TV apps

**Actions:**

- Restart app on device
- Update app if available
- Restart device if leak persists
- Report to app developer

### Workflow 3: Unusual Connection Count

**When device shows unexpected high connections:**

1. **Check device type:**
   - Computer: May be normal (many tabs/apps)
   - Phone/tablet: Moderate (several apps)
   - TV/streaming device: Unusual if >20
   - IoT: Very suspicious if >5
2. **Check Panel 2:** Is bandwidth also high?
3. **Check Panel 13:** What domains being accessed?
4. **Determine cause:**
   - Legitimate multi-tasking
   - Background processes
   - Potential compromise (botnet, malware)

## Common Scenarios & Responses

### Scenario 1: Low Connections + High Bandwidth

**Pattern:** Device shows 3-8 connections, Panel 2 shows 15+ Mbps

**Analysis:** Classic streaming signature

**Expected behavior:**

- 1-2 connections to CDN for video stream
- 1-2 connections for metadata/thumbnails
- 1-3 connections for DRM/authentication

**Action:** None - this is normal streaming

### Scenario 2: High Connections + Low Bandwidth

**Pattern:** Device shows 50+ connections, Panel 2 shows <5 Mbps

**Analysis:** Web browsing or app with many small connections

**Expected causes:**

- Browser with many tabs
- Social media app (many image/video thumbnails)
- News app (many small content loads)

**Not streaming:** Streaming would have high bandwidth

**Action:** None if typical for device type

### Scenario 3: Connection Count Spike During Buffering

**Pattern:** Panel 10 shows buffering, this panel shows connection count spike

**Interpretation:**

- App opening many connections trying to recover
- Attempting multiple CDN nodes
- Connection thrashing due to failures

**Investigation:**

1. Check Panel 13: Multiple CDN domain queries?
2. Check Panel 3/4: CDN performance poor?
3. Confirms: Network issues causing connection retries

**Action:** Fix underlying network issue (not connection count itself)

### Scenario 4: Streaming Device with 100+ Connections

**Pattern:** Known TV/streaming device showing >100 connections

**Analysis:** Unusual and potentially problematic

**Investigation:**

1. Check if transient spike or sustained
2. Check Panel 13: What domains?
3. Check device type: Smart TV with many apps?
4. Possible causes:
   - Many apps running background updates
   - Connection leak (app bug)
   - Potential compromise (botnet)

**Actions:**

- Restart device
- Check for app updates
- Monitor for recurrence
- If persists: Factory reset or isolation

### Scenario 5: Connection Count Follows Bandwidth Pattern

**Pattern:** This panel's timeline matches Panel 2's bandwidth timeline shape

**Interpretation:**

- Each bandwidth increase = new connections opened
- Normal for some protocols/apps
- YouTube often shows this (multiple parallel streams)

**Expected for:**

- YouTube (parallel chunk loading)
- HTTP/2 multiplexing
- Multi-CDN services

**Action:** Normal behavior, no concern

## Files Referenced

- **Dashboard JSON:** `/Users/kirkl/src/network-monitoring/grafana-dashboards/streaming-monitor.json` (Panel ID 7)
- **Router Connection Tracking:** netstat or conntrack on GL-MT2500A router

## Streaming Quality Metrics

### Connection Count Patterns by Activity

| Activity Type | Typical Connections | Bandwidth Pattern |
|---------------|-------------------|-------------------|
| Video streaming | 2-10 | High, sustained |
| Audio streaming | 1-5 | Low, sustained |
| Video call | 5-15 | Moderate, bidirectional |
| Web browsing | 10-50 | Low, sporadic |
| File download | 1-20 | High, temporary |
| Gaming | 1-10 | Low, sustained, low latency |
| Software update | 5-30 | High, temporary |
| Torrent/P2P | 50-200+ | High, many sources |

### Streaming Service Connection Patterns

**Netflix:**

- Connections: 2-6
- Pattern: 1-2 for video, 1-2 for metadata, 1-2 for DRM
- Stable count during streaming

**YouTube:**

- Connections: 5-15
- Pattern: Multiple parallel chunk downloads
- Variable, may spike during buffer ahead

**Prime Video:**

- Connections: 3-8
- Pattern: Similar to Netflix
- Consistent during playback

**Twitch (Live):**

- Connections: 3-10
- Pattern: Main stream + chat + metadata
- Slightly higher than VOD services

### Connection Count as Streaming Quality Indicator

**Abnormal connection patterns during streaming:**

**Too few (<2):**

- May indicate connection issues
- Should have at least video + metadata
- Check if stream starting or ending

**Too many (>20):**

- App may be struggling
- Multiple retries/failovers
- Check Panel 10 for buffering
- Check Panel 3/4 for QoS issues

**Rapidly changing:**

- Connection churn (opening/closing frequently)
- Indicates instability
- Check Panel 5 (jitter) for correlation

## Buffering Detection Patterns

### Pattern 1: Connection Count Drop During Buffering

**Signature:** Panel 10 shows bandwidth drop, this panel shows connection count drop

**Interpretation:**

- Connections timing out during buffering
- App closing failed connections
- May be attempting to reconnect

**Buffering Severity:** Moderate to High

**Expected sequence:**

1. Buffering starts (bandwidth drops)
2. Connections time out (count drops)
3. App reconnects (count recovers)
4. Bandwidth resumes

### Pattern 2: Connection Count Spike Without Bandwidth

**Signature:** Connection count spikes to 20-30, but Panel 2 bandwidth doesn't increase

**Interpretation:**

- App attempting many connections
- Connections failing or not transferring data
- Network connectivity issue

**Investigation:**

1. Check Panel 3/4: Network quality issues?
2. Check Panel 13: Many DNS retries?
3. Connection thrashing indicates problem

**Action:** Fix underlying network issue

### Pattern 3: Sustained High Connections During Streaming

**Signature:** Device streaming (Panel 2 high bandwidth) but 30+ connections

**Analysis:** Either:

1. Multiple services simultaneously
2. Service using many parallel connections
3. Connection leak (not closing old connections)

**Investigation:**

1. Check Panel 8: Multiple services?
2. Check if connections keep rising: Leak
3. Check typical for that device/service

**Action:**

- Multiple services: Normal
- Connection leak: Restart app
- Unusual pattern: Investigate app behavior

## CDN Performance Analysis

### Connection Count by CDN Architecture

**CDN connection patterns:**

**Single-connection CDNs (Netflix, Prime):**

- Expect 2-6 connections total
- Main stream usually single connection
- Additional for metadata/DRM

**Multi-connection CDNs (YouTube):**

- Expect 5-15 connections
- Parallel downloading for speed
- More complex but faster buffering

**Using connection count for CDN diagnosis:**

1. **This panel:** Shows total connections
2. **Panel 9:** Shows which CDN
3. **Compare:** Actual vs expected for that CDN
4. **Deviation:** May indicate CDN issues or failover attempts

**Example:**

- Device normally 4 connections on Netflix/Akamai
- Suddenly 20 connections
- Panel 3: Akamai latency high
- Conclusion: App opening many connections trying to overcome CDN issues

## Files Referenced

- **Dashboard JSON:** `/Users/kirkl/src/network-monitoring/grafana-dashboards/streaming-monitor.json` (Panel ID 7)
- **Router Connection Tracking:** netstat/conntrack on GL-MT2500A
