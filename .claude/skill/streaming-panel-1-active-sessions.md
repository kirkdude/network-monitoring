# Streaming Panel 1: Active Streaming Sessions

## Panel Overview

- **Panel ID:** 1
- **Title:** Active Streaming Sessions
- **Type:** Stat (Card with value and sparkline)
- **Grid Position:** x=0, y=0, width=12, height=8 (top-left, half dashboard width)
- **Purpose:** Identifies and displays devices currently engaged in streaming activity based on sustained high bandwidth (>1 Mbps for 3+ consecutive 10-second intervals)

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
  |> filter(fn: (r) => r._value > 1000000)
  |> group(columns: ["device_name"])
  |> last()
  |> map(fn: (r) => ({r with _value: float(v: r._value) * 8.0 / 10.0}))
```

**Query Breakdown:**

1. **Streaming Candidate Detection (First query):**
   - Aggregate bandwidth in 10-second windows
   - Filter for receive (download) traffic >1 MB/s (1,000,000 bytes)
   - Count how many intervals each device meets threshold
   - Keep only devices with ≥3 intervals (30 seconds sustained)
   - Extract device names into array for filtering

2. **Current Bandwidth Display (Second query):**
   - Filter for streaming candidate devices only
   - Show current bandwidth (last 10-second window)
   - Convert bytes/s to bits/s for display (× 8.0 / 10.0)

### Metrics Used

- **InfluxDB:** `bandwidth` measurement with `direction="rx"` tag
  - Tags: `device_name`, `ip`, `mac`, `protocol`, `direction`
  - Field: `bytes` (integer - delta values sent every minute from router)
  - Type: Event-based (deltas, not cumulative counters)

### Data Collection Flow

1. **Router (GL-MT2500A):** nlbwmon tracks per-IP bandwidth by protocol
   - Commit interval: 1 minute for real-time data
2. **Export Script:** `/root/bin/send-bandwidth-to-influx.sh` (cron every minute)
   - Calculates deltas from previous run
   - Resolves device names via `/root/bin/resolve-device-name.sh`
   - Sends events via UDP to Telegraf
3. **Telegraf:** Receives UDP packets on port 8094 (InfluxDB line protocol)
4. **InfluxDB:** Stores bandwidth events in "network" bucket
5. **Grafana:** Queries and displays active streaming sessions

## Current Configuration

### Thresholds & Colors

- **Red:** 0 - 999,999 bps (<1 Mbps) - Buffering or low quality
- **Yellow:** 1,000,000 - 4,999,999 bps (1-5 Mbps) - SD to HD streaming
- **Green:** 5,000,000+ bps (≥5 Mbps) - Full HD or 4K streaming

### Display Settings

- **Unit:** bps (bits per second)
- **Visualization Type:** Stat card
- **Color Mode:** Value-based coloring
- **Graph Mode:** Area sparkline showing recent trend
- **Text Mode:** Value and device name displayed
- **Display Name:** `${__field.labels.device_name}` - Shows friendly device name

### Time Range

- Uses: dashboard time range variables `v.timeRangeStart` and `v.timeRangeStop`
- Default: Last 1 hour (now-1h to now)
- Auto-refresh: Every 5 seconds (dashboard setting)
- **Streaming detection window:** 30 seconds (3 × 10-second intervals)

## Critical Lessons Learned - Streaming Device Detection

### Issue 1: False Positives from Downloads

**Problem:** Large file downloads (software updates, backups) mistakenly identified as streaming

**Solution:** Require sustained bandwidth for 30+ seconds

- Single large spike = download
- Consistent 30+ seconds = streaming
- 3 consecutive 10-second intervals filters out most downloads

### Issue 2: Missing Devices During Brief Buffering

**Problem:** Device disappears from panel during 10-15 second buffering events

**Reasoning:** This is correct behavior - device is NOT actively streaming during buffer
**Alternative:** Could reduce requirement to 2 intervals (20 seconds) to be more lenient

### Issue 3: Type Conversion for Rate Calculation

**Problem:** `aggregateWindow` returns integer bytes, but rate calculation needs float

**Solution:** Explicitly convert to float BEFORE arithmetic:

```flux
|> map(fn: (r) => ({r with _value: float(v: r._value) * 8.0 / 10.0}))
```

### Issue 4: Streaming Candidate Array Performance

**Pattern:** Using `findColumn()` to create device array, then `contains()` for filtering

**Performance:** Efficient for <100 devices, but consider alternatives for larger networks:

- Option 1: Join tables instead of array membership
- Option 2: Use subquery with `join()` function

## What's Working Well

- ✅ Accurately identifies streaming devices (validated against known TVs, tablets)
- ✅ Filters out short-duration downloads and web browsing
- ✅ Real-time updates every 5 seconds
- ✅ Color-coded bandwidth gives instant quality assessment
- ✅ Sparkline shows bandwidth trends (stable vs fluctuating)
- ✅ Works across all device types (TVs, tablets, phones, computers)
- ✅ Device names are human-readable (resolved via registry)

## Current Gaps

- ❌ No upload bandwidth consideration (upload streaming like video calls not detected)
- ❌ No streaming service identification (can't tell Netflix from YouTube)
- ❌ No quality estimation beyond bandwidth (doesn't factor latency, jitter, loss)
- ❌ No historical context (can't see if this is normal for device)
- ❌ No drill-down to see which domains/services device is accessing
- ❌ Threshold is fixed (doesn't adapt to device capability or content type)
- ❌ Brief buffering events cause device to disappear from panel

## Potential Improvements

### 1. Add Streaming Service Indicator

**What:** Show which service is being streamed (Netflix, YouTube, etc.)
**How:** Correlate with Panel 8 (Streaming Service Detection) data:

```flux
// Join with DNS queries to identify service
streaming_devices = <streaming candidate query>

dns_services = from(bucket: "network")
  |> range(start: -5m)
  |> filter(fn: (r) => r._measurement == "dns_query")
  |> filter(fn: (r) => r._value =~ /netflix|youtube|disney/)
  |> group(columns: ["device_name"])
  |> last()

join(tables: {bandwidth: streaming_devices, service: dns_services}, on: ["device_name"])
```

**Display:** "LG TV (Netflix) - 25 Mbps"
**Impact:** Immediate identification of what users are watching

### 2. Add Quality Score Indicator

**What:** Calculate streaming quality score (1-10) based on bandwidth + QoS metrics
**How:** Combine bandwidth with latency/jitter/loss from Panels 3-5:

```
Quality Score = bandwidth_score × 0.4 + latency_score × 0.3 + jitter_score × 0.2 + loss_score × 0.1
```

**Display:** "LG TV - 25 Mbps [Quality: 9/10]"
**Impact:** Instant visibility into actual streaming experience

### 3. Add Upload Streaming Detection

**What:** Detect video calls, live streaming, gaming (upload-heavy activities)
**How:** Parallel query for `direction="tx"` with similar thresholds:

```flux
upload_streaming_candidates = from(bucket: "network")
  |> filter(fn: (r) => r.direction == "tx")
  |> filter(fn: (r) => r._value > 500000)  // 500 KB/s upload
  |> <same pattern as download>
```

**Display:** Show combined "15 streaming (12 download, 3 upload)"
**Impact:** Capture video conferencing and live streaming activity

### 4. Add Adaptive Thresholds

**What:** Adjust streaming detection threshold based on time of day and device type
**How:**

- Nighttime (10 PM - 6 AM): Lower threshold to 2 Mbps (SD streaming)
- Daytime: Current 1 Mbps threshold
- Known TVs/tablets: Require 3 Mbps minimum (HD expected)

**Impact:** More accurate detection based on expected usage patterns

### 5. Add Duration Indicator

**What:** Show how long device has been streaming
**How:** Track first occurrence of streaming pattern, calculate duration:

```flux
|> elapsed(unit: 1m)
|> cumulativeSum()
```

**Display:** "LG TV - 25 Mbps [Streaming for 45 min]"
**Impact:** Identify binge-watching vs brief clips

## Related Panels

- **Panel 2:** Streaming Bandwidth Timeline - See temporal patterns for these devices
- **Panel 8:** Streaming Service Detection - Identify which services these devices are using
- **Panel 10:** Bandwidth Drops (Potential Stalls) - See if these devices experience buffering
- **Panel 11:** Top Streaming Devices - See total bandwidth consumption rankings
- **Panel 13:** Recent DNS Queries - See streaming domains accessed by these devices
- **Main Dashboard Panel 1:** Top Bandwidth Users (Download) - Compare streaming to total network traffic

## Investigation Workflow

### Workflow 1: Streaming Device Classification

**When you see a device in this panel:**

1. **Verify streaming activity** - Check Panel 2 (Timeline) for sustained pattern (not spikes)
2. **Identify service** - Check Panel 8 (Service Detection) to see Netflix/YouTube/etc.
3. **Check quality** - Bandwidth >5 Mbps = HD, >25 Mbps = 4K
4. **Verify QoS** - Check Panels 3-5 (latency, loss, jitter) for quality issues
5. **Correlate DNS** - Check Panel 13 for streaming domain queries in last 5 minutes

**Expected Pattern:**

- Sustained bandwidth for >30 seconds
- Low connection count (Panel 12 - typically 1-5 connections)
- Streaming service DNS queries (Panel 13)
- Low latency/jitter/loss (Panels 3-5)

### Workflow 2: Troubleshooting Missing Device

**When a known streaming device is NOT in this panel:**

1. **Check total bandwidth** - Panel 2 or Main Dashboard Panel 1
   - If device shows bandwidth but not here → Below 1 Mbps threshold (SD streaming or buffering)
   - If no bandwidth → Device idle or connectivity issue
2. **Check sustainability** - Bandwidth might be spiking but not sustained 30+ seconds
   - Short spikes = downloading/buffering, not streaming
3. **Check direction** - Device might be uploading (video call) not downloading
   - Check Main Dashboard Panel 2 (Upload Bandwidth)
4. **Check time window** - Device might have stopped streaming
   - Extend dashboard time range to see historical activity

### Workflow 3: Quality Assessment

**When assessing streaming quality for a device:**

1. **Identify device** - Note bandwidth displayed (bps)
2. **Map to resolution:**
   - <3 Mbps → SD (480p)
   - 3-5 Mbps → HD (720p)
   - 5-8 Mbps → Full HD (1080p)
   - 25-40 Mbps → 4K (2160p)
   - 100+ Mbps → 8K (4320p)
3. **Check QoS metrics** (Panels 3-5) to verify quality requirements met
4. **Cross-reference** with buffering panel (Panel 10) for issues

## Common Scenarios & Responses

### Scenario 1: Multiple Devices Streaming Simultaneously

**Pattern:** 4+ devices showing active streaming, total bandwidth >50 Mbps

**Investigation:**

1. Check total bandwidth usage across all devices (sum values)
2. Compare to available bandwidth (100 Mbps, 1 Gbps link capacity)
3. If >80% link utilization → Saturation risk
4. Check Panel 10 for bandwidth drops indicating contention

**Action:**

- If saturation detected: Implement QoS prioritization
- If specific device causing issues: Investigate via drill-down
- Consider bandwidth upgrade if consistent pattern

### Scenario 2: Device Shows Red (< 1 Mbps) While "Streaming"

**Pattern:** Device in panel but bandwidth <1 Mbps (red indicator)

**Investigation:**

1. **Likely buffering** - Check Panel 10 for drops
2. **Check QoS** - Panels 3-5 for latency/loss/jitter issues
3. **Check CDN** - Panels 3 & 9 for CDN performance problems
4. **Timeline** - Panel 2 to see if this is temporary or sustained

**Root Causes:**

- Network congestion (local or ISP)
- CDN overload or routing issues
- WiFi interference (if device is wireless)
- ISP throttling streaming traffic

**Action:**

- If local congestion: Reduce other bandwidth usage
- If CDN issue: May resolve automatically (CDN failover)
- If WiFi: Check interference, consider wired connection
- If persistent: Contact ISP about throttling

### Scenario 3: Unknown Device Streaming High Bandwidth

**Pattern:** Unfriendly device name (MAC address) showing 20+ Mbps

**Investigation:**

1. Note device IP and MAC address from Grafana query inspector
2. Check router DHCP leases: `ssh root@192.168.1.2 'cat /tmp/dhcp.leases'`
3. Lookup MAC OUI (first 6 characters) to identify manufacturer
4. Check Panel 13 (DNS Queries) to see domains being accessed
5. Correlate with Panel 8 to identify streaming service

**Action:**

- If legitimate: Add to device registry `/root/etc/device-registry.conf`
- If unknown/suspicious: Move to guest network or block
- If IoT device: Should NOT be streaming - investigate for compromise

### Scenario 4: Streaming During Off-Hours (2-6 AM)

**Pattern:** Device streaming between 2 AM and 6 AM

**Investigation:**

1. **Identify device type** - Check device registry or MAC OUI
2. **Determine service** - Panel 8 (which streaming service?)
3. **Check pattern** - Panel 2 timeline (single session vs repeated)
4. **Review domains** - Panel 13 for suspicious domains

**Analysis:**

- Smart TV with auto-play: Normal (Netflix episode queue)
- Mobile device: Possible sleepless user, normal
- Computer: Unusual - potential compromise or scheduled task
- IoT device: Suspicious - should not stream

**Action:**

- Smart TV/Mobile: Monitor for excessive usage
- Computer: Investigate running processes, check for malware
- IoT: Isolate immediately, investigate for compromise

### Scenario 5: Intermittent Streaming (Device Appears/Disappears)

**Pattern:** Device repeatedly enters and leaves active sessions list

**Investigation:**

1. **Check Panel 2 timeline** - Look for bandwidth pattern
   - Spiky pattern = Short clips (YouTube, TikTok)
   - Sustained then gap = Buffering issues
   - Regular intervals = User pausing content
2. **Check Panel 10** - Are drops correlated with disappearances?
3. **Check QoS** - Panels 3-5 for degraded metrics

**Root Cause Decision Tree:**

- Spiky + varied services (Panel 8) = Short-form content browsing (normal)
- Sustained + drops (Panel 10) = Buffering due to QoS issues
- Regular intervals = User behavior (pausing, switching content)

**Action:**

- Short-form content: Normal behavior, no action needed
- Buffering: Investigate QoS issues (follow Buffering Workflow)
- User pausing: Normal, no action needed

## Files Referenced

- **Dashboard JSON:** `/Users/kirkl/src/network-monitoring/grafana-dashboards/streaming-monitor.json` (lines TBD, Panel ID 1)
- **Provisioned Dashboard:** `/Users/kirkl/src/network-monitoring/grafana-provisioning/dashboards/streaming-monitor.json` (Panel ID 1)
- **Router Export Script:** `/root/bin/send-bandwidth-to-influx.sh` (on GL-MT2500A router)
- **Router Device Registry:** `/root/etc/device-registry.conf` (device name resolution)
- **Router Name Resolution:** `/root/bin/resolve-device-name.sh` (device ID system)
- **Telegraf Config:** `/Users/kirkl/src/network-monitoring/telegraf.conf` (socket_listener input)

## Streaming Quality Metrics

### Bandwidth Requirements by Resolution

| Resolution | Minimum | Recommended | Optimal | Codec Notes |
|------------|---------|-------------|---------|-------------|
| 480p (SD) | 1.5 Mbps | 3 Mbps | 5 Mbps | MPEG-4/H.264 |
| 720p (HD) | 3 Mbps | 5 Mbps | 8 Mbps | H.264 |
| 1080p (FHD) | 5 Mbps | 8 Mbps | 12 Mbps | H.264/H.265 |
| 4K (UHD) | 25 Mbps | 40 Mbps | 60 Mbps | H.265/VP9/AV1 |
| 8K | 100 Mbps | 150 Mbps | 200 Mbps | H.266/AV1 |

### Panel Threshold Interpretation

**Red Zone (<1 Mbps):**

- SD quality (480p) at risk
- Severe buffering likely
- User experience: Poor

**Yellow Zone (1-5 Mbps):**

- SD to HD quality (480p-720p)
- Occasional buffering possible
- User experience: Acceptable

**Green Zone (≥5 Mbps):**

- Full HD to 4K quality (1080p-2160p)
- Smooth streaming expected
- User experience: Good to Excellent

### Service-Specific Bandwidth Patterns

**Netflix:**

- SD: 3 Mbps
- HD: 5 Mbps
- 4K: 25 Mbps
- Uses adaptive bitrate (fluctuates 20-30%)

**YouTube:**

- 480p: 1.1 Mbps
- 720p: 2.5 Mbps
- 1080p: 4.5 Mbps
- 4K: 35 Mbps
- Preloads aggressively (bandwidth spikes)

**Disney+:**

- HD: 5 Mbps
- 4K: 25 Mbps
- More consistent bandwidth (less aggressive buffering)

**Prime Video:**

- SD: 0.9 Mbps
- HD: 3.5 Mbps
- 4K: 15 Mbps
- Lower 4K bandwidth (better compression)

## Buffering Detection Patterns

### Pattern 1: Sustained Low Bandwidth (<3 Mbps while streaming)

**Indicator:** Device shows in panel but consistently red/yellow

**Root Cause Analysis:**

1. Check network saturation (Panel 2 total bandwidth)
2. Check QoS metrics (Panels 3-5) - latency/loss elevated?
3. Check CDN performance (Panel 3) - specific CDN slow?

**Decision Tree:**

- All devices affected + high total bandwidth → Network saturation
- Single device + good QoS → Device capability/WiFi issue
- Multiple devices + elevated latency → ISP or CDN issue

**Resolution:**

- Saturation: Reduce concurrent streams or upgrade link
- Device: Move to wired or closer to AP
- ISP/CDN: Contact ISP or wait for CDN failover

### Pattern 2: Bandwidth Oscillation (Cycling red-yellow-green)

**Indicator:** Device bandwidth cycles through thresholds rapidly

**Root Cause:** Adaptive bitrate responding to variable network conditions

**Analysis:**

1. Check Panel 10 for concurrent bandwidth drops
2. Check Panel 5 for elevated jitter (>10ms)
3. Check WiFi interference if wireless device

**Interpretation:**

- Rapid cycling (<10s intervals) = Network instability
- Slow cycling (30-60s intervals) = Normal adaptive bitrate
- Pattern correlated with other devices = Shared network issue

**Resolution:**

- Network instability: Investigate interference, congestion
- Normal ABR: No action needed (working as designed)
- Shared issue: Address bandwidth contention

### Pattern 3: Intermittent Presence (Appears/Disappears)

**Indicator:** Device enters and exits panel repeatedly

**Root Causes:**

1. **Buffering pauses** - Bandwidth drops below threshold during buffer refill
2. **User pausing** - User pausing and resuming content
3. **Short-form content** - Brief videos (TikTok, YouTube Shorts)

**Diagnosis:**

1. Check Panel 2 timeline for pattern regularity
2. Check Panel 10 for drops occurring during absences
3. Check Panel 13 for content type (short videos vs long-form)

**Action:**

- Buffering detected: Follow buffering investigation workflow
- User behavior: No action needed
- Short-form: Normal pattern for that content type

### Pattern 4: High Bandwidth But Poor Quality Reports

**Indicator:** Device shows green (>5 Mbps) but user reports buffering

**Root Cause:** Bandwidth adequate but QoS metrics poor

**Investigation Priority:**

1. **Check latency** (Panel 3) - >150ms causes buffering
2. **Check packet loss** (Panel 4) - >0.5% causes stuttering
3. **Check jitter** (Panel 5) - >15ms causes glitches
4. **Check DNS** (Panel 6) - >100ms causes initial load delays

**Resolution:** This is a QoS issue, not bandwidth issue

- Follow QoS troubleshooting workflows
- Bandwidth is necessary but not sufficient for quality streaming

## CDN Performance Analysis

### CDN to Streaming Service Mapping

**This panel shows aggregate bandwidth, not CDN-specific metrics**

For CDN-specific analysis, cross-reference with:

- **Panel 3:** CDN Latency (ICMP Ping) - CDN response times
- **Panel 9:** CDN Connection Health - Device-to-CDN mapping
- **Panel 13:** Recent DNS Queries - CDN domain resolution activity

### Using This Panel for CDN Diagnosis

While this panel doesn't directly show CDN metrics, it provides context:

**Scenario:** Multiple devices streaming, some buffering (red/yellow)

**CDN Investigation Workflow:**

1. **Identify affected devices** in this panel (red/yellow indicators)
2. **Map to services** (Panel 8) - All Netflix? All YouTube?
3. **Check CDN latency** (Panel 3) - Is specific CDN elevated?
4. **Correlate** - If all Netflix slow + Akamai latency high → CDN issue

### Expected Bandwidth by CDN/Service

| Service | CDN | Typical Range | Quality |
|---------|-----|---------------|---------|
| Netflix | Akamai, Netflix OCAs | 5-40 Mbps | HD to 4K |
| YouTube | Google Global Cache | 2-35 Mbps | 720p to 4K |
| Prime Video | CloudFront | 3-15 Mbps | HD to 4K |
| Disney+ | Akamai, Bamtech | 5-25 Mbps | HD to 4K |
| Hulu | Akamai, Fastly | 3-16 Mbps | HD to 4K |

**Diagnostic Use:**

- Netflix device <5 Mbps + high Akamai latency → CDN overload
- YouTube device <2.5 Mbps + good Google Cache latency → Device/WiFi issue
- Multiple services affected + high all CDN latency → ISP uplink issue
