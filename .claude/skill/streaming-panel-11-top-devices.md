# Streaming Panel 11: Top Streaming Devices (Total Bandwidth)

## Panel Overview

- **Panel ID:** 6
- **Title:** Top Streaming Devices (Total Bandwidth)
- **Type:** Bar Gauge (Horizontal gradient bars)
- **Grid Position:** x=0, y=42, width=12, height=8 (bottom left section)
- **Purpose:** Ranks devices by total bandwidth consumed during the selected time range, showing top 10 consumers to identify heavy streaming users and potential network hogs

## Data Source

### Current: InfluxDB Flux Query

```flux
from(bucket: "network")
  |> range(start: v.timeRangeStart, stop: v.timeRangeStop)
  |> filter(fn: (r) => r._measurement == "bandwidth" and r.direction == "rx")
  |> group(columns: ["device_name"])
  |> sum()
  |> filter(fn: (r) => r._value > 10000000)
  |> map(fn: (r) => ({r with _value: float(v: r._value) / 1024.0 / 1024.0 / 1024.0}))
  |> sort(columns: ["_value"], desc: true)
  |> limit(n: 10)
```

**Query Breakdown:**

1. **Sum total bandwidth** per device over entire time range
2. **Filter threshold:** Only show devices with >10 MB total (excludes light users)
3. **Convert to GB:** Bytes → GB for readable display (÷ 1024³)
4. **Sort descending:** Highest bandwidth first
5. **Limit to top 10:** Focus on heavy users

**Key Difference from Other Panels:**

- Panel 1: Current bandwidth (real-time snapshot)
- Panel 2: Timeline (temporal pattern)
- **Panel 11:** Total consumption (aggregate over time range)

### Metrics Used

- **InfluxDB:** `bandwidth` measurement with `direction="rx"` tag
  - Tags: `device_name`, `ip`, `mac`, `protocol`, `direction`
  - Field: `bytes` (integer - delta values)
  - Type: Event-based deltas from router

### Data Collection Flow

1. **Router (GL-MT2500A):** nlbwmon tracks per-device bandwidth
2. **Export Script:** `/root/bin/send-bandwidth-to-influx.sh` sends deltas every minute
3. **Telegraf:** Receives UDP on port 8094
4. **InfluxDB:** Stores in "network" bucket
5. **Grafana:** Aggregates total and displays top 10

## Current Configuration

### Thresholds & Colors

Threshold values in **decimal gigabytes (GB)**:

- **Green:** 0 - 0.99 GB (Light usage)
- **Yellow:** 1.0 - 4.99 GB (Moderate usage)
- **Red:** 5.0+ GB (Heavy usage)

**Context for thresholds (1-hour window):**

- 1 GB in 1 hour = ~2.2 Mbps average (SD streaming)
- 2 GB in 1 hour = ~4.4 Mbps average (HD streaming)
- 5 GB in 1 hour = ~11.1 Mbps average (Full HD/4K streaming)
- 10 GB in 1 hour = ~22.2 Mbps average (4K streaming)

### Display Settings

- **Unit:** decgbytes (decimal gigabytes, base 1000)
- **Visualization Type:** Bar Gauge
- **Display Mode:** Gradient (smooth color transition)
- **Orientation:** Horizontal (left-to-right bars)
- **Show Unfilled:** true (shows empty portion of bar)
- **Display Name:** `${__field.labels.device_name}` - Device-friendly names

### Time Range

- Uses: dashboard time range variables `v.timeRangeStart` and `v.timeRangeStop`
- Default: Last 1 hour (now-1h to now)
- **Interpretation varies by time range:**
  - 1 hour: Recent heavy streamers
  - 24 hours: Daily bandwidth leaders
  - 7 days: Weekly consumption rankings
  - 30 days: Monthly data caps monitoring

## Critical Lessons Learned - Total Bandwidth Ranking

### Issue 1: 10 MB Threshold Too Low Initially

**Problem:** Panel filled with devices that only briefly browsed, not actual streamers

**Original threshold:** >100 MB
**Issue:** Too high for 1-hour default window (excluded real streamers)

**Current solution:** 10 MB minimum

- 1-hour window: Captures devices with >22 kbps average (very low bar)
- Effectively includes all streaming devices
- Still filters out completely idle devices

**Adjustment by time range:**

- 1 hour: 10 MB works well
- 6 hours: Could raise to 50 MB
- 24 hours: Could raise to 200 MB
- Would require dynamic threshold based on time range

### Issue 2: Unit Confusion (Binary vs Decimal)

**Problem:** Users expecting binary gigabytes (GiB) but seeing decimal (GB)

**Current:** `decgbytes` (1000-based)

- 1 GB = 1,000,000,000 bytes
- Matches ISP billing and consumer understanding

**Alternative:** `binGiBytes` (1024-based)

- 1 GiB = 1,073,741,824 bytes
- Matches computer science / OS reporting

**Decision:** Keep decimal for consistency with ISP data caps and general consumer expectations

### Issue 3: Bar Gauge vs Table Visualization

**Bar Gauge Advantage:** Visual hierarchy immediately clear

**Table Advantage:** Can show additional columns (IP, MAC, device type)

**Decision:** Bar gauge for quick visual scanning

- Color gradient provides instant assessment
- Horizontal bars easy to compare lengths
- Device names clearly labeled

**Future:** Could add table view as alternative panel

### Issue 4: Time Range Context Missing

**Problem:** 5 GB looks scary but might be normal for 24-hour window

**Current limitation:** No indication of time range on panel itself

**Workaround:** Dashboard time range selector provides context

**Improvement needed:** Show average rate (Mbps) alongside total (GB)

## What's Working Well

- ✅ Clear visual ranking of bandwidth consumption
- ✅ Color gradient provides instant usage assessment
- ✅ Top 10 limit keeps panel focused on key consumers
- ✅ 10 MB threshold effectively filters noise
- ✅ Decimal GB unit matches consumer expectations
- ✅ Works well for data cap monitoring
- ✅ Device names human-readable via registry
- ✅ Scales across different time ranges (1h to 30d)

## Current Gaps

- ❌ No average rate displayed (only total consumption)
- ❌ No percentage of total network bandwidth
- ❌ No comparison to historical baseline for each device
- ❌ No device type indicators (can't see which are TVs vs tablets)
- ❌ Threshold is static (doesn't adapt to time range)
- ❌ No drill-down to see device bandwidth timeline
- ❌ No indication of streaming vs downloading (could be large downloads)
- ❌ No upload bandwidth comparison (one-way view)

## Potential Improvements

### 1. Add Average Rate Column/Metric

**What:** Show both total (GB) and average rate (Mbps) for each device
**How:** Add calculated field:

```flux
|> map(fn: (r) => ({
    r with
    total_gb: float(v: r._value) / 1024.0 / 1024.0 / 1024.0,
    avg_mbps: float(v: r._value) * 8.0 / float(v: uint(v: v.timeRangeStop) - uint(v: v.timeRangeStart)) * 1000000000.0
}))
```

**Display:** "LG TV: 15 GB (33 Mbps avg)"
**Impact:** Provides rate context for total consumption

### 2. Add Network Share Percentage

**What:** Show what percentage of total network bandwidth each device consumed
**How:** Calculate total network bandwidth, then percentages:

```flux
total_bandwidth = <sum all devices>

<per-device query>
|> map(fn: (r) => ({
    r with
    percent: (r._value / total_bandwidth) * 100.0
}))
```

**Display:** "LG TV: 15 GB (45% of network)"
**Impact:** Understand relative impact on network

### 3. Add Baseline Comparison Indicator

**What:** Show if device usage is normal, above, or below typical
**How:** Query 7-day average, compare to current:

```flux
baseline = from(bucket: "network")
  |> range(start: -7d)
  |> <aggregate per device per day>
  |> mean()

current = <current time range query>

join(tables: {current: current, baseline: baseline}, on: ["device_name"])
|> map(fn: (r) => ({
    r with
    deviation: (r.current / r.baseline - 1.0) * 100.0
}))
```

**Display:** "LG TV: 15 GB (↑ 120% vs typical)" or "↓ 40% vs typical"
**Impact:** Anomaly detection - identify unusual behavior

### 4. Add Device Type Tags

**What:** Show [TV], [Phone], [Tablet], [Computer] tags on device names
**How:**

- Add device_type to router device registry
- Include in export script tags
- Display in legend: `{{device_name}} [{{device_type}}]`

**Display:** "LG TV [TV]: 15 GB"
**Impact:** Context for expected behavior - TV using 15 GB normal, phone using 15 GB suspicious

### 5. Add Adaptive Threshold by Time Range

**What:** Automatically adjust 10 MB threshold based on time window
**How:** Calculate proportional threshold:

```
threshold = 10 MB * (time_range_hours / 1 hour)
```

- 1 hour: 10 MB
- 6 hours: 60 MB
- 24 hours: 240 MB

**Impact:** Consistent filtering across time ranges

### 6. Add Streaming vs Download Indicator

**What:** Distinguish sustained streaming from large file downloads
**How:** Calculate bandwidth variance:

```flux
|> variance(column: "_value")
|> map(fn: (r) => ({
    r with
    pattern: if r.variance < threshold then "Streaming" else "Download"
}))
```

**Display:** "LG TV [Streaming]: 15 GB" vs "Laptop [Download]: 15 GB"
**Impact:** Understand usage type, not just volume

## Related Panels

- **Panel 1:** Active Streaming Sessions - See which devices are currently streaming (subset of top consumers)
- **Panel 2:** Streaming Bandwidth Timeline - See temporal patterns for these top devices
- **Panel 8:** Streaming Service Detection - Identify which services these devices are using
- **Panel 10:** Bandwidth Drops - Check if top consumers experienced buffering
- **Main Dashboard Panel 1:** Top Bandwidth Users (Download) - Compare streaming devices to total network
- **Main Dashboard Panel 3:** Bandwidth Over Time - See how these devices contribute to total network load

## Investigation Workflow

### Workflow 1: Data Cap Monitoring

**When monitoring monthly data caps:**

1. **Set time range to 30 days** (full billing cycle)
2. **Identify top consumers** - Note devices approaching data cap risk
3. **Calculate total consumption:**
   - Sum top 10 devices shown
   - Estimate total network (shown devices ~80% of total typically)
   - Compare to ISP data cap (e.g., 1.2 TB/month)
4. **Assess risk:**
   - Current usage × (30 / days_elapsed) = projected monthly usage
   - If projected > 80% of cap → Risk of overage charges
5. **Identify reduction targets:**
   - Devices with highest consumption
   - Check Panel 8 for services (4K vs HD vs SD)
   - Consider reducing streaming quality settings

**Example:**

- Day 15 of month, top 10 devices show 400 GB consumed
- Projected: 400 GB × (30/15) = 800 GB month estimate
- Cap: 1200 GB
- Status: On track (67% usage projected), acceptable

### Workflow 2: Identifying Unusual Device Behavior

**When a device appears unexpectedly in top 10:**

1. **Check device type** - Is this device typically high-bandwidth?
   - TV/Streaming device: Normal
   - Phone/Tablet: Unusual if top 3
   - IoT device: Very suspicious
   - Computer: Could be work/gaming, investigate
2. **Check Panel 2 (Timeline)** for this device:
   - Sustained streaming pattern? Normal
   - Large spike pattern? Likely download
   - Consistent 24/7? Suspicious (could be compromise)
3. **Check Panel 8** (Service Detection):
   - Streaming services? Legitimate
   - No streaming service matches? Investigate further
4. **Check Panel 13** (DNS Queries):
   - Recognize domains? Normal
   - Unusual domains? Research domains for legitimacy
5. **Decision:**
   - Legitimate heavy usage: Document as baseline
   - Suspicious: Investigate for compromise, data exfiltration

### Workflow 3: Fair Usage Enforcement

**When implementing household bandwidth policies:**

1. **Establish baselines** (run 7-day average):
   - Note typical top consumers and their ranges
   - Identify "usual suspects" vs "unusual high usage"
2. **Set per-device limits:**
   - Primary streaming devices: 50-100 GB/week
   - Personal devices: 10-30 GB/week
   - IoT devices: <5 GB/week
3. **Monitor enforcement:**
   - Daily check of this panel (24-hour window)
   - Devices exceeding limit → Conversation or QoS throttling
4. **Identify violators:**
   - Device appears higher than expected? Check Panel 2 for activity times
   - Activity during "homework hours" or overnight? Policy violation
5. **Take action:**
   - Communication: Discuss usage with household member
   - Technical: Implement QoS throttling during restricted hours
   - Nuclear: Guest network with rate limiting

### Workflow 4: Optimizing Streaming Quality Settings

**When bandwidth consumption is too high:**

1. **Identify 4K streamers:**
   - Devices with >10 GB/hour average (check Panel 1/2)
   - Check Panel 8 for services (Netflix, Disney+, etc.)
2. **Calculate savings:**
   - 4K: ~40 Mbps = ~18 GB/hour
   - 1080p: ~8 Mbps = ~3.6 GB/hour
   - Savings: ~80% bandwidth reduction
3. **Target devices:**
   - Smaller screens (<50"): Likely won't notice 4K vs 1080p
   - Distant viewing: Reduced benefit of 4K
   - High-usage devices: Maximum savings opportunity
4. **Implement changes:**
   - Netflix: Account settings → Playback settings → HD (not Auto/High)
   - Disney+: App settings → Video Quality → Standard
   - YouTube: App settings → Video Quality Preferences → 1080p max
5. **Monitor results:**
   - Check this panel after 24 hours
   - Expect 50-80% reduction for converted devices
   - Verify user satisfaction (quality acceptable?)

## Common Scenarios & Responses

### Scenario 1: Smart TV Dominates Top 10 (>50% of total)

**Pattern:** LG TV or similar showing 30-50 GB in 24-hour window, 2-3x more than any other device

**Analysis:**

- **For 1-hour window:** 30-50 GB = 67-111 Mbps average = Consistent 4K streaming
- **For 24-hour window:** Normal for household primary TV with heavy usage
- **Expected behavior:** Families commonly have 6-12 hours of TV streaming per day

**Investigation:**

1. Check Panel 2 timeline: Is it concentrated in evening (normal) or 24/7 (unusual)?
2. Check Panel 8: Multiple services or single service binge?
3. Check time alignment: Evenings/weekends (expected) vs school/work hours (investigate)

**Actions:**

- **If concentrated evening use:** Normal behavior, no action unless data cap concerns
- **If 24/7 continuous:** Check for auto-play settings or investigate for compromise
- **If data cap concern:** Reduce quality to 1080p (80% bandwidth reduction)

**Expected Patterns:**

- Evening spike (6 PM - 11 PM): 4-6 hours = 20-30 GB normal
- Weekend all-day: 8-12 hours = 40-60 GB normal
- Weekday daytime: Minimal = <5 GB expected

### Scenario 2: Mobile Device in Top 3

**Pattern:** iPhone or Android phone showing 10-20 GB in 24-hour window

**Analysis:**

- Unusual - phones typically <5 GB/day on home WiFi
- Possible causes: Video streaming, hotspot abuse, sync/backup, gaming

**Investigation:**

1. **Check Panel 2 timeline:**
   - Continuous 24/7? Phone left streaming or sync running
   - Specific hours? User behavior analysis
2. **Check Panel 1:** Currently streaming? What bandwidth?
3. **Check Panel 8:** Which services? Video (expected) vs other (investigate)
4. **Check device settings:**
   - Cloud backup running? (iCloud, Google Photos)
   - Hotspot enabled? (Other devices using phone as gateway)
   - Auto-download enabled? (App updates, media sync)

**Root Causes:**

- **Legitimate:** Heavy video streaming, cloud backup, app updates
- **Concerning:** Hotspot abuse (should be on separate network), cryptocurrency mining, data exfiltration

**Actions:**

- Video streaming: Normal if teenager/heavy user, consider quality settings
- Cloud backup: Schedule to off-peak hours (2-6 AM)
- Hotspot: Move to guest network or block hotspot feature
- Suspicious: Investigate running apps, check for malware

### Scenario 3: IoT Device Appears in Top 10

**Pattern:** Camera, thermostat, or smart home device showing >1 GB usage

**Analysis:**

- **Highly suspicious** - IoT devices should be <100 MB/day typically
- Security cameras exception: Could be 1-5 GB/day if uploading continuously

**Expected Bandwidth by IoT Device Type:**

- Smart bulbs/switches: <1 MB/day
- Voice assistants: <50 MB/day
- Thermostats: <10 MB/day
- Non-recording cameras: <100 MB/day
- Recording cameras: 1-5 GB/day (to cloud storage)
- Smart TVs (off): <50 MB/day (standby updates)

**Investigation - URGENT:**

1. **Identify device type** - Camera vs sensor vs appliance?
2. **Check Panel 2 timeline:**
   - Continuous upload? Potential compromise/botnet
   - Burst pattern? Could be legitimate cloud sync
3. **Check Panel 13 (DNS):**
   - Manufacturer domains only? Likely legitimate
   - Unknown/suspicious domains? Compromise confirmed
4. **Check Panel 8:**
   - Streaming services detected? Highly suspicious (IoT shouldn't stream)
5. **Check Main Dashboard Panel 2 (Upload):**
   - High upload? Data exfiltration or botnet activity

**Actions:**

- **Camera with expected upload:** Acceptable if 1-5 GB/day to known cloud (Ring, Nest, etc.)
- **Non-camera IoT:** Isolate immediately, investigate for compromise
- **Any IoT with streaming:** Compromise confirmed, factory reset and isolate
- **Prevention:** Move all IoT to isolated VLAN with restricted internet access

### Scenario 4: New Device Suddenly Appears in Top 5

**Pattern:** Previously unseen or low-usage device suddenly ranks high

**Analysis:**

- Could be legitimate (new device, new user behavior) or concerning (compromise, unauthorized user)

**Investigation:**

1. **Identify device:**
   - Check MAC address OUI (manufacturer lookup)
   - Check router DHCP leases for connection time
   - Check device registry for known vs unknown
2. **Correlate with household events:**
   - New device purchase? Expected
   - Guest visiting? Should be on guest network
   - No explanation? Investigate
3. **Check behavior patterns:**
   - Panel 2: Normal streaming pattern vs unusual
   - Panel 8: Recognizable services vs none
   - Panel 13: Legitimate domains vs suspicious
4. **Timeframe analysis:**
   - First seen when? Correlate with household events
   - Active hours? Match household schedule?

**Root Causes:**

- **Legitimate:** New device, behavior change, software update with increased bandwidth
- **Concerning:** Unauthorized device, compromised device, neighbor accessing WiFi

**Actions:**

- Legitimate new device: Add to registry, document baseline
- Guest device: Move to guest network (should have been there from start)
- Unknown device: Block immediately, investigate physical access
- Changed behavior: Document and monitor for consistency

### Scenario 5: Multiple Devices Show Equal High Usage

**Pattern:** 3-5 devices all showing similar consumption (e.g., 10-15 GB each in 24h)

**Analysis:**

- **Normal:** Multi-person household with equal streaming habits
- **Unusual:** If devices are not normally equal users

**Investigation:**

1. **Check device types:**
   - All TVs/tablets/phones? Normal multi-user household
   - Mix of unexpected types? Investigate individually
2. **Check Panel 2 timelines:**
   - Staggered usage? Normal (different people, different times)
   - Concurrent usage? Check total bandwidth vs capacity
3. **Check Panel 8 services:**
   - Different services? Different people's preferences (normal)
   - All same service? Could indicate account sharing abuse
4. **Time correlation:**
   - Spread across day? Normal
   - All simultaneous? Network saturation risk

**Actions:**

- Normal multi-user: No action, healthy usage distribution
- Network saturation: Implement QoS to prioritize critical traffic
- Account sharing concerns: Review service ToS, educate household
- Capacity planning: Consider bandwidth upgrade if all legitimate and saturating

### Scenario 6: Single Device Bandwidth Cycling Pattern

**Pattern:** Device appears and disappears from top 10, usage varies wildly day-to-day

**Analysis:**

- Intermittent user behavior or technical issue

**Investigation:**

1. **Check timeline regularity (Panel 2):**
   - Regular daily pattern? User schedule (works evenings, weekends off, etc.)
   - Random? Investigate for technical issues
2. **Compare multiple days:**
   - Weekday vs weekend difference? Expected behavior
   - Consistent variance? Technical issue or shared device
3. **Check for external factors:**
   - School schedule? Kids' devices
   - Work schedule? Remote workers' devices
   - Travel? Device owner away periodically

**Root Causes:**

- User schedule (shift work, travel, school breaks)
- Shared device (multiple people use same TV/tablet)
- Technical issues (connection drops, app crashes)
- Content availability (binge new season, then quiet)

**Actions:**

- Identified pattern: Document as normal for that device/user
- No clear pattern: Investigate device reliability
- Shared device: Consider separate profiles/accounts for tracking

## Files Referenced

- **Dashboard JSON:** `/Users/kirkl/src/network-monitoring/grafana-dashboards/streaming-monitor.json` (Panel ID 6)
- **Provisioned Dashboard:** `/Users/kirkl/src/network-monitoring/grafana-provisioning/dashboards/streaming-monitor.json` (Panel ID 6)
- **Router Export Script:** `/root/bin/send-bandwidth-to-influx.sh` (on GL-MT2500A)
- **Router Device Registry:** `/root/etc/device-registry.conf` (device name mappings)
- **Telegraf Config:** `/Users/kirkl/src/network-monitoring/telegraf.conf` (socket_listener, lines 6-10)

## Streaming Quality Metrics

### Total Bandwidth to Quality Mapping (1-Hour Window)

| Total (GB/hr) | Average Rate | Typical Quality | Example Use Case |
|---------------|--------------|-----------------|------------------|
| 0.5 - 1 GB | 1-2 Mbps | SD (480p) | Low-quality streams, audio |
| 1 - 2 GB | 2-4 Mbps | HD (720p) | Standard HD streaming |
| 2 - 4 GB | 4-9 Mbps | Full HD (1080p) | High-quality HD streaming |
| 4 - 10 GB | 9-22 Mbps | 4K starting | Entry 4K or premium 1080p |
| 10 - 20 GB | 22-44 Mbps | 4K standard | Typical 4K streaming |
| 20+ GB | 44+ Mbps | 4K premium/8K | High-bitrate 4K or 8K |

### Extended Time Range Interpretation

**24-Hour Window:**

- <5 GB: Light user (occasional streaming)
- 5-20 GB: Moderate user (2-4 hours streaming)
- 20-50 GB: Heavy user (4-10 hours streaming)
- 50-100 GB: Very heavy user (10-20 hours, likely 4K)
- >100 GB: Extreme user (20+ hours or continuous 4K)

**7-Day Window:**

- <20 GB: Minimal streaming activity
- 20-100 GB: Light to moderate streaming (1-2 hrs/day)
- 100-300 GB: Heavy streaming (3-6 hrs/day average)
- 300-500 GB: Very heavy streaming (6-10 hrs/day)
- >500 GB: Extreme/primary entertainment source (>10 hrs/day)

**30-Day Window (Data Cap Planning):**

- <100 GB: Minimal streaming, well under any cap
- 100-300 GB: Light streaming, safe from caps
- 300-600 GB: Moderate streaming, approaching 1 TB caps
- 600-1000 GB: Heavy streaming, may hit 1 TB cap
- >1000 GB: Very heavy, will exceed typical 1.2 TB caps

### Service-Specific Consumption Estimates

**Netflix:**

- SD: 0.7 GB/hour
- HD: 3 GB/hour
- 4K: 7 GB/hour (with efficient compression)
- Typical pattern: Mix of qualities, average 4-5 GB/hour

**YouTube:**

- 480p: 0.5 GB/hour
- 720p: 1.5 GB/hour
- 1080p: 2.5 GB/hour
- 4K: 10 GB/hour
- Typical pattern: Variable, depends on content and user preferences

**Disney+:**

- HD: 2 GB/hour
- 4K: 8 GB/hour
- Typical pattern: Consistent, family-friendly content

**Prime Video:**

- SD: 0.6 GB/hour
- HD: 2 GB/hour
- 4K: 6 GB/hour (superior compression)
- Typical pattern: Lower than competitors due to better encoding

## Buffering Detection Patterns

**This panel shows total consumption, not real-time bandwidth patterns.**

For buffering detection, cross-reference with:

- **Panel 10:** Bandwidth Drops (Potential Stalls) - Direct buffering indicators
- **Panel 2:** Streaming Bandwidth Timeline - Pattern analysis
- **Panel 1:** Active Streaming Sessions - Current streaming quality

### Using This Panel for Buffering Context

**Scenario:** Device shows high total consumption but user reports buffering

**Analysis Workflow:**

1. **Verify device is top consumer** in this panel (confirms active streaming)
2. **Check Panel 2** for device timeline:
   - Smooth high bandwidth? Buffering is not bandwidth-limited
   - Erratic/dropping bandwidth? Bandwidth-related buffering
3. **Check Panel 10** for specific buffering events
4. **Check Panels 3-5** for QoS issues (latency, loss, jitter)

**Interpretation:**

- High total + smooth timeline + buffering reports = QoS issue (not bandwidth)
- High total + erratic timeline + buffering reports = Bandwidth or network issue
- Low total + buffering reports = Below quality threshold, increase bandwidth

### Total Bandwidth as Buffering Risk Indicator

While not a direct buffering metric, total bandwidth provides context:

**High total (>10 GB/hour) with buffering:**

- Sufficient bandwidth available
- Issue is latency, packet loss, jitter, or CDN
- Follow QoS troubleshooting workflow

**Low total (<2 GB/hour) with buffering:**

- Insufficient bandwidth for desired quality
- Device may be attempting 4K but only achieving SD
- Increase available bandwidth or reduce quality setting

**Medium total (2-10 GB/hour) with buffering:**

- Borderline bandwidth for HD/4K
- Likely experiencing adaptive bitrate adjustments
- May need slightly more bandwidth or accept current quality

## CDN Performance Analysis

**This panel aggregates bandwidth without CDN specificity.**

For CDN-specific analysis, cross-reference with:

- **Panel 3:** CDN Latency (ICMP Ping) - Per-CDN performance
- **Panel 9:** CDN Connection Health - Device-to-CDN mapping
- **Panel 8:** Streaming Service Detection - Service-to-CDN correlation

### Using This Panel for CDN Context

**Scenario:** Investigating CDN performance issues

**Workflow:**

1. **Identify affected devices** in this panel (top consumers)
2. **Map to services** (Panel 8): Which services do they use?
3. **Map services to CDNs:**
   - Netflix → Akamai/Netflix OCA
   - YouTube → Google Global Cache
   - Prime Video → CloudFront
   - Disney+ → Akamai/Bamtech
4. **Check CDN latency** (Panel 3) for those CDNs
5. **Correlate high consumption with poor CDN performance**

**Expected Correlation:**

- High total + specific CDN latency issues = CDN affecting quality
- High total + all CDNs good latency = Not a CDN issue
- Low total + poor CDN latency = CDN preventing higher consumption

### Total Bandwidth as CDN Load Indicator

**Scenario:** All top devices streaming same service showing reduced consumption

**Example:** All top 3 devices are Netflix users, all showing 50% less bandwidth than typical

**Investigation:**

1. Check Panel 3: Is Akamai/Netflix latency elevated?
2. Check Panel 2: Are devices showing declining patterns?
3. Check Panel 8: Confirm all are Netflix users
4. Conclusion: Netflix/Akamai CDN performance issue reducing available bandwidth

**This panel helps identify:**

- Widespread service-specific issues (all Netflix users affected)
- Individual device issues (one device low, others normal)
- Network-wide issues (all devices low regardless of service)
