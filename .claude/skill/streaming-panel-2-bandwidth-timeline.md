# Streaming Panel 2: Streaming Bandwidth Timeline

## Panel Overview

- **Panel ID:** 2
- **Title:** Streaming Bandwidth Timeline
- **Type:** Timeseries (Line graph with multiple series)
- **Grid Position:** x=12, y=0, width=12, height=8 (top-right, half dashboard width)
- **Purpose:** Displays temporal bandwidth patterns for all active streaming devices over the selected time range, enabling pattern analysis and anomaly detection

## Data Source

### Current: InfluxDB Flux Query

```flux
streaming_candidates = from(bucket: "network")
  |> range(start: v.timeRangeStart, stop: v.timeRangeStop)
  |> filter(fn: (r) => r._measurement == "bandwidth" and r.direction == "rx")
  |> aggregateWindow(every: 10s, fn: sum, createEmpty: false)
  |> filter(fn: (r) => r._value > 1000000)
  |> group(columns: ["device_name"])
  |> count()
  |> filter(fn: (r) => r._value >= 3)
  |> findColumn(fn: (key) => true, column: "device_name")

from(bucket: "network")
  |> range(start: v.timeRangeStart, stop: v.timeRangeStop)
  |> filter(fn: (r) => r._measurement == "bandwidth" and r.direction == "rx")
  |> filter(fn: (r) => contains(value: r.device_name, set: streaming_candidates))
  |> aggregateWindow(every: 10s, fn: sum, createEmpty: false)
  |> group(columns: ["device_name"])
  |> map(fn: (r) => ({r with _value: float(v: r._value) * 8.0 / 10.0}))
```

**Query Breakdown:**

1. **Streaming Candidate Detection:** Same algorithm as Panel 1 - identifies devices with sustained >1 Mbps bandwidth
2. **Timeline Data:** Returns time-series data for all streaming candidates showing bandwidth over time
3. **Aggregation:** 10-second windows for smooth visualization without excessive data points
4. **Conversion:** Bytes/s to bits/s for standard bandwidth display

**Key Difference from Panel 1:**

- Panel 1 shows only current/last value (stat card)
- Panel 2 shows complete timeline (graph) for pattern analysis

### Metrics Used

- **InfluxDB:** `bandwidth` measurement with `direction="rx"` tag
  - Tags: `device_name`, `ip`, `mac`, `protocol`, `direction`
  - Field: `bytes` (integer - delta values)
  - Type: Event-based deltas from router

### Data Collection Flow

1. **Router (GL-MT2500A):** nlbwmon tracks bandwidth every minute
2. **Export Script:** `/root/bin/send-bandwidth-to-influx.sh` sends deltas via UDP
3. **Telegraf:** Receives on port 8094, stores to InfluxDB
4. **Grafana:** Aggregates into 10-second windows and visualizes

## Current Configuration

### Thresholds & Colors

**No thresholds on this panel** - uses default line colors with overrides for specific devices:

- **LGwebOSTV_(LG_Electronics):** Blue (fixed)
- **43TCLRokuTV:** Green (fixed)
- Other devices: Auto-assigned from Grafana palette

### Display Settings

- **Unit:** bps (bits per second)
- **Visualization Type:** Timeseries line graph
- **Draw Style:** Line (smooth interpolation)
- **Fill Opacity:** 20% (semi-transparent area under line)
- **Span Nulls:** true (connects gaps in data)
- **Display Name:** `${__field.labels.device_name}` - Shows device names
- **Legend:** Table format at bottom showing Mean and Max values per device

### Time Range

- Uses: dashboard time range variables `v.timeRangeStart` and `v.timeRangeStop`
- Default: Last 1 hour (now-1h to now)
- Auto-refresh: Every 5 seconds
- **Recommended ranges:**
  - 5-15 minutes: Real-time monitoring
  - 1 hour: Session analysis
  - 6-24 hours: Daily pattern analysis

## Critical Lessons Learned - Timeline Visualization

### Issue 1: Too Many Series Clutters Graph

**Problem:** >10 streaming devices makes graph unreadable (overlapping lines)

**Solutions:**

1. **Current:** Device-specific color overrides for primary devices (LG TV, Roku)
2. **Alternative:** Filter to top N devices by bandwidth
3. **Alternative:** Add device selection variable to dashboard

**Best Practice:** Use 1-hour time range to naturally limit concurrent streamers

### Issue 2: Gaps in Timeline from Buffering

**Problem:** Brief buffering causes line breaks, hard to see overall pattern

**Solution:** `spanNulls: true` connects gaps automatically

- Gaps <30s: Likely buffering, span them for continuity
- Gaps >30s: Actual streaming stop, leave visible

### Issue 3: Spiky vs Smooth Patterns

**Observation:** Different streaming services have different bandwidth patterns

**Patterns Identified:**

- **Netflix:** Smooth, gradually rising (efficient adaptive bitrate)
- **YouTube:** Spiky, aggressive preloading (loads ahead of playback)
- **Disney+:** Very smooth, consistent (conservative buffering)
- **Prime Video:** Moderate spikes (balanced approach)

**Use:** Pattern recognition helps identify which service without DNS correlation

### Issue 4: Aggregation Window Choice

**Testing Results:**

- 5s windows: Too noisy, high cardinality
- 10s windows: ✅ Good balance (current setting)
- 30s windows: Too smooth, misses buffering events
- 60s windows: Unusable for real-time monitoring

**Recommendation:** Keep 10s for real-time, use 30s for >6 hour time ranges

## What's Working Well

- ✅ Clear visualization of streaming patterns over time
- ✅ Easy identification of sustained vs intermittent streaming
- ✅ Mean/Max legend values provide summary statistics
- ✅ Smooth line interpolation makes patterns clear
- ✅ Color overrides distinguish primary streaming devices
- ✅ 10-second aggregation balances detail and performance
- ✅ Span nulls feature maintains continuity during brief interruptions
- ✅ Auto-refresh keeps timeline current for live monitoring

## Current Gaps

- ❌ No bandwidth threshold indicators (can't see quality tiers visually)
- ❌ No annotations for buffering events
- ❌ No pattern classification (can't automatically label streaming types)
- ❌ Limited to 10-20 devices before graph becomes cluttered
- ❌ No comparison to available bandwidth (can't see saturation risk)
- ❌ No correlation with QoS events (latency spikes, packet loss)
- ❌ Color overrides hardcoded for specific devices (not dynamic)
- ❌ No drill-down to specific device timeline

## Potential Improvements

### 1. Add Bandwidth Threshold Markers

**What:** Horizontal threshold lines showing quality tiers
**How:** Add graph threshold annotations:

```json
{
  "thresholds": [
    {"value": 1000000, "color": "red", "label": "SD (1 Mbps)"},
    {"value": 5000000, "color": "yellow", "label": "HD (5 Mbps)"},
    {"value": 25000000, "color": "green", "label": "4K (25 Mbps)"}
  ]
}
```

**Impact:** Instantly see which devices meet quality requirements

### 2. Add Total Bandwidth Series

**What:** Show sum of all streaming bandwidth as separate series
**How:** Add second query:

```flux
from(bucket: "network")
  |> range(start: v.timeRangeStart, stop: v.timeRangeStop)
  |> filter(fn: (r) => r._measurement == "bandwidth" and r.direction == "rx")
  |> filter(fn: (r) => contains(value: r.device_name, set: streaming_candidates))
  |> aggregateWindow(every: 10s, fn: sum)
  |> group()  // Remove device grouping to get total
  |> sum()
```

**Display:** Thick dashed line showing aggregate
**Impact:** See total streaming load on network

### 3. Add Buffering Event Annotations

**What:** Mark timeline with buffering event indicators
**How:** Correlate with Panel 10 (Bandwidth Drops):

```flux
buffering_events = from(bucket: "network")
  |> range(start: v.timeRangeStart, stop: v.timeRangeStop)
  |> filter(fn: (r) => r._measurement == "bandwidth")
  |> filter(fn: (r) => r._value < 500000)  // Below buffering threshold
  |> group(columns: ["device_name"])
```

**Display:** Red markers on timeline at buffering moments
**Impact:** Visual correlation of bandwidth drops with timeline patterns

### 4. Add Device Selection Variable

**What:** Dashboard variable to filter timeline to specific devices
**How:** Create multi-select variable:

```flux
from(bucket: "network")
  |> range(start: -1h)
  |> filter(fn: (r) => r._measurement == "bandwidth")
  |> distinct(column: "device_name")
```

**Query modification:**

```flux
|> filter(fn: (r) => contains(value: r.device_name, set: $devices))
```

**Impact:** User-controlled device selection, reduces clutter

### 5. Add Pattern Classification Labels

**What:** Automatically label streaming pattern type in legend
**How:** Analyze bandwidth variance and label:

- Low variance (<20%) = "Smooth - Likely Netflix/Disney+"
- High variance (>50%) = "Spiky - Likely YouTube"
- Intermittent = "Short-form - TikTok/Shorts"

**Display:** Legend shows "LG TV [Smooth Netflix Pattern]"
**Impact:** Quick identification of streaming service type

## Related Panels

- **Panel 1:** Active Streaming Sessions - See current bandwidth for devices shown here
- **Panel 8:** Streaming Service Detection - Identify which services these patterns represent
- **Panel 10:** Bandwidth Drops (Potential Stalls) - See buffering events on this timeline
- **Panel 11:** Top Streaming Devices - See total bandwidth rankings for these devices
- **Panel 3:** CDN Latency - Correlate bandwidth drops with latency spikes
- **Panel 4:** Packet Loss to CDNs - Correlate bandwidth issues with packet loss
- **Main Dashboard Panel 3:** Bandwidth Over Time - Compare streaming to total network traffic

## Investigation Workflow

### Workflow 1: Streaming Session Analysis

**When analyzing a streaming session:**

1. **Identify device** - Note which line/color represents the device
2. **Assess pattern:**
   - **Sustained flat line:** Good quality streaming, consistent bitrate
   - **Gradually rising:** Adaptive bitrate increasing quality
   - **Gradually falling:** Quality degrading (network issues)
   - **Spiky:** Buffering ahead (normal for YouTube) or intermittent issues
   - **Gaps:** Buffering pauses or user pausing content
3. **Check duration** - How long has streaming been active?
4. **Compare to thresholds:**
   - <1 Mbps: SD quality or buffering
   - 1-5 Mbps: HD quality
   - 5-25 Mbps: Full HD quality
   - >25 Mbps: 4K quality
5. **Cross-reference:**
   - Panel 1: Current bandwidth value
   - Panel 8: Which service is being streamed
   - Panel 10: Any buffering events?

### Workflow 2: Buffering Investigation

**When you see bandwidth drops or irregular patterns:**

1. **Identify drop characteristics:**
   - **Duration:** Brief (<10s) vs sustained (>30s)
   - **Frequency:** One-time vs recurring
   - **Pattern:** Random vs periodic
2. **Check concurrent activity:**
   - Are multiple devices affected simultaneously? → Network issue
   - Single device affected? → Device or WiFi issue
3. **Correlate with QoS metrics:**
   - Panel 3 (CDN Latency): Spike during drop? → CDN issue
   - Panel 4 (Packet Loss): Elevated during drop? → Network quality
   - Panel 5 (Jitter): High during drop? → Connection instability
4. **Check total bandwidth:**
   - Sum all device bandwidth at time of drop
   - Compare to link capacity (>80% = saturation)
5. **Determine root cause:**
   - Network saturation: Multiple devices + total >80% capacity
   - CDN issue: Latency spike + single CDN affected
   - WiFi issue: Single wireless device + good wired device performance
   - ISP issue: All devices affected + external latency high

### Workflow 3: Pattern Recognition

**When identifying streaming service types:**

1. **Analyze bandwidth pattern:**
   - **Netflix pattern:** Smooth curve, gradually rising, occasional plateaus
   - **YouTube pattern:** Spikes every 30-60s (preloading), high variance
   - **Disney+ pattern:** Very consistent, flat line, low variance
   - **Live stream pattern:** Constant bitrate, perfectly flat
   - **Short-form pattern:** Brief spikes (30-120s), gaps between
2. **Verify with DNS:**
   - Panel 13: Check recent DNS queries for device
   - Match timing of queries to bandwidth pattern start
3. **Confirm with service detection:**
   - Panel 8: See which services device has accessed
4. **Document pattern:**
   - Note device and pattern characteristics
   - Helps with future rapid identification

### Workflow 4: Quality Assessment Over Time

**When assessing streaming quality trends:**

1. **Select time range:** 1-6 hours to see session evolution
2. **Identify quality changes:**
   - Rising bandwidth: Quality improving (good)
   - Falling bandwidth: Quality degrading (bad)
   - Stable: Consistent experience
3. **Count quality transitions:**
   - Frequent changes: Unstable connection (adaptive bitrate struggling)
   - Rare changes: Stable connection (adaptive bitrate working well)
4. **Check time-of-day correlation:**
   - Degradation during peak hours (evening)? → Congestion
   - Degradation at specific times? → Interference pattern
   - Random degradation? → Intermittent issue
5. **Compare devices:**
   - All devices degrade together? → Shared network issue
   - One device degrades? → Device-specific issue

## Common Scenarios & Responses

### Scenario 1: Smooth Rising Pattern (Netflix Style)

**Pattern:** Bandwidth starts at 3-5 Mbps, gradually rises to 15-25 Mbps over 5-10 minutes

**Analysis:**

- This is Netflix's adaptive bitrate algorithm working optimally
- Starts conservatively to avoid buffering
- Gradually increases as buffer builds
- Indicates good network conditions

**Expected Behavior:**

- Should plateau at device/content capability
- No drops or interruptions
- Mean bandwidth 10-15 Mbps for HD, 25+ Mbps for 4K

**Action:** None needed - this is perfect streaming behavior

### Scenario 2: Spiky Pattern (YouTube Style)

**Pattern:** Bandwidth spikes to 20-30 Mbps for 5-10 seconds, drops to near zero, repeats every 30-60 seconds

**Analysis:**

- This is YouTube's aggressive preloading strategy
- Loads video segments ahead of playback
- Drops to zero during playback of cached segments
- Normal behavior for YouTube

**Characteristics:**

- High variance (50-80%)
- Regular spike intervals
- Brief high-bandwidth bursts
- Long low-bandwidth periods

**Action:** None needed - YouTube working as designed

**Note:** This pattern can cause issues on bandwidth-limited connections as it competes aggressively with other traffic

### Scenario 3: Declining Bandwidth Pattern

**Pattern:** Starts at 10-15 Mbps, gradually declines to 2-3 Mbps over 10-15 minutes

**Analysis:**

- Adaptive bitrate reducing quality due to network issues
- Indicates deteriorating network conditions
- User will experience quality degradation

**Investigation:**

1. Check Panel 3 (CDN Latency): Gradually rising? → CDN overload
2. Check Panel 4 (Packet Loss): Increasing? → Network degradation
3. Check total bandwidth: Are other devices using more? → Saturation
4. Check time of day: Peak hours? → Expected congestion

**Root Causes:**

- Network saturation (other users/devices)
- CDN overload (too many users on CDN node)
- WiFi interference increasing
- ISP congestion during peak hours

**Action:**

- If saturation: Reduce other bandwidth usage
- If CDN: May resolve automatically (CDN load balancing)
- If WiFi: Move closer to AP or switch to wired
- If ISP: Contact ISP or wait for off-peak hours

### Scenario 4: Intermittent Pattern (On/Off)

**Pattern:** Bandwidth present for 30-120 seconds, absent for 10-30 seconds, repeats

**Analysis - Two Possible Causes:**

**A. Short-form content (TikTok, YouTube Shorts, Stories):**

- Brief videos load quickly
- Gaps between videos normal
- Pattern: On (video loads), Off (user browsing), On (next video)
- Action: None needed - normal usage pattern

**B. Buffering pauses:**

- Video loads, plays until buffer empty, pauses to load more
- Indicates insufficient bandwidth or network issues
- Pattern: On (buffering), Off (playing buffer), On (rebuffering)
- Action: Investigate network issues

**How to distinguish:**

- Check Panel 10: Buffering shows drops <500 kbps during "On" periods
- Check Panel 13: Short-form shows many different domains rapidly
- Check timing: Buffering has consistent intervals, short-form varies

### Scenario 5: Multiple Devices Simultaneous Drop

**Pattern:** All streaming devices bandwidth drops sharply at same time

**Analysis:**

- Shared network event affecting all devices
- Not device-specific or CDN-specific
- High priority investigation needed

**Investigation Priority:**

1. **Check total bandwidth:** Did total network usage spike? → Saturation
2. **Check QoS metrics (Panels 3-5):** All degraded? → Network event
3. **Check time:** Exactly on the hour? → ISP maintenance window
4. **Duration:** Brief (<60s) vs sustained (>5 minutes)

**Root Causes:**

- **Brief drops:** ISP routing change, brief congestion, WiFi interference
- **Sustained drops:** ISP outage, router issue, upstream congestion
- **On-the-hour:** Scheduled maintenance or backup jobs

**Action:**

- Brief: Monitor for recurrence, may self-resolve
- Sustained: Check router logs, contact ISP
- Scheduled: Adjust backup/maintenance schedules to off-peak

### Scenario 6: Single Device Oscillating Bandwidth

**Pattern:** One device bandwidth cycles between 1 Mbps and 10 Mbps every 10-30 seconds

**Analysis:**

- Adaptive bitrate struggling with variable network conditions
- Device experiencing unstable connection
- Other devices stable → Device-specific issue

**Investigation:**

1. **Check device type:** Wireless device? → WiFi issue likely
2. **Check Panel 12 (Connections):** High connection count? → Competing traffic on device
3. **Check Panel 5 (Jitter):** Elevated? → Connection instability
4. **Check physical location:** Far from AP? → Signal strength issue

**Root Causes:**

- WiFi interference (microwave, neighbor networks)
- Weak WiFi signal (distance, obstacles)
- Device switching between WiFi bands (2.4 GHz ↔ 5 GHz)
- Background processes on device competing for bandwidth

**Action:**

- Move device closer to access point
- Switch to wired connection if possible
- Change WiFi channel to avoid interference
- Check device for background updates/uploads
- Consider dedicated streaming VLAN/SSID

## Files Referenced

- **Dashboard JSON:** `/Users/kirkl/src/network-monitoring/grafana-dashboards/streaming-monitor.json` (Panel ID 2)
- **Provisioned Dashboard:** `/Users/kirkl/src/network-monitoring/grafana-provisioning/dashboards/streaming-monitor.json` (Panel ID 2)
- **Router Export Script:** `/root/bin/send-bandwidth-to-influx.sh` (on GL-MT2500A)
- **Telegraf Config:** `/Users/kirkl/src/network-monitoring/telegraf.conf` (socket_listener input, lines 6-10)
- **Router nlbwmon Config:** `/etc/config/nlbwmon` (bandwidth monitoring, 1-minute commit interval)

## Streaming Quality Metrics

### Bandwidth Pattern Interpretation

| Pattern | Mean Bandwidth | Variance | Quality Assessment |
|---------|---------------|----------|-------------------|
| Flat high (>10 Mbps) | 15+ Mbps | <20% | Excellent - Full HD/4K stable |
| Rising smooth | 8-20 Mbps | <30% | Good - HD with adaptive improvement |
| Moderate spiky | 5-15 Mbps | 40-60% | Acceptable - HD with preloading |
| Declining | 3-8 Mbps | 30-50% | Degrading - Quality reducing |
| Low spiky | 1-5 Mbps | >50% | Poor - SD with frequent buffering |
| Intermittent | <3 Mbps | >70% | Very Poor - Constant buffering |

### Time-of-Day Quality Expectations

**Peak Hours (6 PM - 11 PM):**

- Expect 10-30% lower bandwidth due to congestion
- More quality transitions (adaptive bitrate working harder)
- Acceptable: 720p/1080p instead of 4K
- Action threshold: <5 Mbps sustained = investigate

**Off-Peak Hours (1 AM - 6 AM):**

- Expect optimal bandwidth (minimal congestion)
- Stable high bitrates expected
- Should achieve maximum quality (4K if capable)
- Action threshold: <10 Mbps = unusual, investigate

**Daytime (9 AM - 5 PM):**

- Moderate usage, variable by household
- Remote work video calls may compete
- Acceptable: Some quality variation
- Action threshold: <3 Mbps = investigate

### Session Duration Analysis

| Duration | Pattern | Typical Content |
|----------|---------|----------------|
| <5 min | Brief spikes | YouTube clips, news, previews |
| 5-30 min | Moderate sustained | TV episodes, YouTube videos |
| 30-90 min | Long sustained | Movies, long videos |
| 90+ min | Extended sustained | Binge watching, live streams |
| Intermittent 2-5 min bursts | Repeated brief | Short-form (TikTok, Shorts) |

## Buffering Detection Patterns

### Pattern 1: Gradual Bandwidth Decline

**Signature:** Smooth decrease from high to low bandwidth over 5-15 minutes

**Buffering Correlation:**

- Check Panel 10 at end of decline
- Expect buffering events when bandwidth falls below quality threshold
- Example: 4K stream declining to 3 Mbps → buffering inevitable

**Root Cause Indicators:**

1. **All devices declining:** Network or ISP congestion
2. **Single device declining:** WiFi signal degradation or device issue
3. **Time-correlated:** Peak hour congestion
4. **CDN-correlated:** Check Panel 3 for specific CDN latency increase

**Buffering Timing:**

- Buffering typically starts when bandwidth drops to 70% of quality requirement
- Example: 1080p needs 8 Mbps, buffering starts at ~5 Mbps

### Pattern 2: Sudden Bandwidth Drops (Cliffs)

**Signature:** Abrupt drops from high bandwidth to <1 Mbps

**Buffering Certainty:** High - will cause immediate buffering

**Investigation:**

1. **Check duration of drop:**
   - <10s: Brief interruption, may recover from buffer
   - 10-30s: Visible buffering, user will notice
   - >30s: Significant interruption, potential user action
2. **Check if drop coincides with other devices:**
   - Yes: Network event (WiFi reset, router issue, ISP)
   - No: Device-specific (app crash, WiFi roaming, background task)
3. **Check Panel 10:** Should show corresponding bandwidth drop marker

**Recovery Pattern:**

- Good: Returns to previous bandwidth within 10-30s
- Poor: Returns to lower bandwidth (quality degraded)
- Failed: Doesn't recover (streaming stopped)

### Pattern 3: Oscillating Bandwidth (Sawtooth)

**Signature:** Regular cycling between high and low bandwidth

**Buffering Risk:** Moderate to High depending on amplitude

**Analysis:**

- **Small amplitude (±2 Mbps):** Normal adaptive bitrate, minimal buffering risk
- **Medium amplitude (±5 Mbps):** Unstable connection, periodic micro-buffering
- **Large amplitude (>10 Mbps range):** Severe instability, frequent buffering

**Frequency Matters:**

- Fast oscillation (<30s cycle): Serious connection instability
- Slow oscillation (>60s cycle): Adaptive bitrate responding to varying conditions

**Root Causes:**

- WiFi signal fluctuation (movement, interference)
- Competing traffic on device or network
- ISP congestion cycling
- CDN load balancing (device switching between CDN nodes)

### Pattern 4: Bandwidth Spikes Above Normal

**Signature:** Periodic spikes significantly above sustained bandwidth

**Buffering Interpretation:** **NOT buffering** - this is preloading

**Pattern Recognition:**

- YouTube: 30-60s regular spikes (aggressive preloading)
- Netflix: Gradual rise no spikes (smooth adaptive bitrate)
- Disney+: Consistent, minimal spikes (conservative buffering)

**Spike Characteristics:**

- Height: 2-5x sustained bandwidth
- Duration: 5-20 seconds
- Frequency: Every 30-120 seconds
- Gap behavior: Low/zero bandwidth between spikes

**Action:** None - this is normal buffering strategy, not quality issue

## CDN Performance Analysis

### Correlating Timeline with CDN Metrics

This panel shows device bandwidth, not CDN-specific data. For CDN analysis:

**Cross-Reference Workflow:**

1. **Identify affected device(s)** showing degraded patterns in this panel
2. **Check Panel 8** to determine which streaming service/CDN
3. **Check Panel 3** (CDN Latency) for corresponding latency spikes
4. **Check Panel 9** (CDN Connection Health) for CDN-to-device mapping
5. **Correlate timing** between bandwidth drops and CDN latency spikes

### Service-Specific Bandwidth Pattern to CDN Mapping

| Bandwidth Pattern | Likely Service | CDN | Expected Panel 3 Latency |
|-------------------|----------------|-----|-------------------------|
| Smooth, rising, consistent | Netflix | Akamai, Netflix OCA | <30 ms |
| Spiky, aggressive preload | YouTube | Google Global Cache | <25 ms |
| Smooth, very consistent | Disney+ | Akamai, Bamtech | <30 ms |
| Moderate spikes | Prime Video | CloudFront | <35 ms |
| Variable, adaptive | Hulu | Akamai, Fastly | <35 ms |

### CDN Issue Detection via Timeline

**Scenario:** Multiple devices streaming same service, all show degraded patterns

**Example:** 3 devices streaming Netflix, all show declining bandwidth simultaneously

**CDN Investigation:**

1. **Timeline (this panel):** All Netflix devices declining together
2. **Service Detection (Panel 8):** Confirms all are Netflix
3. **CDN Latency (Panel 3):** Check Akamai/Netflix latency
   - Elevated (>50ms)? → CDN issue confirmed
   - Normal (<30ms)? → Not CDN, check ISP/network
4. **CDN Health (Panel 9):** Shows all devices use same CDN

**Interpretation:**

- Same service + same timing + elevated CDN latency = CDN overload
- Same service + same timing + normal CDN latency = ISP throttling
- Different services + same timing = General network issue

**Action:**

- CDN overload: Usually resolves automatically (CDN load balancing)
- ISP throttling: Contact ISP, consider VPN
- Network issue: Investigate local network/ISP connection
