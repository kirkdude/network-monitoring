# Streaming Panel 5: Network Jitter (Latency Std Dev)

## Panel Overview

- **Panel ID:** 11
- **Title:** Network Jitter (Latency Std Dev)
- **Type:** Timeseries
- **Grid Position:** x=16, y=8, width=8, height=8
- **Purpose:** Monitors latency variability (jitter) to CDN endpoints, detecting connection instability that causes inconsistent streaming quality and micro-buffering even when average latency appears acceptable

## Data Source

### Current: InfluxDB Flux Query

```flux
from(bucket: "network")
  |> range(start: v.timeRangeStart, stop: v.timeRangeStop)
  |> filter(fn: (r) => r._measurement == "ping")
  |> filter(fn: (r) => r._field == "standard_deviation_ms")
  |> aggregateWindow(every: 30s, fn: mean, createEmpty: false)
  |> group(columns: ["url"])
```

**Field:** `standard_deviation_ms` - statistical variance of the 5 ping response times per interval

### Metrics Used

- **InfluxDB:** `ping` measurement from Telegraf
- **Calculation:** Standard deviation of 5 pings (measures spread around mean)
- **Type:** Time-series, 30-second intervals

## Current Configuration

### Thresholds & Colors

- **Green:** 0-4 ms (Stable connection)
- **Yellow:** 5-9 ms (Moderate variability)
- **Red:** 10+ ms (High instability)

**Context:**

- <2 ms: Excellent stability (wired, optimal)
- 2-5 ms: Good stability (typical wired or strong WiFi)
- 5-10 ms: Moderate instability (WiFi, minor issues)
- 10-15 ms: High instability (poor WiFi, interference)
- >15 ms: Severe instability (unusable for real-time)

### Display Settings

- **Unit:** ms
- **Visualization:** Timeseries line graph
- **Legend:** Table with Mean and Max values

## Critical Lessons Learned

### Issue 1: Small Sample Size (5 Pings)

**Challenge:** Standard deviation of only 5 samples can be noisy

**Reality:**

- Still useful indicator of variability
- Patterns emerge over multiple intervals
- Focus on sustained jitter, not single spikes

### Issue 2: Jitter vs Latency Relationship

**Key Insight:** You can have:

- Low latency + low jitter: Excellent (wired, stable)
- Low latency + high jitter: Unstable but fast (WiFi with interference)
- High latency + low jitter: Slow but consistent (distant, stable path)
- High latency + high jitter: Worst case (distant, unstable)

**Streaming Impact:**

- High latency + low jitter: Adaptive bitrate can compensate
- Low latency + high jitter: Adaptive bitrate struggles (unpredictable)

### Issue 3: WiFi Jitter Signatures

**Patterns observed:**

- 2.4 GHz WiFi: Typically 3-8 ms baseline jitter
- 5 GHz WiFi: Typically 1-4 ms baseline jitter
- Wired: Typically <2 ms baseline jitter

**Use:** Compare device jitter to identify WiFi vs wired devices

## What's Working Well

- ✅ Early warning of connection instability
- ✅ Identifies WiFi interference issues
- ✅ Complements latency/loss monitoring
- ✅ Detects issues before users complain
- ✅ Multiple CDNs provide comparison
- ✅ Effective at identifying unstable devices

## Current Gaps

- ❌ No device-level jitter correlation
- ❌ No WiFi vs wired breakdown
- ❌ No historical baseline
- ❌ No automatic classification (WiFi/wired/problematic)
- ❌ Small sample size (5 pings) limits accuracy

## Potential Improvements

### 1. Add WiFi-Specific Jitter Baseline

**What:** Indicate expected jitter range for WiFi vs wired
**How:** Add threshold annotations:

- 0-2 ms: "Wired connection quality"
- 2-8 ms: "Normal WiFi jitter"
- >8 ms: "Connection instability"

### 2. Correlate with Device Types

**What:** Show which devices experiencing high jitter
**How:** Cross-reference with Panel 1/2 device data and WiFi/wired status

### 3. Add Jitter-to-Latency Ratio

**What:** Show jitter as percentage of mean latency
**How:** Calculate: (std_dev / mean_latency) × 100%
**Interpretation:**

- <10%: Stable
- 10-20%: Moderate variability
- >20%: High variability

## Related Panels

- **Panel 3:** CDN Latency - Jitter is variability of this
- **Panel 4:** Packet Loss - High jitter often accompanies loss
- **Panel 2:** Streaming Bandwidth Timeline - Jitter causes bandwidth oscillation
- **Panel 10:** Bandwidth Drops - High jitter often precedes drops

## Investigation Workflow

### Workflow 1: Connection Instability Diagnosis

**When investigating streaming quality issues:**

1. **Check jitter levels:**
   - <5 ms: Connection is stable, look elsewhere
   - 5-10 ms: Moderate instability, contributing factor
   - >10 ms: Primary cause of quality issues
2. **Check all CDNs:**
   - All high: Local network issue (likely WiFi)
   - Single CDN: Routing to that CDN unstable
3. **Correlate with Panel 3 (Latency):**
   - High jitter + varying latency: Confirms instability
   - High jitter + stable latency: Unusual, investigate
4. **Correlate with Panel 4 (Loss):**
   - High jitter + packet loss: Severe network issue
   - High jitter + no loss: Latency variability only
5. **Check Panel 2 bandwidth patterns:**
   - Oscillating bandwidth? High jitter causing TCP instability

### Workflow 2: WiFi vs Wired Identification

**Using jitter to identify connection types:**

1. **<2 ms sustained:** Likely wired connection
2. **2-5 ms sustained:** Likely strong 5 GHz WiFi or wired
3. **5-10 ms sustained:** Typical 2.4 GHz WiFi or weak 5 GHz
4. **>10 ms sustained:** Poor WiFi or network instability

**Validation:**

- Cross-check with known device types
- Wired devices (desktop, TV) should show <2 ms
- Wireless devices (phone, tablet) expect 3-8 ms

### Workflow 3: Intermittent Issue Pattern Recognition

**When jitter oscillates between low and high:**

1. **Regular oscillation:**
   - Check interval (every 5 min, 15 min, hour)
   - May indicate scheduled interference source
   - Common: Microwave use (meal times), neighbor activity
2. **Random oscillation:**
   - Environmental interference (random)
   - Device movement (mobile devices)
   - WiFi channel congestion (dynamic)
3. **Correlate with time of day:**
   - Evening spikes: Neighbor WiFi activity increasing
   - Daytime spikes: Microwave oven, Bluetooth devices

## Common Scenarios & Responses

### Scenario 1: High Jitter on WiFi Devices Only

**Pattern:** Wireless devices show 10-20 ms jitter, wired devices <2 ms

**Analysis:** WiFi interference or congestion

**Investigation:**

1. Check 2.4 vs 5 GHz band usage
2. Scan for channel congestion (neighbor WiFi)
3. Check for interference sources (microwave, Bluetooth)
4. Check distance from AP and signal strength

**Actions:**

- Change WiFi channel to less congested
- Switch devices to 5 GHz band
- Reduce 2.4 GHz interference sources
- Add WiFi AP or move closer

### Scenario 2: All Devices High Jitter (WiFi and Wired)

**Pattern:** Even wired devices showing 8-15 ms jitter

**Analysis:** Not WiFi-specific, ISP or router issue

**Investigation:**

1. Check Panel 4 (Loss): Is loss also present?
2. Check Panel 3 (Latency): Is latency also varying widely?
3. Check ISP modem logs for errors
4. Check router CPU usage

**Root Causes:**

- ISP routing instability (BGP flapping)
- ISP uplink congestion with variable queueing
- Router overload (CPU, memory)
- Physical connection issue (cable, modem)

**Actions:**

- Document pattern with timestamps
- Contact ISP with evidence
- Check router resources, consider upgrade
- Verify all physical connections

### Scenario 3: Jitter Spikes Correlated with Bandwidth Usage

**Pattern:** Jitter increases when Panel 2 shows high total bandwidth

**Analysis:** Network saturation causing variable queueing delays

**Investigation:**

1. Calculate total bandwidth at jitter spike times
2. Compare to link capacity
3. Identify which devices causing saturation (Panel 11)

**Solution:**

- Implement QoS to manage queueing
- Upgrade bandwidth if chronically saturated
- Limit non-critical traffic during peak usage
- Schedule large downloads for off-peak

### Scenario 4: Gradually Increasing Jitter

**Pattern:** Jitter starts low (2 ms), gradually rises to 15+ ms over hours

**Analysis:** Progressive network degradation

**Investigation:**

1. Check time of day pattern (peak hours?)
2. Check Panel 3: Is latency also rising?
3. Check for temperature issues (hardware overheating)
4. Check interference patterns (neighbors coming home)

**Root Causes:**

- Peak hour congestion building
- Hardware thermal issues
- Increasing WiFi interference as day progresses
- ISP capacity degradation during peak

**Actions:**

- If peak hour pattern: Expected, may need QoS or upgrade
- If thermal: Improve cooling/ventilation
- If WiFi: Change channel or band
- If ISP: Document and report

### Scenario 5: Cloudflare Different from Streaming CDNs

**Pattern:** Cloudflare 2 ms jitter, Netflix/YouTube/Amazon 12 ms jitter

**Analysis:** Streaming CDN routing instability

**Investigation:**

1. Verify sustained pattern (not transient)
2. Check if latency also shows disparity (Panel 3)
3. Research ISP peering arrangements

**Root Causes:**

- ISP poor peering with streaming CDNs
- Streaming CDN routing through congested paths
- ISP traffic shaping affecting streaming

**Actions:**

- Document pattern
- Contact ISP
- Consider VPN (may improve routing)

## Files Referenced

- **Dashboard JSON:** `/Users/kirkl/src/network-monitoring/grafana-dashboards/streaming-monitor.json` (Panel ID 11)
- **Telegraf Config:** `/Users/kirkl/src/network-monitoring/telegraf.conf` (inputs.ping, lines 12-24)

## Streaming Quality Metrics

### Jitter Requirements by Resolution

| Resolution | Excellent | Acceptable | Poor | Unusable |
|------------|-----------|------------|------|----------|
| 480p | <10ms | 10-15ms | 15-20ms | >20ms |
| 720p | <8ms | 8-12ms | 12-15ms | >15ms |
| 1080p | <5ms | 5-10ms | 10-12ms | >12ms |
| 4K | <3ms | 3-5ms | 5-8ms | >8ms |
| 8K | <2ms | 2-3ms | 3-5ms | >5ms |

### Connection Type Jitter Signatures

| Connection | Expected Jitter | If Higher → Issue |
|------------|-----------------|-------------------|
| Wired (Ethernet) | <2 ms | Router/ISP issue |
| WiFi 5 GHz (strong) | 2-4 ms | Interference/distance |
| WiFi 5 GHz (weak) | 4-8 ms | Move closer to AP |
| WiFi 2.4 GHz (strong) | 3-8 ms | Expected range |
| WiFi 2.4 GHz (weak) | 8-15 ms | Poor signal/interference |
| Cellular/Mobile | 10-30 ms | Normal for mobile |

## Buffering Detection Patterns

### Pattern 1: High Jitter with Oscillating Bandwidth

**Signature:** This panel shows 10-20 ms jitter, Panel 2 shows bandwidth cycling

**Mechanism:**

- High jitter → TCP confused about RTT
- TCP congestion control overreacting
- Throughput oscillates as TCP adjusts
- User sees quality cycling and micro-buffering

**Buffering Certainty:** High

### Pattern 2: Sudden Jitter Spike Preceding Bandwidth Drop

**Signature:** Jitter spikes from 3 ms to 15 ms, Panel 2 drops 10-30s later

**Interpretation:**

- Connection becoming unstable
- Early warning before throughput affected
- Predictive indicator of upcoming buffering

### Pattern 3: Sustained High Jitter

**Signature:** Jitter consistently >10 ms for extended period

**Quality Impact:**

- Adaptive bitrate algorithms struggle
- Frequent quality adjustments
- Unpredictable buffering
- Poor user experience

## CDN Performance Analysis

### Using Jitter for CDN Diagnosis

**All CDNs high jitter:**

- Local network issue (WiFi, router)
- ISP uplink instability
- Not CDN-specific

**Single CDN high jitter:**

- Routing to that CDN unstable
- CDN node issues
- ISP peering problems

**Jitter + Latency + Loss Combined Analysis:**

| Latency | Loss | Jitter | Diagnosis |
|---------|------|--------|-----------|
| Normal | Normal | High | Connection instability |
| High | Normal | High | Congestion, variable queueing |
| Normal | High | High | Severe network degradation |
| High | High | High | Critical network failure |

**Use combined metrics for complete QoS picture**
