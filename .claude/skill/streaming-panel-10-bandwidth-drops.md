# Streaming Panel 10: Bandwidth Drops (Potential Stalls)

## Panel Overview

- **Panel ID:** 5
- **Title:** Bandwidth Drops (Potential Stalls)
- **Type:** Timeseries (Point markers)
- **Grid Position:** x=0, y=34, width=24, height=8 (full width)
- **Purpose:** Detects and visualizes buffering events by marking bandwidth drops below quality thresholds for active streaming devices - the primary buffering detection panel

## Data Source

### Current: InfluxDB Flux Query

```flux
streaming_candidates = from(bucket: "network")
  |> range(start: v.timeRangeStart, stop: v.timeRangeStop)
  |> filter(fn: (r) => r._measurement == "bandwidth" and r.direction == "rx")
  |> aggregateWindow(every: 10s, fn: sum, createEmpty: false)
  |> filter(fn: (r) => r._value > 500000)
  |> group(columns: ["device_name"])
  |> count()
  |> filter(fn: (r) => r._value >= 3)
  |> findColumn(fn: (key) => true, column: "device_name")

from(bucket: "network")
  |> range(start: v.timeRangeStart, stop: v.timeRangeStop)
  |> filter(fn: (r) => r._measurement == "bandwidth" and r.direction == "rx")
  |> filter(fn: (r) => contains(value: r.device_name, set: streaming_candidates))
  |> aggregateWindow(every: 5s, fn: sum, createEmpty: false)
  |> group(columns: ["device_name"])
  |> map(fn: (r) => ({r with _value: float(v: r._value) * 8.0 / 5.0}))
  |> filter(fn: (r) => r._value < 500000.0)
```

**Query Breakdown:**

1. **Identify streaming candidates:** Devices with sustained >500 kbps (0.5 Mbps) for 30+ seconds
2. **Detect drops:** Show only when bandwidth falls below 500 kbps threshold
3. **5-second aggregation:** High temporal resolution to catch brief buffering events
4. **Result:** Red point markers appear when streaming devices experience drops

**Key Logic:**

- Lower threshold (500 kbps) than Panel 1 (1 Mbps) to catch early degradation
- Points-only display makes drops immediately visible
- Full-width panel for maximum visibility

## Current Configuration

### Thresholds & Colors

- **Single threshold:** < 500 kbps = RED
- **All points are red:** Emphasizes these are problem events

**500 kbps Threshold Reasoning:**

- SD streaming (480p) needs ~1 Mbps
- Drops below 500 kbps will cause buffering for any quality level
- Lower than Panel 1's 1 Mbps detection to catch early degradation

### Display Settings

- **Unit:** bps
- **Visualization:** Timeseries with POINTS ONLY (no lines)
- **Draw Style:** Points (discrete markers)
- **Point Size:** 8 (large, visible)
- **Fill Opacity:** 0% (no area, just points)
- **Color:** Red (fixed) - all buffering events shown as red dots
- **Legend:** List placement bottom
- **Width:** Full dashboard width (24) for maximum visibility

## Critical Lessons Learned - Buffering Detection

### Issue 1: Threshold Choice (500 kbps)

**Testing:**

- 1 Mbps: Too high, misses early degradation
- 500 kbps: ✅ Catches buffering at all quality levels
- 250 kbps: Too low, shows only severe stalls

**Reasoning:**

- Even SD (480p) needs ~1 Mbps
- 500 kbps = 50% of minimum
- At this level, buffering is imminent or occurring

### Issue 2: Why Streaming Candidates Filter

**Problem:** Without filtering, shows ALL low-bandwidth devices

**Without filter:**

- Shows every idle device
- Thousands of false positives
- Unusable for buffering detection

**With filter (current):**

- Shows only devices that were streaming >500 kbps
- Then dropped below 500 kbps
- True buffering events only

### Issue 3: Points vs Lines Display

**Design choice:** Points only, no connecting lines

**Reasoning:**

- Buffering events are discrete occurrences
- Lines would create visual clutter
- Points make each event immediately visible
- Red dots = problems that need attention

**Impact:** Very effective visual alert system

### Issue 4: False Positives from Stream Ending

**Challenge:** Device stops streaming intentionally, shows as "drop"

**Reality:**

- Stream end looks identical to buffering drop in this panel
- Need context from Panel 2 (does stream resume?)

**Mitigation:** Cross-reference with Panel 2 timeline

- Bandwidth returns? Was buffering
- Bandwidth stays zero? Was stream end

## What's Working Well

- ✅ Immediate visual identification of buffering events
- ✅ Red points highly visible on timeline
- ✅ Full width makes scanning easy
- ✅ Filters out non-streaming devices (no false positives from idle devices)
- ✅ 5-second aggregation catches brief buffering
- ✅ Works across all devices and services
- ✅ Clear correlation with Panel 2 bandwidth timeline

## Current Gaps

- ❌ Can't distinguish buffering from stream end
- ❌ No severity indicator (all drops treated equally)
- ❌ No duration calculation (how long was drop?)
- ❌ No automatic root cause analysis
- ❌ No correlation overlay with QoS metrics
- ❌ Threshold is fixed (doesn't adapt to quality level)

## Potential Improvements

### 1. Add Drop Duration Calculation

**What:** Show how long each buffering event lasted
**How:** Calculate time between drop start and bandwidth recovery

**Display:** Point size or tooltip showing duration

- Small dot: <10s buffering
- Medium: 10-30s
- Large: >30s

**Impact:** Severity assessment at a glance

### 2. Add Root Cause Indicators

**What:** Color-code points by likely cause
**How:** Correlate with Panels 3-5 at time of drop:

- Red: Bandwidth issue (no QoS issues)
- Orange: CDN latency issue
- Yellow: Packet loss issue
- Purple: Jitter/instability issue

**Impact:** Immediate diagnosis direction

### 3. Add Severity Levels

**What:** Different point sizes for severity
**How:** Based on depth and duration of drop:

- Level 1: 250-500 kbps, <10s
- Level 2: 100-250 kbps, 10-30s
- Level 3: <100 kbps, >30s

**Impact:** Prioritize investigation by severity

### 4. Add Multi-Device Pattern Detection

**What:** Highlight when multiple devices buffer simultaneously
**How:** Detect concurrent drops across devices

**Display:** Annotation or different color for shared events

**Impact:** Immediately identifies network-wide vs device-specific issues

### 5. Add Stream End Detection

**What:** Distinguish buffering from intentional stream end
**How:** Check if bandwidth resumes within 60 seconds:

- Resumes: Was buffering
- Doesn't resume: Was stream end (filter out)

**Impact:** Reduce false positives

## Related Panels

- **Panel 2:** Streaming Bandwidth Timeline - Shows full bandwidth context around drops
- **Panel 1:** Active Streaming Sessions - Shows affected devices' current state
- **Panel 3:** CDN Latency - Check latency at time of drop
- **Panel 4:** Packet Loss to CDNs - Check loss at time of drop
- **Panel 5:** Network Jitter - Check stability at time of drop
- **Panel 8:** Streaming Service Detection - Identify which service affected
- **Panel 9:** CDN Connection Health - Map device to CDN for targeted diagnosis

## Investigation Workflow

### Workflow 1: Complete Buffering Root Cause Analysis (8 Steps)

**When red dot appears (buffering detected):**

1. **Identify affected device and time:**
   - Note device name from point hover
   - Note exact timestamp
2. **Check Panel 2 (Bandwidth Timeline):**
   - What was bandwidth before drop?
   - What was bandwidth during drop?
   - Did it recover? How long did drop last?
   - Is there a pattern (multiple drops)?
3. **Check Panel 3 (CDN Latency) at drop time:**
   - <50 ms: Latency NOT the cause
   - 50-100 ms: Latency contributing factor
   - >100 ms: Latency primary cause
4. **Check Panel 4 (Packet Loss) at drop time:**
   - 0%: Loss NOT the cause
   - 0.1-1%: Loss contributing factor
   - >1%: Loss primary cause
5. **Check Panel 5 (Jitter) at drop time:**
   - <5 ms: Jitter NOT the cause
   - 5-10 ms: Jitter contributing factor
   - >10 ms: Jitter primary cause
6. **Check network saturation:**
   - Panel 2: Sum all devices at drop time
   - Compare to link capacity (100 Mbps, 1 Gbps)
   - >80%: Saturation cause
7. **Identify root cause from matrix:**

| Latency | Loss | Jitter | Total BW | Diagnosis |
|---------|------|--------|----------|-----------|
| Normal | Normal | Normal | <80% | Device/WiFi issue |
| High | Normal | Low | <80% | CDN congestion |
| Normal | High | High | <80% | WiFi interference |
| High | High | High | <80% | Network degradation |
| Any | Any | Any | >80% | Network saturation |

8. **Take corrective action based on root cause**

### Workflow 2: Multi-Device Simultaneous Drops

**When multiple red dots appear at same time:**

1. **Count affected devices:**
   - 2-3 devices: May be coincidence
   - 3+ devices: Shared issue likely
2. **Determine shared factor:**
   - All on WiFi? WiFi issue
   - All using same CDN (Panel 9)? CDN issue
   - All using same service (Panel 8)? Service/CDN issue
   - All devices regardless of connection? Network/ISP issue
3. **Check QoS panels (3, 4, 5):**
   - All show issues? Confirmed network event
4. **Check total bandwidth:**
   - Sum Panel 2 all devices
   - >80% capacity? Saturation event
5. **Root cause:**
   - WiFi only + no QoS issues: WiFi problem
   - All devices + QoS issues: Network/ISP event
   - Same CDN + CDN QoS issues: CDN problem
   - Saturation: Bandwidth upgrade or QoS needed

### Workflow 3: Recurring Drop Pattern

**When drops occur at regular intervals:**

1. **Identify pattern period:**
   - Every 5 minutes: Possible scheduled task
   - Every 30 minutes: Possible interference cycle
   - Every hour: Possible maintenance/backup
2. **Check Panel 2 for pattern:**
   - Does bandwidth always drop at same interval?
   - Confirms recurring issue
3. **Investigate timing correlation:**
   - Check system cron jobs
   - Check router scheduled tasks
   - Check neighbor activity patterns (if WiFi)
4. **Root causes:**
   - Scheduled backup running
   - Router QoS recalculation
   - Neighbor WiFi scan/channel change
   - ISP maintenance window

### Workflow 4: Progressive Drop Pattern

**When drops become more frequent over time:**

1. **Pattern:** Rare at start (1-2 drops/hour), increasing to frequent (10+ drops/hour)
2. **Indicates:** Progressive network degradation
3. **Investigation:**
   - Check Panel 3: Latency also rising?
   - Check Panel 4: Loss also increasing?
   - Check time: Peak hour progression?
   - Check Panel 2: Total bandwidth growing?
4. **Root causes:**
   - Peak hour congestion building
   - Hardware overheating (progressive thermal throttling)
   - WiFi interference increasing (neighbors coming home)
5. **Actions:**
   - If thermal: Improve cooling
   - If peak hours: Implement QoS or upgrade
   - If WiFi: Change channel or band

## Common Scenarios & Responses

### Scenario 1: Single Red Dot, Quick Recovery

**Pattern:** One red point, Panel 2 shows brief drop and recovery within 10-20 seconds

**Analysis:** Brief buffering event, likely recovered from buffer

**User Impact:**

- Brief pause or loading spinner
- Quality may reduce briefly
- Typically resumes smoothly

**Investigation (if recurring):**

1. Check if dots appear at regular intervals
2. Check QoS panels for transient spikes
3. If one-time: Acceptable, monitor
4. If recurring: Investigate pattern

**Actions:**

- One-time glitch: No action
- Recurring pattern: Follow full workflow

### Scenario 2: Cluster of Red Dots (Sustained Buffering)

**Pattern:** Many red points densely clustered over 2-5 minutes

**Analysis:** Sustained buffering event, poor user experience

**User Impact:**

- Continuous buffering and pausing
- Quality severely degraded or stream stopped
- User likely frustrated or abandoned stream

**Investigation Priority: HIGH**

- Follow complete 8-step workflow above
- Identify root cause immediately
- Take corrective action

**Expected user behavior:**

- May report issue
- May switch services
- May give up on streaming

### Scenario 3: Red Dots on All Streaming Devices

**Pattern:** Every active streamer (Panel 1) shows red dots at same time

**Analysis:** Network-wide event, shared cause

**Root Causes (in priority order):**

1. **Network saturation:** Check total bandwidth >80% capacity
2. **ISP uplink issue:** Check Panel 3/4 all CDNs affected
3. **Router problem:** Check router CPU, memory, logs
4. **WiFi interference:** If all wireless devices, none wired
5. **ISP maintenance:** Brief reconfiguration

**Investigation:**

1. Calculate total bandwidth (sum Panel 2)
2. Check QoS panels (3, 4, 5) for all CDNs
3. Check router resources
4. Determine scope (WiFi vs all, ISP vs local)

**Actions:**

- Saturation: Reduce streams or upgrade
- ISP: Document and report
- Router: Restart or upgrade
- WiFi: Mitigate interference

### Scenario 4: Red Dots Correlate with Latency Spikes

**Pattern:** Panel 3 shows latency spike, red dots appear 5-15 seconds later in this panel

**Mechanism:**

1. CDN latency increases (Panel 3)
2. TCP throughput reduces due to increased RTT
3. Bandwidth drops below threshold
4. Red dot appears in this panel

**This is classic latency-caused buffering**

**Investigation:**

1. Identify which CDN spiked (Panel 3)
2. Check which services use that CDN (Panel 8, 9)
3. Verify only those service users show drops
4. Conclusion: CDN latency issue

**Actions:**

- Wait for CDN recovery (usually automatic)
- If sustained >30 minutes: Report to service/ISP
- Check Panel 13 for CDN failover attempts

### Scenario 5: Red Dots Without QoS Issues

**Pattern:** Red dots present, but Panels 3, 4, 5 all show good metrics

**Analysis:** Bandwidth issue not caused by latency/loss/jitter

**Possible Causes:**

1. **Device issue:** Device unable to request/process data
2. **App issue:** Streaming app bug or limitation
3. **WiFi signal:** Weak signal (not captured in CDN pings)
4. **Local congestion:** Device's local network segment
5. **Background activity:** Device's other apps consuming bandwidth

**Investigation:**

1. Check if device-specific (one device) or widespread
2. If device-specific: Check device WiFi signal, background processes
3. Check Panel 12: Connection count spike? (competing traffic)
4. Check device type: Known issues with that device model?

**Actions:**

- Device WiFi: Move closer, improve signal
- Background activity: Close apps, disable auto-updates
- Device limitation: May be hardware capability limit
- App issue: Update app, restart app, reinstall

### Scenario 6: Progressive Worsening (Drops Intensifying)

**Pattern:** Starts with few shallow drops, progresses to many deep severe drops

**Analysis:**

- Situation deteriorating
- May lead to complete stream failure
- Urgent investigation needed

**Progression stages:**

1. **Early:** Occasional <10s drops, <3 per hour
2. **Moderate:** Frequent 10-30s drops, 5-10 per hour
3. **Severe:** Constant drops, >20 per hour
4. **Critical:** Sustained <500 kbps, streaming impossible

**Investigation:**

1. Check if progressive or sudden transition
2. Check Panel 2: Is bandwidth declining overall?
3. Check Panel 3: Is latency rising?
4. Check time of day: Peak hours approaching?
5. Identify acceleration rate: How fast is it worsening?

**Root Causes:**

- Peak hour congestion building
- Progressive hardware failure
- Thermal throttling (router/modem overheating)
- Interference intensifying

**Actions:**

- If peak hour: Normal but may need QoS
- If hardware: Check cooling, restart devices
- If accelerating: Immediate action required
- May need to temporarily stop streaming to stabilize

## Files Referenced

- **Dashboard JSON:** `/Users/kirkl/src/network-monitoring/grafana-dashboards/streaming-monitor.json` (Panel ID 5)
- **Router Export Script:** `/root/bin/send-bandwidth-to-influx.sh`
- **Telegraf Config:** `/Users/kirkl/src/network-monitoring/telegraf.conf` (socket_listener)

## Streaming Quality Metrics

### Buffering Threshold Matrix

| Quality | Bitrate | Buffering Starts Below | This Panel Threshold |
|---------|---------|------------------------|---------------------|
| SD (480p) | 1-3 Mbps | 800 kbps | 500 kbps ✓ |
| HD (720p) | 3-5 Mbps | 2.5 Mbps | 500 kbps ✓ |
| Full HD (1080p) | 5-8 Mbps | 4 Mbps | 500 kbps ✓ |
| 4K (UHD) | 25-40 Mbps | 20 Mbps | 500 kbps ✓ |

**500 kbps threshold catches all quality levels**

### Drop Duration to User Impact

| Drop Duration | User Experience | Recovery |
|---------------|-----------------|----------|
| <5 seconds | Brief pause, may not notice if buffered | Immediate |
| 5-10 seconds | Noticeable buffering spinner | Quick |
| 10-30 seconds | Significant interruption | May reduce quality |
| 30-60 seconds | Major disruption, frustrating | Quality reduced |
| >60 seconds | Likely to abandon stream | May not recover |

### Drop Frequency to Quality Impact

| Drops per Hour | Quality Impact | User Tolerance |
|----------------|----------------|----------------|
| 0-2 | Minimal, occasional glitch | Acceptable |
| 2-5 | Noticeable, regular interruptions | Borderline |
| 5-10 | Frequent issues, poor experience | Unacceptable |
| >10 | Constant buffering, unusable | Will abandon |

## Buffering Detection Patterns

### Pattern 1: Isolated Single Drops

**Signature:** Single red dot, long gaps between occurrences

**Buffering Certainty:** Low to Moderate

**Causes:**

- Transient network glitches
- Brief interference
- Single packet burst loss
- Momentary congestion

**User Impact:** Minimal, likely absorbed by buffer

**Action:** Monitor for recurrence, no immediate action

### Pattern 2: Clustered Drops (Burst Buffering)

**Signature:** 5-10 red dots within 2-3 minutes

**Buffering Certainty:** High

**Causes:**

- Network instability period
- CDN node struggling
- WiFi interference event
- Congestion episode

**User Impact:** Significant, multiple buffering events

**Action:** Investigate immediately with full workflow

### Pattern 3: Periodic Drops (Regular Pattern)

**Signature:** Red dots at consistent intervals (every 5, 10, 15 minutes)

**Buffering Certainty:** High, recurring

**Causes:**

- Scheduled task interfering
- Router maintenance interval
- Neighbor device cycling
- Thermal throttling cycle

**Investigation:** Identify period and source

**Action:** Eliminate/mitigate recurring interference source

### Pattern 4: All-Device Simultaneous Drops

**Signature:** All streaming devices show red dots at same timestamp

**Buffering Certainty:** Very High, network event

**Causes:**

- Network saturation
- ISP uplink congestion
- Router overload
- Power fluctuation

**Impact:** All users affected simultaneously

**Priority:** Highest - network-wide issue

### Pattern 5: Progressive Intensity (Drops Accelerating)

**Signature:** Gaps between drops decreasing over time

**Buffering Evolution:**

- Hour 1: 2 drops
- Hour 2: 5 drops
- Hour 3: 15 drops
- Hour 4: Constant drops

**Causes:**

- Congestion building (peak hours)
- Thermal degradation
- Hardware failing
- Interference intensifying

**Action:** Urgent intervention before complete failure

## CDN Performance Analysis

### Using Drops to Identify CDN Issues

**Complete Investigation Chain:**

1. **This panel:** Red dot appears for device
2. **Panel 8:** Which service was device streaming?
3. **Panel 9:** Which CDN was device using?
4. **Panel 3:** Check that CDN's latency at drop time
5. **Panel 4:** Check that CDN's packet loss at drop time

**Example:**

- This panel: LG TV red dot at 8:15 PM
- Panel 8: LG TV was streaming Netflix
- Panel 9: LG TV using Akamai
- Panel 3: Akamai (netflix.com) showed 110ms at 8:15 PM
- Panel 4: Akamai showed 0.5% loss at 8:15 PM
- **Conclusion:** Akamai performance issue caused Netflix buffering on LG TV

### CDN-Specific Buffering Patterns

**Akamai (Netflix, Disney+, Hulu):**

- Drops often during peak hours (high usage)
- Geographic variations (dense urban vs rural)
- Usually recovers via load balancing

**Google (YouTube):**

- Rarely shows drops (excellent infrastructure)
- When drops occur, usually local network issue
- Google's CDN extremely reliable

**CloudFront (Prime Video, Twitch):**

- Moderate drop frequency
- Regional variations
- Generally reliable

**Fastly (Hulu, HBO):**

- Occasional capacity issues
- Smaller network than Akamai/Google
- May show more drops during peak

### Buffering Frequency by CDN Health

**Healthy CDN (Panel 3 <30ms, Panel 4 <0.1% loss):**

- Drops rare (<2 per hour)
- Brief duration (<10s)
- Quick recovery

**Stressed CDN (Panel 3 50-100ms, Panel 4 0.1-1% loss):**

- Moderate drops (3-8 per hour)
- Medium duration (10-30s)
- May reduce quality after recovery

**Failing CDN (Panel 3 >100ms, Panel 4 >1% loss):**

- Frequent drops (>10 per hour)
- Long duration (>30s)
- Often doesn't fully recover
- Users will abandon or switch services
