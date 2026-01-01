# Streaming Panel 6: DNS Resolution Time

## Panel Overview

- **Panel ID:** 12
- **Title:** DNS Resolution Time
- **Type:** Timeseries
- **Grid Position:** x=0, y=16, width=12, height=8
- **Purpose:** Monitors DNS query response times to streaming service domains, detecting DNS performance issues that cause delayed stream starts and CDN selection problems

## Data Source

### Current: InfluxDB Flux Query

```flux
from(bucket: "network")
  |> range(start: v.timeRangeStart, stop: v.timeRangeStop)
  |> filter(fn: (r) => r._measurement == "dns_query")
  |> filter(fn: (r) => r._field == "query_time_ms")
  |> aggregateWindow(every: 30s, fn: mean, createEmpty: false)
  |> group(columns: ["domain"])
```

**Field:** `query_time_ms` - Time to resolve domain name to IP address

### Metrics Used

- **InfluxDB:** `dns_query` measurement from Telegraf
- **Telegraf Plugin:** `inputs.dns_query`
- **Domains Tested:** netflix.com, youtube.com, primevideo.com, disneyplus.com
- **DNS Server:** 192.168.1.2 (router)
- **Query Type:** A records
- **Interval:** 30 seconds

### Data Collection Flow

1. **Telegraf:** `inputs.dns_query` plugin queries router DNS
2. **Router:** Resolves or forwards to upstream DNS (ISP or 1.1.1.1/8.8.8.8)
3. **Measurement:** Time from query to response
4. **InfluxDB:** Stores timing in "network" bucket
5. **Grafana:** Displays timelines per domain

## Current Configuration

### Thresholds & Colors

- **Green:** 0-19 ms (Excellent)
- **Yellow:** 20-49 ms (Acceptable)
- **Orange:** 50-99 ms (Slow)
- **Red:** 100+ ms (Poor, noticeable delay)

**Context:**

- <10 ms: Optimal (cached or very fast DNS)
- 10-20 ms: Excellent (typical local DNS with cache)
- 20-50 ms: Acceptable (upstream DNS lookup)
- 50-100 ms: Slow (affects initial stream start)
- >100 ms: Poor (noticeable delay, CDN selection issues)

### Display Settings

- **Unit:** ms
- **Display Name:** `${__field.labels.domain}` - Domain name
- **Visualization:** Timeseries line graph
- **Legend:** Table with Mean, Max, Last

## Critical Lessons Learned

### Issue 1: Caching Effects

**Observation:** DNS times vary dramatically based on cache state

**Patterns:**

- First query: 50-200 ms (upstream lookup)
- Subsequent queries: 1-5 ms (cached)
- After TTL expires: Slow again

**Interpretation:**

- Spikes are normal when cache expires
- Focus on average/typical times
- Consistent high times indicate problem

### Issue 2: DNS Server Choice Impact

**Testing Results:**

- Local router DNS (with upstream): 10-50 ms typical
- Direct ISP DNS: 15-40 ms typical
- Cloudflare (1.1.1.1): 15-30 ms typical
- Google (8.8.8.8): 20-40 ms typical

**Current setup:** Router (192.168.1.2) forwarding to upstream

### Issue 3: CDN Selection Impact

**Key Insight:** DNS resolution time affects which CDN node selected

**Mechanism:**

- Slow DNS → Client may timeout, retry
- Retry may get different CDN node
- Different node may have different performance

**Monitoring value:** Slow DNS can indirectly cause poor CDN selection

## What's Working Well

- ✅ Detects DNS performance issues
- ✅ Tests actual streaming service domains
- ✅ Monitors through router (real user path)
- ✅ 30-second interval catches most issues
- ✅ Multiple services provide comparison
- ✅ Identifies DNS vs network vs CDN issues

## Current Gaps

- ❌ Only tests 4 domains (many more streaming services exist)
- ❌ No cache vs non-cache differentiation
- ❌ No upstream DNS server identification
- ❌ No geographic CDN node detection
- ❌ No correlation with actual device queries

## Potential Improvements

### 1. Add More Streaming Domains

**What:** Test additional services (HBO Max, Hulu, Paramount+, etc.)
**How:** Add domains to telegraf.conf inputs.dns_query

### 2. Test Multiple DNS Servers

**What:** Compare router vs ISP vs public DNS performance
**How:** Run parallel queries to different servers

### 3. Correlate with Panel 13

**What:** Cross-reference with actual device DNS queries
**How:** Compare Telegraf test queries to real device query patterns

## Related Panels

- **Panel 3:** CDN Latency - DNS affects which CDN node selected
- **Panel 8:** Streaming Service Detection - Shows which services actively used
- **Panel 13:** Recent DNS Queries - Shows actual device DNS activity

## Investigation Workflow

### Workflow 1: Slow Stream Start Investigation

**When streams take long to start:**

1. **Check DNS times at stream start:**
   - <50 ms: DNS not the bottleneck
   - 50-100 ms: DNS contributing to delay
   - >100 ms: DNS primary cause
2. **Check if spike or sustained:**
   - Single spike: Cache miss (normal)
   - Sustained high: DNS server issue
3. **Compare all domains:**
   - All slow: DNS server problem
   - One domain slow: That domain's authoritative DNS issue

### Workflow 2: CDN Selection Problems

**When users get poor CDN nodes:**

1. **Check DNS times for affected service**
2. **Slow DNS may cause:**
   - Client timeout and retry
   - Different CDN node on retry
   - Suboptimal node selection
3. **Correlate with Panel 3:**
   - High DNS time + high CDN latency = Compounding issues

## Common Scenarios & Responses

### Scenario 1: Periodic Spikes (Cache Expiry Pattern)

**Pattern:** DNS time spikes to 80-150 ms periodically (every 5-15 minutes)

**Analysis:** Normal cache expiry and refresh

**Expected Behavior:**

- Most queries: 5-20 ms (cached)
- Periodic spike: 50-150 ms (cache refresh)
- Pattern matches domain TTL

**Action:** No action needed if:

- Spikes are brief (1-2 data points)
- Return to normal quickly
- Not causing user-reported issues

### Scenario 2: All Domains Consistently Slow (>50ms)

**Pattern:** All streaming domains showing 60-120 ms consistently

**Analysis:** DNS server performance issue

**Investigation:**

1. Check router DNS settings
2. Test upstream DNS directly
3. Consider switching DNS provider

**Actions:**

- Try alternate DNS (1.1.1.1, 8.8.8.8)
- Check ISP DNS health
- Consider caching DNS resolver locally

### Scenario 3: Single Domain Slow

**Pattern:** Netflix 100+ ms, others <30 ms

**Analysis:** That domain's authoritative DNS slow

**Possible Causes:**

- Service's DNS infrastructure overloaded
- ISP routing to that DNS slow
- Geographic DNS issue

**Action:**

- Monitor for resolution (usually temporary)
- Report if sustained >24 hours
- Check if affecting stream performance

### Scenario 4: DNS Degradation During Peak Hours

**Pattern:** DNS times rise from 20 ms to 80+ ms during 6-11 PM

**Analysis:** DNS server capacity insufficient for peak load

**Investigation:**

1. Check if router overloaded (CPU, memory)
2. Check upstream DNS server
3. Compare ISP DNS vs public DNS

**Actions:**

- Consider more capable router
- Switch to faster DNS provider
- Enable DNS caching

## Files Referenced

- **Dashboard JSON:** `/Users/kirkl/src/network-monitoring/grafana-dashboards/streaming-monitor.json` (Panel ID 12)
- **Telegraf Config:** `/Users/kirkl/src/network-monitoring/telegraf.conf` (inputs.dns_query, lines 26-35)

## Streaming Quality Metrics

### DNS Time Impact on User Experience

| DNS Time | Stream Start Delay | User Perception |
|----------|-------------------|-----------------|
| <20 ms | Instant | Imperceptible |
| 20-50 ms | <1s additional | Barely noticeable |
| 50-100 ms | 1-2s additional | Noticeable |
| 100-200 ms | 2-4s additional | Annoying |
| >200 ms | 4+ s additional | Unacceptable |

### DNS + CDN Latency Combined Impact

**Total time to start stream ≈ DNS time + CDN connect + initial buffer**

**Example:**

- DNS: 100 ms
- CDN connect: 200 ms
- Initial buffer: 2 seconds
- **Total: 2.3 seconds** before playback

**Optimization opportunity:** Reducing DNS from 100ms to 20ms saves 80ms (3.5% improvement)

## Buffering Detection Patterns

**DNS primarily affects initial stream start, not ongoing buffering**

**However, DNS issues can cause:**

- Slow CDN node discovery
- Failed connections (timeout, retry with different node)
- Suboptimal CDN selection

**Indirect buffering causes:**

1. Slow DNS → Poor CDN selected → High latency (Panel 3) → Buffering
2. Slow DNS → Connection timeout → Reconnect delay → Buffer underrun

**Check:** If buffering occurs WITH high DNS times, DNS may be indirect cause

## CDN Performance Analysis

### DNS Geographic Routing

**How DNS affects CDN selection:**

1. Client queries streaming domain DNS
2. Authoritative DNS sees client IP (or DNS resolver IP)
3. DNS returns IP of geographically close CDN node
4. Client connects to that CDN node

**DNS Time Impact:**

- Fast DNS: Smooth process, optimal node
- Slow DNS: Client may timeout, get suboptimal node

### Using This Panel for CDN Diagnosis

**Scenario:** Users reporting poor streaming quality

**Investigation:**

1. Check DNS times (this panel)
2. If DNS slow: May be getting poor CDN nodes
3. Check Panel 3: Verify CDN latency also high
4. Conclusion: Slow DNS → Poor CDN selection → High latency

**Solution:**

- Fix DNS performance
- This may improve CDN selection
- Result: Better streaming quality
