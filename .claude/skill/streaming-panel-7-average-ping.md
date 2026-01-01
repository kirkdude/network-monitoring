# Streaming Panel 7: Average Ping Latency

## Panel Overview

- **Panel ID:** 13
- **Title:** Average Ping Latency
- **Type:** Timeseries
- **Grid Position:** x=12, y=16, width=12, height=8
- **Purpose:** Provides overview of network health with relaxed thresholds compared to Panel 3, focusing on general connectivity rather than streaming-specific QoS

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

**Same data as Panel 3 (CDN Latency), different presentation**

### Metrics Used

- **InfluxDB:** `ping` measurement from Telegraf
- **Field:** `average_response_ms`
- **Targets:** Same 4 CDNs as Panel 3

## Current Configuration

### Thresholds & Colors

- **Green:** 0-99 ms (Good general connectivity)
- **Yellow:** 100-199 ms (Acceptable for basic use)
- **Red:** 200+ ms (Poor connectivity)

**Key Difference from Panel 3:**

- Panel 3: Streaming-focused thresholds (green <50ms, red >100ms)
- Panel 7: General connectivity thresholds (green <100ms, red >200ms)

**Use Case:**

- Panel 3: Streaming quality monitoring
- Panel 7: General network health overview

### Display Settings

- **Unit:** ms
- **Visualization:** Timeseries
- **Fill Opacity:** 15% (slightly more than Panel 3's 10%)
- **Legend:** Table with Mean, Max, Last

## Critical Lessons Learned

### Issue 1: Duplicate Information with Panel 3

**Observation:** This panel shows same data as Panel 3

**Why both exist:**

- Different threshold perspectives
- Panel 3: Strict streaming requirements
- Panel 7: Relaxed general connectivity
- Allows quick assessment at different quality levels

### Issue 2: Threshold Choice Rationale

**100ms threshold:**

- Too high for 4K streaming (need <50ms)
- Acceptable for HD streaming
- Good for web browsing, email, general use
- Indicates "network works" vs "network broken"

**200ms threshold:**

- Unusable for real-time applications
- Marginal even for HD streaming
- Clear indicator of network problems

## What's Working Well

- ✅ Quick "network health" overview
- ✅ Less sensitive than Panel 3 (fewer false alarms)
- ✅ Good for non-streaming network assessment
- ✅ Complements Panel 3's strict monitoring

## Current Gaps

- ❌ Redundant with Panel 3 for streaming use cases
- ❌ Thresholds may be too relaxed for modern streaming
- ❌ Could be replaced with multi-threshold view on Panel 3

## Potential Improvements

### 1. Consolidate with Panel 3

**What:** Combine with Panel 3 using multiple threshold lines
**How:** Add annotations to Panel 3:

- 50ms line: "Streaming Quality Threshold"
- 100ms line: "General Connectivity Threshold"
- 200ms line: "Poor Connectivity Threshold"

### 2. Repurpose for Different Targets

**What:** Test different endpoints (non-CDN)
**How:** Change targets to:

- ISP gateway
- General internet (8.8.8.8)
- Local network devices
**Purpose:** Differentiate local vs internet vs CDN issues

### 3. Add Packet Loss Context

**What:** Show latency with loss overlay
**How:** Combine Panel 3, 4, and 7 data into single comprehensive view

## Related Panels

- **Panel 3:** CDN Latency - Stricter thresholds, streaming-focused
- **Panel 4:** Packet Loss - Combined with latency for QoS picture
- **Panel 5:** Network Jitter - Latency variability
- **Panel 6:** DNS Resolution Time - Name resolution latency

## Investigation Workflow

### Workflow 1: General Network Health Check

**Daily monitoring routine:**

1. **Check this panel for overview:**
   - All green: Network healthy for all uses
   - Some yellow: Degraded but streaming may work
   - Any red: Network issues requiring investigation
2. **If yellow/red, check Panel 3:**
   - Panel 3 red but Panel 7 yellow: Streaming affected, browsing okay
   - Both red: General network failure
3. **Correlate with other panels:**
   - Check Panel 4 (loss), Panel 5 (jitter)
   - Determine if latency-only or multi-factor issue

### Workflow 2: Streaming vs Non-Streaming Diagnosis

**When isolating streaming-specific issues:**

1. **Compare Panel 3 and Panel 7:**
   - Panel 3 red, Panel 7 green: Streaming quality issue, network otherwise fine
   - Both red: General network problem affecting everything
2. **This helps determine:**
   - Is problem streaming-specific? (high standards not met)
   - Or general network failure? (basic connectivity impaired)
3. **Action priority:**
   - Panel 7 red: High priority (network broken)
   - Panel 3 red, Panel 7 yellow/green: Medium priority (streaming degraded)

## Common Scenarios & Responses

### Scenario 1: Panel 3 Red, Panel 7 Green

**Pattern:** Panel 3 showing 80-120ms (red), Panel 7 same values but green

**Interpretation:**

- Network latency inadequate for 4K streaming
- But acceptable for HD and general use
- Users may experience quality reduction

**Actions:**

- Inform users 4K may not work optimally
- HD streaming should be acceptable
- General internet use unaffected
- Investigate if latency can be improved

### Scenario 2: Panel 7 Yellow (100-150ms)

**Pattern:** Latency in the yellow zone

**Interpretation:**

- Network degraded but functional
- Streaming will adapt quality downward
- Browsing will be slower but usable

**Actions:**

- Check Panel 4 (loss) and Panel 5 (jitter)
- If loss/jitter also elevated: Investigate network
- If only latency: May be acceptable temporarily
- Monitor for escalation to red zone

### Scenario 3: Panel 7 Red (>200ms)

**Pattern:** Latency exceeds 200ms

**Interpretation:**

- Severe network issues
- Streaming unusable
- Even browsing significantly impaired

**Actions:**

- **Immediate investigation required**
- Check Panel 4: Is packet loss also present?
- Check Panel 5: Is jitter also high?
- Check physical connections, ISP status
- This is outage-level severity

### Scenario 4: Both Panels Green

**Pattern:** Panel 3 and 7 both green (<50ms)

**Interpretation:**

- Optimal network performance
- All streaming qualities supported
- General internet use excellent

**Actions:**

- No action needed
- Current baseline for comparison
- Document as "healthy state"

## Files Referenced

- **Dashboard JSON:** `/Users/kirkl/src/network-monitoring/grafana-dashboards/streaming-monitor.json` (Panel ID 13)
- **Telegraf Config:** `/Users/kirkl/src/network-monitoring/telegraf.conf` (inputs.ping, lines 12-24)

## Streaming Quality Metrics

### Panel 3 vs Panel 7 Threshold Comparison

| Latency | Panel 3 (Streaming) | Panel 7 (General) | User Impact |
|---------|---------------------|-------------------|-------------|
| <50ms | Green (Excellent) | Green (Excellent) | All uses optimal |
| 50-100ms | Yellow/Red | Green | Streaming degraded, browsing fine |
| 100-200ms | Red (Poor) | Yellow | Streaming poor, browsing slow |
| >200ms | Red (Poor) | Red (Poor) | All uses impaired |

### When to Use Which Panel

**Use Panel 3 when:**

- Investigating streaming quality issues
- Monitoring 4K/8K streaming requirements
- Need strict QoS metrics
- Troubleshooting buffering

**Use Panel 7 when:**

- General network health overview
- Non-streaming use cases
- Want less sensitive alerting
- Assessing basic connectivity

## Buffering Detection Patterns

**This panel uses same data as Panel 3**

Refer to Panel 3 skill for buffering detection patterns.

**Key difference:** Thresholds less sensitive

- Panel 7 green doesn't mean streaming is perfect
- Panel 7 red definitely means streaming is broken
- For buffering investigation, primarily use Panel 3

## CDN Performance Analysis

**This panel monitors same CDNs as Panel 3**

Refer to Panel 3 skill for CDN-specific analysis.

**Purpose difference:**

- Panel 3: CDN performance for streaming
- Panel 7: CDN as internet connectivity indicator

**Usage:** This panel helps distinguish:

- CDN issue vs general internet issue
- Streaming-specific problem vs widespread problem
