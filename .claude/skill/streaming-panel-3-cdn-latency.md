# Streaming Panel 3: CDN Latency (ICMP Ping)

## Panel Overview

- **Panel ID:** 9
- **Title:** CDN Latency (ICMP Ping)
- **Type:** Timeseries (Line graph with multiple series)
- **Grid Position:** x=0, y=8, width=8, height=8
- **Purpose:** Monitors ICMP ping response times to major CDN endpoints used by streaming services, providing early warning of CDN performance degradation that can cause buffering

## Data Source

### Current: InfluxDB Flux Query

```flux
from(bucket: "network")
  |> range(start: v.timeRangeStart, stop: v.timeRangeStop)
  |> filter(fn: (r) => r._measurement == "ping")
  |> filter(fn: (r) => r._field == "average_response_ms")
  |> aggregateWindow(every: 30s, fn: mean, createEmpty: false)
  |> group(columns: ["url"])
```

**Query Breakdown:**

1. **Measurement:** `ping` from Telegraf ping plugin
2. **Field:** `average_response_ms` - average of 5 pings per check
3. **Aggregation:** 30-second windows with mean (smooth out single-ping anomalies)
4. **Grouping:** By URL to show separate line per CDN

### Metrics Used

- **InfluxDB:** `ping` measurement from Telegraf
  - Tags: `url` (target hostname)
  - Fields: `average_response_ms`, `minimum_response_ms`, `maximum_response_ms`, `percent_packet_loss`, `standard_deviation_ms`
  - Type: Time-series polling (every 30 seconds)

### Data Collection Flow

1. **Telegraf:** `inputs.ping` plugin configured to ping 4 CDN endpoints
2. **Target URLs:**
   - <www.netflix.com> (Akamai/Netflix OCA)
   - <www.youtube.com> (Google Global Cache)
   - <www.amazon.com> (CloudFront/Amazon)
   - <www.cloudflare.com> (Cloudflare CDN baseline)
3. **Ping Configuration:**
   - Count: 5 pings per interval
   - Interval: 30 seconds
   - Timeout: 5 seconds
   - Method: Native ICMP (requires root/capabilities)
4. **InfluxDB:** Stores metrics in "network" bucket
5. **Grafana:** Displays as timeseries

## Current Configuration

### Thresholds & Colors

- **Green:** 0-49 ms (Excellent latency)
- **Yellow:** 50-99 ms (Acceptable latency, quality may degrade)
- **Red:** 100+ ms (Poor latency, buffering likely)

**Context:**

- <20 ms: Optimal for all streaming qualities including 8K
- 20-50 ms: Excellent for 4K streaming
- 50-100 ms: Acceptable for HD, marginal for 4K
- 100-150 ms: SD only, frequent buffering
- >150 ms: Poor experience even at SD

### Display Settings

- **Unit:** ms (milliseconds)
- **Visualization Type:** Timeseries line graph
- **Draw Style:** Line with smooth interpolation
- **Fill Opacity:** 10% (subtle area under curve)
- **Display Name:** `${__field.labels.url}` - Shows CDN hostname
- **Legend:** Table format with Mean, Max, Last values

### Time Range

- Uses: dashboard time range variables
- Default: Last 1 hour
- Auto-refresh: Every 5 seconds
- **Recommended:** 1-6 hours for pattern analysis

## Critical Lessons Learned - CDN Latency Monitoring

### Issue 1: Hostnames vs IP Addresses

**Decision:** Use hostnames (<www.netflix.com>) not IPs

**Reasoning:**

- CDNs use geographic routing - hostname resolves to nearest node
- IP addresses would test only one specific node
- Hostnames reflect actual user experience (DNS-based routing)
- Mirrors what streaming devices actually connect to

### Issue 2: Ping Count vs Frequency Tradeoff

**Current:** 5 pings every 30 seconds

**Alternatives tested:**

- 10 pings every 60s: Too slow to catch transient issues
- 1 ping every 10s: Too sensitive, false alarms from single packet loss
- 5 pings every 30s: ✅ Good balance

**Benefits:**

- Average of 5 reduces single-ping noise
- 30s interval catches most issues without overwhelming
- Provides 2 data points per minute for smooth graphs

### Issue 3: Mean vs Median Aggregation

**Current:** Mean (average)

**Consideration:** Median would be more robust to outliers

**Decision:** Mean is appropriate here because:

- Outliers represent real latency spikes users experience
- Median would hide intermittent problems
- Mean better correlates with user-perceived quality
- Streaming services care about worst-case, not typical-case

### Issue 4: ICMP vs TCP/HTTP Monitoring

**Current:** ICMP ping

**Limitation:** ICMP doesn't test actual streaming protocol

**Why ICMP anyway:**

- Lightweight and fast
- Supported by all CDNs
- Good proxy for network path quality
- Actual streaming latency would require complex application-layer testing

**Future improvement:** Add HTTP probe to actual CDN video endpoints

## What's Working Well

- ✅ Early warning of CDN issues before users complain
- ✅ Clear differentiation between CDN providers
- ✅ 30-second aggregation smooths noise while catching issues
- ✅ Legend shows mean/max/last for quick assessment
- ✅ Multiple CDNs provide comparison baseline
- ✅ Cloudflare serves as control (general internet health)
- ✅ Real-time updates catch transient issues
- ✅ Simple ICMP is reliable and universally supported

## Current Gaps

- ❌ No geographic CDN node identification
- ❌ No correlation with specific streaming services
- ❌ No automatic alerting on threshold breach
- ❌ No historical baseline comparison
- ❌ No CDN failover detection
- ❌ Limited to 4 CDNs (many more exist)
- ❌ ICMP may not reflect actual HTTPS latency
- ❌ No path analysis (traceroute) capability

## Potential Improvements

### 1. Add Service-to-CDN Mapping Labels

**What:** Annotate which services use which CDNs
**How:** Add labels to legend:

```
netflix.com → "Netflix (Akamai)"
youtube.com → "YouTube (Google)"
amazon.com → "Prime Video (CloudFront)"
```

**Impact:** Users immediately understand service implications

### 2. Add Percentile Lines (P95, P99)

**What:** Show 95th and 99th percentile latency alongside mean
**How:** Add additional queries calculating percentiles:

```flux
|> aggregateWindow(every: 5m, fn: (tables=<-, column) =>
    tables |> quantile(q: 0.95, column: column))
```

**Impact:** Understand worst-case latency affecting users

### 3. Add CDN Comparison Baseline

**What:** Show relative performance vs historical baseline
**How:** Query 7-day average, overlay as reference line

**Impact:** Identify if current latency is normal or degraded

### 4. Add Geographic CDN Node Detection

**What:** Identify which CDN node/region being used
**How:** Reverse DNS lookup on resolved IPs, parse location

**Impact:** Diagnose routing changes and CDN load balancing

### 5. Add HTTP/HTTPS Latency Probe

**What:** Test actual HTTPS connection time, not just ICMP
**How:** Use Telegraf `inputs.http_response` plugin:

```toml
[[inputs.http_response]]
  urls = ["https://www.netflix.com", "https://www.youtube.com"]
  response_timeout = "5s"
  method = "HEAD"
```

**Impact:** More accurate representation of streaming connection latency

## Related Panels

- **Panel 1:** Active Streaming Sessions - See which devices affected by high latency
- **Panel 2:** Streaming Bandwidth Timeline - Correlate latency spikes with bandwidth drops
- **Panel 4:** Packet Loss to CDNs - Combined latency + loss = poor QoS
- **Panel 5:** Network Jitter - Combined with jitter identifies connection instability
- **Panel 8:** Streaming Service Detection - Map services to CDNs shown here
- **Panel 9:** CDN Connection Health - See which devices use which CDNs
- **Panel 10:** Bandwidth Drops - Latency spikes often precede bandwidth drops

## Investigation Workflow

### Workflow 1: Buffering Investigation - Is CDN Latency the Cause?

**When user reports buffering:**

1. **Check this panel** for latency at time of buffering
2. **Assess severity:**
   - <50 ms: Latency is NOT the cause, look elsewhere
   - 50-100 ms: Latency is a contributing factor
   - >100 ms: Latency is primary cause
3. **Check CDN pattern:**
   - Single CDN elevated? CDN-specific issue
   - All CDNs elevated? Network or ISP issue
   - Intermittent spikes? Routing instability
4. **Correlate with bandwidth (Panel 2):**
   - Latency spike + bandwidth drop? Quality degraded due to CDN
   - Latency spike + bandwidth stable? CDN slow but adequate
5. **Check packet loss (Panel 4):**
   - Latency high + loss high? Severe network issue
   - Latency high + loss normal? CDN congestion
6. **Identify affected service:**
   - Panel 8: Which service was user streaming?
   - Map to CDN: Netflix→this panel's netflix.com line

**Decision Tree:**

- All CDNs high + user ISP normal → ISP uplink congestion
- Single CDN high + others normal → CDN node overload
- Intermittent spikes all CDNs → WiFi or local network issue
- Sustained high all CDNs → Need to contact ISP

### Workflow 2: Proactive CDN Performance Monitoring

**Daily monitoring routine:**

1. **Set time range to 24 hours**
2. **Check legend mean values:**
   - All <30 ms? Excellent, no action
   - Any 30-50 ms? Acceptable, monitor
   - Any >50 ms? Investigate further
3. **Look for patterns:**
   - Peak hour degradation (6-11 PM)? Expected, acceptable if <100ms
   - Random spikes? Investigate routing
   - Sustained elevation? CDN capacity issue
4. **Compare CDNs:**
   - One much worse than others? CDN-specific problem
   - All similar? Network path issue
   - Cloudflare different? General internet vs CDN-specific
5. **Check historical trend:**
   - Degrading over days/weeks? Capacity planning needed
   - Stable? Good baseline

### Workflow 3: CDN Failover Detection

**When CDN latency suddenly drops after being high:**

1. **Identify the pattern:**
   - High latency (>100ms) then sudden drop to <30ms
   - Indicates CDN load balancing kicked in
2. **Verify failover:**
   - Check Panel 9 (CDN Connection Health) for shift in CDN usage
   - Check Panel 13 (DNS Queries) for change in resolved domains
3. **Assess user impact:**
   - Temporary buffering during high latency period
   - Smooth recovery after failover
4. **Document pattern:**
   - Note time of failover
   - CDN that failed over
   - Duration of elevated latency
   - Helps identify recurring CDN issues

## Common Scenarios & Responses

### Scenario 1: Single CDN Elevated (Netflix/Akamai High, Others Normal)

**Pattern:** netflix.com showing 80-120ms, youtube.com and others <30ms

**Analysis:**

- CDN-specific issue, not general network
- Netflix/Akamai node is overloaded or has routing issue
- Other streaming services unaffected

**Investigation:**

1. **Check Panel 8:** Are many devices streaming Netflix?
2. **Check Panel 2:** Are Netflix devices showing reduced bandwidth?
3. **Check time:** Peak hours (evening)? Expected higher latency
4. **Check duration:** Brief spike or sustained?

**Root Causes:**

- **Peak hour CDN congestion:** Normal during 6-11 PM, acceptable if <100ms
- **CDN node failure:** One node down, traffic redirected
- **ISP routing to CDN:** Suboptimal path to specific CDN
- **Geographic CDN issue:** Regional CDN problem

**User Impact:**

- <100ms: Slight quality reduction, may not notice
- 100-150ms: Buffering during high-bitrate scenes
- >150ms: Frequent buffering, significant degradation

**Actions:**

- **If peak hours + <100ms:** Acceptable, no action
- **If sustained >100ms:** Report to Netflix/ISP
- **If ISP routing:** May need to contact ISP
- **If all devices affected:** CDN issue, wait for resolution (usually auto-fixes)

### Scenario 2: All CDNs Elevated Simultaneously

**Pattern:** All four CDNs showing elevated latency at same time (60-90ms when normally <30ms)

**Analysis:**

- Not CDN-specific, shared network issue
- Affects all streaming services equally
- High priority investigation

**Investigation:**

1. **Check Cloudflare specifically:**
   - If Cloudflare also high: General internet issue
   - If Cloudflare normal: CDN-specific routing issue (unlikely but possible)
2. **Check timing:**
   - Exactly on the hour? Possible ISP maintenance
   - Peak hours? Normal congestion, acceptable
   - Random? Investigate network
3. **Check Panel 4 (Packet Loss):**
   - Loss also elevated? Network quality issue
   - Loss normal? Pure latency/distance issue
4. **Check Panel 5 (Jitter):**
   - Jitter high? Connection instability
   - Jitter normal? Routing path changed

**Root Causes:**

- **ISP uplink congestion:** Peak hour overloading
- **ISP routing change:** New path with more hops
- **Local network congestion:** WiFi interference or bandwidth saturation
- **ISP maintenance:** Brief routing reconfiguration
- **Regional internet issue:** Major backbone congestion

**Actions:**

- **If <100ms and stable:** Acceptable, monitor
- **If >100ms sustained:** Contact ISP
- **If intermittent spikes:** Check WiFi (Panel 5 jitter)
- **If peak hours only:** May need bandwidth upgrade

### Scenario 3: Intermittent Latency Spikes (Sawtooth Pattern)

**Pattern:** Latency cycles between 20ms and 100ms+ every few minutes

**Analysis:**

- Connection instability, not sustained CDN issue
- Affects streaming quality unpredictably
- Adaptive bitrate will struggle

**Investigation:**

1. **Check spike characteristics:**
   - Regular intervals? Scheduled process or interference
   - Random? Network instability
   - Correlated with bandwidth (Panel 2)? Congestion
2. **Check if all CDNs affected:**
   - All CDNs: Local network issue
   - Single CDN: CDN routing flapping
3. **Check Panel 5 (Jitter):**
   - High jitter confirms instability
4. **Check WiFi:**
   - Wireless devices primarily affected? WiFi interference

**Root Causes:**

- **WiFi interference:** Microwave, neighbor networks, channel congestion
- **WiFi channel switching:** Device or AP changing channels
- **ISP routing flapping:** BGP route instability
- **Local network congestion:** Periodic heavy usage
- **VPN or proxy issues:** If using VPN

**User Impact:**

- Unpredictable buffering
- Quality frequently changing
- Frustrating user experience

**Actions:**

- **WiFi interference:** Change WiFi channel, use 5GHz
- **Routing instability:** Contact ISP
- **Local congestion:** Implement QoS
- **VPN:** Disable or change VPN endpoint

### Scenario 4: Gradual Latency Increase Over Hours

**Pattern:** CDN latency starts at 20ms, slowly increases to 80-100ms over 2-4 hours

**Analysis:**

- CDN node gradually becoming overloaded
- Progressive quality degradation
- Indicates capacity issue

**Investigation:**

1. **Check time pattern:**
   - Starts at 6 PM? Evening peak usage pattern (expected)
   - Random time? CDN capacity issue
2. **Check which CDNs affected:**
   - Single CDN: That CDN's capacity issue
   - All CDNs: ISP or network capacity issue
3. **Check Panel 2 bandwidth:**
   - Bandwidth also declining? Users experiencing degradation
   - Bandwidth stable? Users adapted to higher latency
4. **Compare to previous days:**
   - Same pattern daily? Normal peak behavior
   - New pattern? Investigate change

**Root Causes:**

- **Peak hour loading:** Normal for 6-11 PM, acceptable if manages well
- **CDN capacity insufficient:** CDN can't handle load
- **ISP congestion:** Uplink saturating during peak
- **Event-driven spike:** Major content release (new show, sports event)

**Actions:**

- **If predictable and <100ms:** Normal pattern, no action
- **If exceeds 100ms regularly:** Report to CDN/ISP
- **If event-driven:** Temporary, will resolve post-event
- **If sustained pattern:** May need QoS or bandwidth upgrade

### Scenario 5: Cloudflare Different from Streaming CDNs

**Pattern:** Cloudflare 20ms, Netflix/YouTube/Amazon 60-80ms

**Analysis:**

- Streaming CDN-specific routing issue
- Cloudflare baseline shows general internet is fine
- ISP may have suboptimal routing to streaming CDNs

**Investigation:**

1. **Verify pattern consistency:**
   - Sustained difference? Routing issue
   - Temporary? May resolve
2. **Check if known ISP issue:**
   - Research ISP forums for similar reports
   - Some ISPs have poor peering with specific CDNs
3. **Check Panel 9:**
   - Are devices hitting expected CDNs?
   - Unexpected CDN nodes might indicate routing issues

**Root Causes:**

- **ISP peering:** Poor peering agreements with streaming CDNs
- **ISP traffic shaping:** Deprioritizing streaming traffic
- **Geographic routing:** Streaming CDNs routing to distant nodes
- **CDN selection:** DNS resolving to suboptimal CDN nodes

**Actions:**

- **Document pattern:** Record times and latencies
- **Contact ISP:** Provide evidence of routing disparity
- **Consider VPN:** May get better routing (test first)
- **Report to streaming service:** They may adjust CDN selection

### Scenario 6: Sudden Latency Drop After High Period

**Pattern:** Latency at 100-150ms for 30+ minutes, suddenly drops to 25ms

**Analysis:**

- CDN load balancing succeeded
- Users were experiencing degraded service, now recovered
- May indicate CDN failover or traffic redistribution

**Investigation:**

1. **Note the recovery time:** How long was degradation?
2. **Check Panel 9:** Did CDN node change?
3. **Check Panel 13:** DNS resolution changes?
4. **Check user impact:** Panel 2 bandwidth recovered?

**User Impact:**

- During high latency: Buffering and quality reduction
- After recovery: Normal quality restored
- May have noticed interruption then recovery

**Actions:**

- **Document incident:** Time, duration, affected CDN
- **Monitor for recurrence:** Same CDN pattern = chronic issue
- **If recurring:** Report to CDN provider
- **If one-time:** Normal CDN operations, no action needed

## Files Referenced

- **Dashboard JSON:** `/Users/kirkl/src/network-monitoring/grafana-dashboards/streaming-monitor.json` (Panel ID 9)
- **Provisioned Dashboard:** `/Users/kirkl/src/network-monitoring/grafana-provisioning/dashboards/streaming-monitor.json` (Panel ID 9)
- **Telegraf Config:** `/Users/kirkl/src/network-monitoring/telegraf.conf` (inputs.ping plugin, lines 12-24)
- **InfluxDB Bucket:** "network" bucket stores ping metrics

## Streaming Quality Metrics

### Latency Requirements by Resolution

| Resolution | Excellent | Acceptable | Poor | Buffering Likely |
|------------|-----------|------------|------|------------------|
| 480p (SD) | <100ms | 100-150ms | 150-200ms | >200ms |
| 720p (HD) | <80ms | 80-120ms | 120-150ms | >150ms |
| 1080p (FHD) | <50ms | 50-100ms | 100-120ms | >120ms |
| 4K (UHD) | <30ms | 30-50ms | 50-80ms | >80ms |
| 8K | <20ms | 20-30ms | 30-50ms | >50ms |

### CDN-Specific Performance Baselines

Based on empirical observations:

**Netflix (Akamai/OCA):**

- Excellent: <20ms
- Good: 20-50ms
- Acceptable: 50-80ms
- Poor: >80ms
- **Notes:** Netflix has extensive CDN infrastructure, typically excellent latency

**YouTube (Google Global Cache):**

- Excellent: <25ms
- Good: 25-60ms
- Acceptable: 60-90ms
- Poor: >90ms
- **Notes:** Google's network very robust, rarely sees high latency

**Prime Video (CloudFront):**

- Excellent: <30ms
- Good: 30-70ms
- Acceptable: 70-100ms
- Poor: >100ms
- **Notes:** Amazon CloudFront generally reliable

**Cloudflare (Baseline):**

- Excellent: <15ms
- Good: 15-40ms
- Acceptable: 40-70ms
- Poor: >70ms
- **Notes:** Serves as control - if Cloudflare is slow, general internet issue

## Buffering Detection Patterns

### Pattern 1: Latency Spike Preceding Bandwidth Drop

**Signature:** Latency increases 50-100ms, then Panel 2 shows bandwidth drop 10-30s later

**Interpretation:**

- High latency causes TCP to slow down
- Reduced TCP throughput manifests as bandwidth drop
- User experiences buffering shortly after latency spike

**Buffering Certainty:** High

**Investigation:**

1. Check which CDN spiked (this panel)
2. Check which service affected (Panel 8)
3. Check if packet loss also occurred (Panel 4)
4. Determine root cause: CDN vs network vs ISP

### Pattern 2: Sustained Elevated Latency

**Signature:** Latency consistently above acceptable threshold for >5 minutes

**Quality Impact:**

- 50-80ms sustained: Quality reduced, occasional buffering
- 80-120ms sustained: Frequent buffering, poor experience
- >120ms sustained: Constant buffering, unusable

**Expected User Behavior:**

- Adaptive bitrate will reduce quality
- Panel 2 will show reduced bandwidth
- User may abandon streaming session

**Root Cause Indicators:**

- All CDNs: Network/ISP issue
- Single CDN: CDN capacity/routing issue
- Peak hours: Normal congestion pattern

### Pattern 3: Intermittent Latency Spikes (Jitter)

**Signature:** Latency oscillates between good and poor rapidly

**Correlation with Panel 5:**

- This pattern will show high jitter (standard deviation)
- Panel 5 dedicated jitter measurement confirms

**Buffering Manifestation:**

- Micro-buffering (brief pauses)
- Quality cycling (adaptive bitrate struggling)
- Stuttering or freezing

**Root Causes:**

- WiFi interference or instability
- ISP routing instability (BGP flapping)
- Local network congestion cycling

### Pattern 4: Latency Increases During High Bandwidth

**Signature:** Latency rises when Panel 2 shows multiple high-bandwidth streams

**Interpretation:**

- Network or ISP link saturation
- Increased traffic causing queueing delays
- Affects latency before throughput

**Buffering Risk:**

- Moderate: If latency stays <100ms
- High: If latency exceeds 100ms
- Critical: If combined with packet loss (Panel 4)

**Mitigation:**

- Reduce concurrent streams
- Implement QoS to prioritize streaming
- Upgrade bandwidth if chronic

## CDN Performance Analysis

### Service-to-CDN Mapping for This Panel

**<www.netflix.com>:**

- **CDN:** Akamai and Netflix Open Connect Appliances (OCAs)
- **What it tests:** Path to Netflix content delivery
- **Expected latency:** <30ms optimal, <60ms acceptable
- **Geographic:** Typically resolves to nearest Netflix OCA or Akamai edge

**<www.youtube.com>:**

- **CDN:** Google Global Cache (GGC)
- **What it tests:** Path to YouTube content delivery
- **Expected latency:** <25ms optimal, <50ms acceptable
- **Geographic:** Google's extensive CDN network, usually excellent

**<www.amazon.com>:**

- **CDN:** Amazon CloudFront
- **What it tests:** Path to Prime Video and general Amazon content
- **Expected latency:** <30ms optimal, <60ms acceptable
- **Geographic:** CloudFront has many edge locations globally

**<www.cloudflare.com>:**

- **CDN:** Cloudflare CDN
- **What it tests:** General internet backbone health baseline
- **Expected latency:** <20ms optimal, <40ms acceptable
- **Geographic:** Cloudflare's Anycast network, very widely distributed

### Using Multiple CDNs for Diagnosis

**All 4 CDNs elevated:**

- Indicates: General network or ISP issue
- Not: CDN-specific problem
- Action: Check ISP connection, local network

**Only streaming CDNs elevated (not Cloudflare):**

- Indicates: ISP routing to streaming CDNs suboptimal
- Possible: ISP traffic shaping or peering issues
- Action: Contact ISP about streaming performance

**Single CDN elevated:**

- Indicates: That specific CDN having issues
- Expected: Occasional, CDN nodes can overload
- Action: Monitor for resolution, report if sustained

**Cloudflare elevated but streaming CDNs normal:**

- Indicates: Possible Cloudflare-specific routing issue
- Unusual: Cloudflare typically very reliable
- Action: Investigate local DNS or routing

### CDN Geographic Routing Analysis

**Low latency (<20ms):**

- Likely connected to nearby CDN edge node
- Optimal for streaming quality
- Geographic routing working well

**Moderate latency (20-50ms):**

- Probably connected to regional CDN node
- Still acceptable for streaming
- Not nearest node but reasonable

**High latency (>50ms):**

- Potentially connected to distant CDN node
- Geographic routing may be suboptimal
- Could indicate CDN capacity issues forcing distant routing

**Sudden latency change:**

- CDN load balancing or failover occurred
- May have switched to different geographic node
- Monitor to see if latency improves or degrades
