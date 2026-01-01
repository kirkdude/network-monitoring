# Streaming Panel 4: Packet Loss to CDNs

## Panel Overview

- **Panel ID:** 10
- **Title:** Packet Loss to CDNs
- **Type:** Timeseries (Line graph with multiple series)
- **Grid Position:** x=8, y=8, width=8, height=8
- **Purpose:** Monitors packet loss percentage to major CDN endpoints, detecting network quality issues that cause streaming stuttering, freezing, and rebuffering even when bandwidth appears adequate

## Data Source

### Current: InfluxDB Flux Query

```flux
from(bucket: "network")
  |> range(start: v.timeRangeStart, stop: v.timeRangeStop)
  |> filter(fn: (r) => r._measurement == "ping")
  |> filter(fn: (r) => r._field == "percent_packet_loss")
  |> aggregateWindow(every: 30s, fn: mean, createEmpty: false)
  |> group(columns: ["url"])
```

**Query Breakdown:**

1. **Measurement:** `ping` from Telegraf ping plugin (same as Panel 3)
2. **Field:** `percent_packet_loss` - percentage of packets lost in each ping batch
3. **Aggregation:** 30-second windows with mean
4. **Grouping:** By URL for separate line per CDN

### Metrics Used

- **InfluxDB:** `ping` measurement from Telegraf
  - Tags: `url` (target hostname)
  - Field: `percent_packet_loss` (calculated as lost_packets / total_packets × 100)
  - Calculation: Based on 5 pings per interval (0%, 20%, 40%, 60%, 80%, 100% possible values)
  - Type: Time-series polling every 30 seconds

### Data Collection Flow

1. **Telegraf:** `inputs.ping` plugin sends 5 ICMP pings every 30 seconds
2. **Target URLs:** Same as Panel 3 (netflix.com, youtube.com, amazon.com, cloudflare.com)
3. **Loss Calculation:** Telegraf calculates percentage automatically
4. **InfluxDB:** Stores in "network" bucket
5. **Grafana:** Displays as percentage timeline

## Current Configuration

### Thresholds & Colors

- **Green:** 0-0.09% (Excellent - effectively zero loss)
- **Red:** 0.1%+ (Quality degradation begins)

**Context:**

- 0%: Perfect - target state for streaming
- 0.1-0.5%: Minor degradation - occasional glitches
- 0.5-1%: Noticeable issues - frequent micro-stutters
- 1-2%: Significant issues - visible freezing
- >2%: Severe issues - unusable streaming

### Display Settings

- **Unit:** percent (0-100%)
- **Min/Max:** 0% to 100% (forces y-axis scale)
- **Visualization Type:** Timeseries line graph
- **Draw Style:** Line with smooth interpolation
- **Fill Opacity:** 20% (more visible than Panel 3 due to criticality)
- **Display Name:** `${__field.labels.url}` - CDN hostname
- **Legend:** Table with Mean and Max values (Last omitted - instant values misleading for loss)

### Time Range

- Uses: dashboard time range variables
- Default: Last 1 hour
- Auto-refresh: Every 5 seconds
- **Recommended:** 1-6 hours to identify patterns

## Critical Lessons Learned - Packet Loss Monitoring

### Issue 1: Discrete Value Nature (20% increments)

**Challenge:** With 5 pings, only 6 possible values (0%, 20%, 40%, 60%, 80%, 100%)

**Implication:**

- Can't detect <20% loss in single measurement
- Need aggregation over time to see subtle patterns
- 30-second aggregation smooths these discrete jumps

**Why 5 pings:**

- Balance between accuracy and overhead
- 5 pings sufficient to detect most issues
- More pings would increase load and frequency

### Issue 2: Transient vs Sustained Loss

**Pattern Recognition:**

- **Single spike to 20%:** Often false positive, 1 lost packet
- **Sustained >0%:** Real issue requiring investigation
- **Oscillating 0%/20%:** Intermittent problem

**Solution:** Look at Mean value in legend

- Mean <1%: Acceptable, occasional loss
- Mean 1-2%: Concerning, intermittent issues
- Mean >2%: Critical, sustained problem

### Issue 3: Loss vs Latency Interaction

**Observation:** Packet loss and latency often correlated

**Patterns:**

- High loss + high latency: Network congestion (queue overflow)
- High loss + normal latency: Intermittent disruption (WiFi, interference)
- Normal loss + high latency: Bandwidth saturation without packet drops

**Best practice:** Always check both Panel 3 and Panel 4 together

### Issue 4: ICMP Treatment vs TCP

**Limitation:** ICMP may be deprioritized by routers

**Reality:**

- ICMP loss often mirrors TCP loss
- In rare cases, ICMP filtered but TCP fine
- If ICMP shows loss but streaming works fine, verify with HTTP probe

**Mitigation:** Use as indicator, confirm with user experience

## What's Working Well

- ✅ Immediate visibility into network quality issues
- ✅ Catches intermittent problems that affect streaming
- ✅ Multiple CDNs provide baseline comparison
- ✅ 30-second aggregation smooths discrete 20% jumps
- ✅ Mean/Max legend shows both typical and worst-case
- ✅ Highly sensitive - any red indicates problem
- ✅ Complements latency monitoring (Panel 3)
- ✅ Works across all CDNs identically

## Current Gaps

- ❌ Only 5 pings limits granularity (20% increments)
- ❌ No differentiation between upstream/downstream loss
- ❌ No correlation with specific network hops (traceroute)
- ❌ ICMP may not reflect TCP loss exactly
- ❌ No automatic alerting on sustained loss
- ❌ No loss pattern classification
- ❌ No historical baseline for "normal" loss rate
- ❌ Can't distinguish between WiFi vs wired loss

## Potential Improvements

### 1. Increase Ping Count for Finer Granularity

**What:** Increase from 5 to 10 or 20 pings per interval
**How:** Modify telegraf.conf:

```toml
[[inputs.ping]]
  count = 10  # Was 5
```

**Impact:**

- 10 pings: 10% granularity instead of 20%
- 20 pings: 5% granularity
- Tradeoff: Higher overhead, more ICMP traffic

**Recommendation:** 10 pings as good compromise

### 2. Add TCP Connection Loss Monitoring

**What:** Monitor TCP connection success rate, not just ICMP
**How:** Use Telegraf `inputs.net_response` plugin:

```toml
[[inputs.net_response]]
  protocol = "tcp"
  address = "www.netflix.com:443"
```

**Impact:** More accurate representation of streaming connection loss

### 3. Add Loss Pattern Classification

**What:** Automatically classify loss patterns (intermittent, sustained, increasing)
**How:** Add alert rules or annotations:

```flux
|> map(fn: (r) => ({
    r with
    pattern: if r._value == 0 then "none"
      else if r._value < 1.0 then "minor"
      else if r._value < 5.0 then "moderate"
      else "severe"
}))
```

**Impact:** Quick pattern recognition without manual analysis

### 4. Add Direction-Specific Loss Monitoring

**What:** Separate upstream (upload) vs downstream (download) loss
**How:** Use bidirectional ping tools or monitor asymmetric paths

**Impact:** Diagnose if loss is upload path (less impact on streaming) vs download path (direct impact)

### 5. Add Historical Baseline Overlay

**What:** Show 7-day average loss rate as reference line
**How:** Query historical data:

```flux
baseline = from(bucket: "network")
  |> range(start: -7d)
  |> filter(fn: (r) => r._measurement == "ping" and r._field == "percent_packet_loss")
  |> aggregateWindow(every: 1h, fn: mean)
  |> mean()
```

**Impact:** Understand if current loss is abnormal

## Related Panels

- **Panel 3:** CDN Latency - Combined loss + latency = complete QoS picture
- **Panel 5:** Network Jitter - High jitter often accompanies loss
- **Panel 2:** Streaming Bandwidth Timeline - Loss causes bandwidth drops
- **Panel 10:** Bandwidth Drops - Loss directly causes bandwidth reduction
- **Panel 1:** Active Streaming Sessions - Shows quality impact of loss
- **Panel 8:** Streaming Service Detection - Map affected services to CDNs

## Investigation Workflow

### Workflow 1: Streaming Quality Degradation - Is Loss the Cause?

**When user reports stuttering, freezing, or poor quality:**

1. **Check this panel for loss at time of issue:**
   - 0%: Loss is NOT the cause
   - 0.1-0.5%: Minor contributor
   - 0.5-1%: Significant contributor
   - >1%: Primary cause
2. **Check loss pattern:**
   - Single spike: Transient glitch, likely resolved
   - Oscillating: Intermittent issue, ongoing problem
   - Sustained: Critical issue requiring immediate action
3. **Check which CDNs affected:**
   - Single CDN: CDN-specific routing or node issue
   - All CDNs: Local network or ISP problem
   - All except Cloudflare: Streaming CDN-specific routing
4. **Correlate with latency (Panel 3):**
   - Loss + high latency: Network congestion (queue drops)
   - Loss + normal latency: Physical disruption (WiFi, cable)
5. **Check bandwidth impact (Panel 2):**
   - Loss + bandwidth drop: TCP backing off due to loss
   - Loss + stable bandwidth: Loss not yet affecting throughput
6. **Determine root cause location:**
   - All wired devices: ISP or upstream issue
   - Wireless only: WiFi interference or AP issue
   - Single device: Device network adapter issue

**Decision Tree:**

- Loss all CDNs + wired + WiFi → ISP uplink
- Loss all CDNs + WiFi only → WiFi interference/congestion
- Loss single CDN + others fine → CDN routing issue
- Loss intermittent all → Check Panel 5 (jitter)

### Workflow 2: WiFi vs Wired Diagnosis

**When isolating WiFi as loss source:**

1. **Check if only wireless devices streaming have loss impact**
2. **If WiFi suspected:**
   - Check Panel 5 (Jitter): High jitter confirms WiFi instability
   - Check 2.4 GHz vs 5 GHz: 2.4 GHz more prone to interference
   - Check AP location: Distance and obstacles matter
3. **Common WiFi loss causes:**
   - Microwave oven operation (2.4 GHz interference)
   - Bluetooth devices (2.4 GHz band sharing)
   - Neighbor WiFi on same channel
   - Too many clients on single AP
4. **Mitigation steps:**
   - Change WiFi channel (scan for least congested)
   - Switch to 5 GHz band (if supported)
   - Move closer to AP or add WiFi extender
   - Reduce client count per AP
   - Consider wired connection for primary streaming devices

### Workflow 3: Concurrent Loss and Latency Spike

**When both panels show issues simultaneously:**

1. **This indicates network congestion:**
   - Buffers full → packet drops (loss)
   - Queue delays → increased latency
2. **Check total network bandwidth (Panel 2):**
   - Sum all device bandwidth
   - Compare to link capacity
   - If >80%: Saturation confirmed
3. **Identify bandwidth hogs:**
   - Panel 11: Which devices consuming most?
   - Panel 2: Any device with sustained very high bandwidth?
4. **Assess QoS requirements:**
   - Critical: Video calls (need <1% loss, <100ms latency)
   - Important: 4K streaming (need <0.5% loss, <50ms latency)
   - Lower priority: Downloads, software updates
5. **Implement mitigation:**
   - Enable QoS on router: Prioritize real-time traffic
   - Limit non-critical bandwidth: Rate limit background tasks
   - Schedule heavy downloads: Off-peak hours
   - Upgrade bandwidth: If chronically saturated

## Common Scenarios & Responses

### Scenario 1: Zero Loss Most of Time, Occasional 20% Spikes

**Pattern:** Mostly flat at 0%, brief spikes to 20% lasting 1-2 data points

**Analysis:**

- With 5 pings, 20% = 1 lost packet
- Occasional single packet loss is often acceptable
- Mean <0.5% indicates healthy connection

**Investigation:**

1. **Check spike frequency:**
   - <5 per hour: Acceptable, noise level
   - 5-20 per hour: Monitor, may become issue
   - >20 per hour: Investigate pattern
2. **Check if correlated with activity:**
   - Panel 2 bandwidth spikes? Momentary congestion
   - Random timing? Environmental interference
3. **Check legend Mean value:**
   - <0.5%: Acceptable
   - >0.5%: Becoming problematic

**User Impact:**

- Minimal - occasional single lost packet causes brief glitch
- Adaptive bitrate and buffering typically absorb this
- User unlikely to notice

**Actions:**

- Mean <0.5%: No action needed, normal variability
- Mean >0.5%: Investigate pattern (see Workflow 1)
- If WiFi device: Consider interference mitigation

### Scenario 2: Sustained 20% Loss (Flat Line)

**Pattern:** Consistently showing 20% loss (1 out of 5 pings) for extended period (>5 minutes)

**Analysis:**

- This is NOT normal
- Indicates persistent network issue
- User definitely experiencing quality degradation

**Investigation:**

1. **Check all CDNs:**
   - All showing 20%? Network issue (local or ISP)
   - Single CDN? That CDN's routing issue
2. **Check Panel 3 latency:**
   - Also elevated? Congestion likely
   - Normal? Physical layer issue (cable, WiFi, hardware)
3. **Check wired vs WiFi:**
   - WiFi only? WiFi saturation or interference
   - Wired too? ISP or router issue
4. **Check time pattern:**
   - Peak hours only? Congestion pattern
   - Random? Hardware or connection issue

**User Impact:**

- Frequent micro-stutters
- Reduced quality due to lost frames
- Adaptive bitrate lowering quality
- Frustrating experience

**Actions:**

- **If WiFi:** Follow WiFi mitigation (change channel, reduce clients)
- **If congestion:** Enable QoS or upgrade bandwidth
- **If hardware:** Check cables, router, network adapters
- **If ISP:** Document and contact ISP with evidence

### Scenario 3: Oscillating Loss (0%, 20%, 40% cycling)

**Pattern:** Loss percentage cycling through values every few minutes

**Analysis:**

- Intermittent disruption
- Could be interference, congestion cycling, or physical connection issue
- Unpredictable for adaptive bitrate algorithms

**Investigation:**

1. **Identify cycle period:**
   - 1-5 minutes: Interference or device behavior
   - 10-30 minutes: Possible scheduled process
   - Irregular: Random environmental interference
2. **Check Panel 5 (Jitter):**
   - High jitter confirms connection instability
3. **Check for patterns:**
   - Time-of-day correlation? Neighbor activity, microwave use
   - Device-correlated? Specific device causing interference
4. **Check Panel 3 latency:**
   - Also cycling? Network path instability
   - Stable? Physical layer issue only

**Root Causes:**

- **WiFi interference:** Microwave, Bluetooth, cordless phones
- **WiFi roaming:** Device switching between APs or bands
- **Scheduled processes:** Background tasks running periodically
- **Physical connection:** Loose cable, failing hardware
- **ISP routing:** Path instability (BGP flapping)

**User Impact:**

- Unpredictable quality
- Frequent buffering events
- Quality constantly adjusting
- Very frustrating experience

**Actions:**

- **WiFi interference:** Scan for sources, change channels
- **Roaming:** Configure sticky AP or band steering
- **Scheduled process:** Identify and reschedule
- **Physical:** Check all cables, replace if needed
- **ISP:** Document pattern, report to ISP

### Scenario 4: All CDNs Show Loss Except Cloudflare

**Pattern:** Netflix, YouTube, Amazon showing 1-5% loss, Cloudflare showing 0%

**Analysis:**

- Unlikely pattern - usually all or none
- Possible ISP traffic shaping targeting streaming CDNs
- Or routing issue specific to streaming CDN paths

**Investigation:**

1. **Verify pattern is sustained (not transient)**
2. **Check Panel 3 latency pattern:**
   - Streaming CDNs also high latency? Confirms routing disparity
   - Latency similar? Isolated loss without latency
3. **Research ISP behavior:**
   - Check ISP forums for similar reports
   - Some ISPs known to deprioritize streaming
4. **Test with VPN:**
   - If loss disappears with VPN: ISP traffic shaping confirmed
   - If loss persists: Routing issue, not throttling

**Root Causes:**

- **ISP traffic shaping:** Deliberately degrading streaming traffic
- **Routing issues:** Suboptimal paths to streaming CDN peering
- **QoS misconfiguration:** ISP QoS policy affecting streaming
- **Peering problems:** Poor ISP-to-CDN interconnection

**User Impact:**

- Degraded streaming quality
- Other internet use (Cloudflare baseline) unaffected
- Specifically targeting entertainment

**Actions:**

- **Document evidence:** Capture screenshots, times, values
- **Contact ISP:** Report with evidence, request explanation
- **Escalate if needed:** File FCC complaint (US) or regulatory body
- **Consider VPN:** May provide better routing (test first)
- **Switch ISP:** If chronic and unresolved

### Scenario 5: Sudden Spike to 100% Loss, Brief Recovery

**Pattern:** Normal 0%, suddenly 100% for 1-3 data points, back to 0%

**Analysis:**

- Complete connection interruption
- Very brief (30-90 seconds)
- Possible causes varied

**Investigation:**

1. **Check frequency:**
   - One-time: Transient glitch, likely acceptable
   - Multiple per hour: Serious instability
2. **Check if all CDNs simultaneously:**
   - All CDNs: Local network or ISP issue
   - Single CDN: That CDN temporarily unreachable
3. **Check logs:**
   - Router logs: Disconnection events?
   - ISP modem: Uplink reconnection?
4. **Check Panel 3 during recovery:**
   - High latency after recovery? Route convergence
   - Normal immediately? Brief disruption only

**Root Causes:**

- **Router restart/reboot:** Manual or automatic
- **ISP DHCP renewal:** Brief disconnection during renewal
- **Physical disconnection:** Cable loosened momentarily
- **ISP maintenance:** Brief maintenance window
- **Modem sync loss:** DSL/Cable modem resync

**User Impact:**

- Brief buffering or pause
- Stream may restart or reduce quality
- If infrequent: Acceptable
- If frequent: Unacceptable

**Actions:**

- **One-time:** Monitor, likely no action needed
- **Recurring:** Investigate router, modem, ISP connection
- **Check physical:** All cables secure
- **Router logs:** Look for disconnection events
- **ISP:** Contact if recurring without explanation

### Scenario 6: Gradual Increase in Loss Over Hours

**Pattern:** Starts at 0%, gradually increases to 2-5% over 2-4 hours

**Analysis:**

- Progressive network degradation
- Could be congestion building, hardware heating, interference increasing
- Indicates capacity or environmental issue

**Investigation:**

1. **Check time correlation:**
   - Evening hours (6-11 PM)? Peak congestion pattern
   - Consistent time daily? Environmental pattern (neighbor activity)
   - Random? Hardware thermal issue
2. **Check Panel 2 bandwidth growth:**
   - More devices streaming? Congestion from usage growth
   - Stable device count? External congestion or interference
3. **Check temperature:**
   - Router/modem hot? Thermal throttling possible
   - Environment hot? Overheating affecting hardware
4. **Check Panel 3 latency:**
   - Also increasing? Confirms congestion pattern
   - Stable? Isolated loss without latency change

**Root Causes:**

- **Peak hour congestion:** Normal for 6-11 PM if progressive
- **Hardware overheating:** Degraded performance as temperature rises
- **Increasing interference:** Neighbors coming home, more WiFi activity
- **ISP congestion:** Uplink becoming saturated during peak

**Actions:**

- **Peak hour pattern:** May need bandwidth upgrade or QoS
- **Hardware thermal:** Improve ventilation, cooling
- **Interference:** Change WiFi channel or switch to 5 GHz
- **ISP chronic:** Document and report to ISP

## Files Referenced

- **Dashboard JSON:** `/Users/kirkl/src/network-monitoring/grafana-dashboards/streaming-monitor.json` (Panel ID 10)
- **Provisioned Dashboard:** `/Users/kirkl/src/network-monitoring/grafana-provisioning/dashboards/streaming-monitor.json` (Panel ID 10)
- **Telegraf Config:** `/Users/kirkl/src/network-monitoring/telegraf.conf` (inputs.ping plugin, lines 12-24)
- **InfluxDB Bucket:** "network" bucket stores ping metrics

## Streaming Quality Metrics

### Packet Loss Requirements by Resolution

| Resolution | Excellent | Acceptable | Poor | Unusable |
|------------|-----------|------------|------|----------|
| 480p (SD) | <0.5% | 0.5-1% | 1-2% | >2% |
| 720p (HD) | <0.3% | 0.3-0.8% | 0.8-1.5% | >1.5% |
| 1080p (FHD) | <0.2% | 0.2-0.5% | 0.5-1% | >1% |
| 4K (UHD) | <0.1% | 0.1-0.3% | 0.3-0.5% | >0.5% |
| 8K | <0.05% | 0.05-0.1% | 0.1-0.2% | >0.2% |

### Combined Latency + Loss Quality Matrix

| Latency | Loss < 0.5% | Loss 0.5-1% | Loss > 1% |
|---------|-------------|-------------|-----------|
| <50ms | Excellent | Good | Poor |
| 50-100ms | Good | Acceptable | Poor |
| >100ms | Acceptable | Poor | Unusable |

**Key Insight:** Loss is MORE critical than latency

- 0% loss + 150ms latency = Usable (slow start, then fine)
- 2% loss + 30ms latency = Unusable (constant stuttering)

### Loss Impact on Streaming Protocols

**TCP-based streaming (most services):**

- Loss triggers TCP retransmission
- Reduces effective throughput
- Causes buffering as throughput drops below bitrate
- Adaptive bitrate compensates by reducing quality

**UDP-based streaming (some live streams, video conferencing):**

- Lost packets = lost frames (no retransmission)
- Direct visual impact (freezing, artifacts)
- More sensitive to loss than TCP streaming
- Requires <0.1% loss for acceptable quality

## Buffering Detection Patterns

### Pattern 1: Loss Spike Correlating with Bandwidth Drop

**Signature:** This panel shows loss spike, Panel 2 shows bandwidth drop 10-30s later

**Mechanism:**

1. Packet loss occurs
2. TCP detects loss via missing ACKs
3. TCP enters congestion avoidance, reduces sending rate
4. Reduced rate manifests as bandwidth drop
5. User experiences buffering as bandwidth falls below bitrate

**Buffering Certainty:** Very High

**Mitigation:**

- Reduce loss (root cause)
- Enable forward error correction if available
- Increase buffer size (tradeoff: higher latency)

### Pattern 2: Sustained Low-Level Loss (0.5-1%)

**Signature:** Consistent loss below critical threshold but above zero

**Quality Impact:**

- Frequent TCP retransmissions
- Slightly reduced effective bandwidth
- Occasional micro-buffering
- Adaptive bitrate may reduce quality slightly

**User Experience:**

- May not consciously notice loss
- Subtle quality reduction
- Occasional brief pauses or glitches

**Action Threshold:**

- <0.5% sustained: Acceptable, monitor
- 0.5-1% sustained: Should investigate
- >1% sustained: Must fix

### Pattern 3: Intermittent Loss Bursts

**Signature:** Periods of 0% alternating with periods of 5-20% loss

**Buffering Manifestation:**

- Unpredictable buffering events
- User frustrated by randomness
- Adaptive bitrate struggling to find stable quality

**Root Causes:**

- WiFi interference (microwaves, Bluetooth)
- Physical connection instability (loose cable)
- ISP routing flapping
- Competing traffic bursts

**Investigation Priority: High** - Intermittent issues hardest to diagnose

### Pattern 4: Loss Without Latency Increase

**Signature:** This panel shows loss, Panel 3 latency remains normal

**Interpretation:**

- Not congestion-related (would show both)
- Likely physical layer issue
- WiFi interference, cable problem, or hardware

**Diagnostic Approach:**

1. Check physical connections
2. Check WiFi signal strength and interference
3. Check hardware (router, modem, NICs)
4. Check for environmental interference

**Not:** Bandwidth saturation or ISP congestion

## CDN Performance Analysis

### Using Loss for CDN Quality Assessment

**This panel uses same CDN endpoints as Panel 3:**

- <www.netflix.com> (Akamai/Netflix OCA)
- <www.youtube.com> (Google Global Cache)
- <www.amazon.com> (CloudFront)
- <www.cloudflare.com> (Baseline)

**Loss as CDN Health Indicator:**

**All CDNs show loss:**

- Network path issue (ISP, local network)
- Not CDN-specific
- Check local network first, then ISP

**Single CDN shows loss:**

- Routing to that CDN problematic
- CDN node issues
- ISP peering to that CDN poor
- May need ISP to adjust routing

**Cloudflare different from streaming CDNs:**

- If Cloudflare clean, streaming CDNs lossy → ISP traffic shaping possible
- If Cloudflare lossy, streaming CDNs clean → Unlikely but investigate

### Loss vs Latency CDN Diagnosis Matrix

| Panel 3 (Latency) | Panel 4 (Loss) | Diagnosis |
|-------------------|----------------|-----------|
| Normal | Normal | Healthy connection |
| High | Normal | Congestion/distance, no drops |
| Normal | High | Physical issue, WiFi, hardware |
| High | High | Severe congestion, queue drops |

**Use this matrix for rapid CDN health assessment**
