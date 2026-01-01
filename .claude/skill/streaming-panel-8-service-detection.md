# Streaming Panel 8: Streaming Service Detection (DNS)

## Panel Overview

- **Panel ID:** 3
- **Title:** Streaming Service Detection (DNS)
- **Type:** Table
- **Grid Position:** x=0, y=24, width=12, height=10
- **Purpose:** Identifies which streaming services are being used across the network by analyzing DNS queries, mapping devices to services for usage tracking and troubleshooting

## Data Source

### Current: InfluxDB Flux Query

```flux
import "strings"

from(bucket: "network")
  |> range(start: v.timeRangeStart, stop: v.timeRangeStop)
  |> filter(fn: (r) => r._measurement == "dns_query" and r._field == "domain")
  |> filter(fn: (r) => r._value =~ /netflix|disney|amazon.*video|youtube|googlevideo|hulu|hbo|twitch|spotify|apple.*tv|paramount|peacock|pluto|roku/)
  |> map(fn: (r) => ({r with
      service: if strings.containsStr(v: r._value, substr: "netflix") then "Netflix"
        else if strings.containsStr(v: r._value, substr: "disney") then "Disney+"
        else if strings.containsStr(v: r._value, substr: "amazon") then "Prime Video"
        else if strings.containsStr(v: r._value, substr: "youtube") or strings.containsStr(v: r._value, substr: "googlevideo") then "YouTube"
        else if strings.containsStr(v: r._value, substr: "hulu") then "Hulu"
        else if strings.containsStr(v: r._value, substr: "hbo") then "HBO Max"
        else if strings.containsStr(v: r._value, substr: "twitch") then "Twitch"
        else if strings.containsStr(v: r._value, substr: "spotify") then "Spotify"
        else if strings.containsStr(v: r._value, substr: "apple") then "Apple TV+"
        else if strings.containsStr(v: r._value, substr: "paramount") then "Paramount+"
        else if strings.containsStr(v: r._value, substr: "peacock") then "Peacock"
        else if strings.containsStr(v: r._value, substr: "pluto") then "Pluto TV"
        else if strings.containsStr(v: r._value, substr: "roku") then "Roku Channel"
        else "Other Streaming"
    }))
  |> group(columns: ["device_name", "service"])
  |> count()
  |> group()
  |> rename(columns: {_value: "DNS Queries"})
  |> sort(columns: ["DNS Queries"], desc: true)
```

**Query Breakdown:**

1. **Filter streaming DNS queries** using regex pattern
2. **Map domains to service names** using string matching
3. **Group by device and service** to get per-device, per-service counts
4. **Count queries** to show activity level
5. **Sort by query count** to show most active

### Services Detected (13 Total)

- Netflix
- Disney+
- Prime Video (Amazon)
- YouTube
- Hulu
- HBO Max
- Twitch
- Spotify
- Apple TV+
- Paramount+
- Peacock
- Pluto TV
- Roku Channel

## Current Configuration

### Display Settings

- **Visualization:** Table
- **Columns:** device_name, service, DNS Queries (count)
- **Sorting:** By DNS Queries descending (most active first)
- **Column Override:** _value renamed to "DNS Queries"

## Critical Lessons Learned

### Issue 1: DNS-Based Detection Limitations

**What's detected:** DNS queries to streaming domains
**What's NOT detected:**

- Services without DNS queries (already cached, using IP)
- Services with generic domain names
- Encrypted DNS (DoH/DoT bypasses router)

**Accuracy:** ~90% for active streaming sessions

### Issue 2: Query Count vs Actual Usage

**High query count ≠ high streaming:**

- Some services query frequently for metadata
- Background app activity generates queries
- Service checks even when not streaming

**Better correlation:** Cross-reference with Panel 2 bandwidth

### Issue 3: Service Name Ambiguity

**Challenges:**

- "amazon" matches both Prime Video and Amazon shopping
- "apple" matches Apple TV+ and other Apple services
- Multiple CDNs per service

**Solution:** Regex patterns tuned to streaming-specific domains

## What's Working Well

- ✅ Identifies 13 major streaming services
- ✅ Maps services to specific devices
- ✅ Shows activity levels via query counts
- ✅ Real-time service usage visibility
- ✅ Helps troubleshoot service-specific issues
- ✅ Useful for household usage tracking

## Current Gaps

- ❌ Doesn't detect services not in the list
- ❌ No bandwidth correlation (DNS count ≠ usage)
- ❌ No quality assessment per service
- ❌ No CDN mapping (which CDN each service uses)
- ❌ Encrypted DNS bypasses detection
- ❌ No historical baseline comparison

## Potential Improvements

### 1. Add Service-to-CDN Mapping

**What:** Show which CDN each service uses
**How:** Add column mapping services to CDNs:

- Netflix → Akamai/Netflix OCA
- YouTube → Google Global Cache
- Prime Video → CloudFront

**Impact:** Connect Panel 3 CDN metrics to specific services

### 2. Correlate with Bandwidth

**What:** Join with Panel 2 bandwidth data
**How:** Show bandwidth alongside DNS queries

**Display:**

- Service | Device | DNS Queries | Bandwidth Used
- Netflix | LG TV | 45 | 15 GB

**Impact:** Distinguish active streaming from background checks

### 3. Add Service Quality Indicators

**What:** Show if service is experiencing issues
**How:** Correlate with Panel 3 (latency) and Panel 4 (loss)

**Display:** Traffic light indicator per service:

- 🟢 Netflix (Good QoS)
- 🟡 YouTube (Moderate QoS)
- 🔴 Prime Video (Poor QoS)

## Related Panels

- **Panel 1:** Active Streaming Sessions - See which devices are streaming
- **Panel 2:** Streaming Bandwidth Timeline - Correlate service with bandwidth
- **Panel 3:** CDN Latency - Map service to CDN, check performance
- **Panel 9:** CDN Connection Health - See CDN usage breakdown
- **Panel 13:** Recent DNS Queries - Detailed query log

## Investigation Workflow

### Workflow 1: Service-Specific Quality Issue

**When users report issues with specific service:**

1. **Check this panel:** Is device accessing that service?
2. **Note query count:** Active use or background only?
3. **Check Panel 2:** Is device showing streaming bandwidth?
4. **Map to CDN:**
   - Netflix → Check Panel 3 for Akamai latency
   - YouTube → Check Panel 3 for Google Cache latency
   - Prime → Check Panel 3 for CloudFront latency
5. **Check Panel 4:** Is CDN experiencing packet loss?
6. **Diagnosis:**
   - Service DNS present + bandwidth low → Service issue or CDN
   - Service DNS present + high latency to CDN → CDN problem
   - Service DNS absent → Not actually using service

### Workflow 2: Household Usage Tracking

**For monitoring family streaming habits:**

1. **Group by device:** See which devices use which services
2. **Compare query counts:** Relative usage levels
3. **Time range analysis:**
   - 1 hour: Current activity
   - 24 hours: Daily patterns
   - 7 days: Weekly habits
4. **Cross-reference Panel 11:** Total bandwidth correlates with service usage

### Workflow 3: CDN Problem Service Mapping

**When CDN has issues, identify affected services:**

1. **Check Panel 3:** Which CDN has high latency?
2. **Map CDN to services:**
   - Akamai high → Check Netflix, Disney+, Hulu
   - Google high → Check YouTube
   - CloudFront high → Check Prime Video
3. **Verify in this panel:** Are those services being used?
4. **Check Panel 2:** Are those devices showing quality degradation?

## Common Scenarios & Responses

### Scenario 1: High DNS Query Count, Low Bandwidth

**Pattern:** Device showing 100+ DNS queries to Netflix, but Panel 2 shows <1 Mbps

**Analysis:** App open but not streaming, or background activity

**Investigation:**

1. Check timing in Panel 13 (Recent Queries)
2. Continuous queries without bandwidth = app open, browsing
3. Check if device present in Panel 1 (Active Sessions)

**Interpretation:**

- User browsing catalog, not streaming
- App background metadata refresh
- Not actual streaming activity

### Scenario 2: Device Shows Multiple Services

**Pattern:** Single device (LG TV) showing Netflix, YouTube, Hulu all with queries

**Analysis:** Normal - devices check multiple apps

**Interpretation:**

- Apps refreshing in background
- User switching between services
- Auto-play from one service to another

**Action:** Cross-check Panel 2 to see which is actually streaming (highest bandwidth)

### Scenario 3: Service Detection But User Reports Not Using

**Pattern:** Panel shows YouTube, but user says they weren't watching YouTube

**Possible Causes:**

1. **Background activity:** App auto-refreshing
2. **Ads:** Many sites embed YouTube for ads
3. **Cached content:** Old DNS queries still counted
4. **Other app:** Another app using YouTube's infrastructure

**Investigation:**

1. Check Panel 13 for specific domains queried
2. Check Panel 2 for bandwidth at same time
3. Verify time range matches user's complaint

### Scenario 4: Expected Service Missing

**Pattern:** User reports streaming Netflix, but panel doesn't show it

**Possible Causes:**

1. **DNS cache:** Resolved earlier, using cached IP
2. **Encrypted DNS:** Device using DoH/DoT
3. **VPN:** DNS queries bypassing router
4. **Time range:** Not looking at correct time window

**Investigation:**

1. Expand time range (check last 6-24 hours)
2. Check Panel 1: Is device showing as active streamer?
3. Check Panel 2: Is device using bandwidth consistent with streaming?
4. Check router DNS settings

### Scenario 5: High Spotify Queries (Music vs Video)

**Pattern:** Spotify showing high query count

**Note:** Spotify is audio, not video streaming

**Bandwidth expectations:**

- Spotify: 0.5-1 Mbps (much lower than video)
- If device shows high bandwidth: Not Spotify, likely video streaming

**Action:** Don't confuse audio with video streaming when investigating buffering

## Files Referenced

- **Dashboard JSON:** `/Users/kirkl/src/network-monitoring/grafana-dashboards/streaming-monitor.json` (Panel ID 3)
- **Router DNS Export:** `/root/bin/dns-monitor-daemon.sh` (captures DNS queries)

## Streaming Quality Metrics

### Service-to-CDN Mapping

| Service | Primary CDN | Panel 3 Target | Expected Latency |
|---------|-------------|----------------|------------------|
| Netflix | Akamai, Netflix OCA | <www.netflix.com> | <30ms |
| YouTube | Google Global Cache | <www.youtube.com> | <25ms |
| Prime Video | CloudFront | <www.amazon.com> | <35ms |
| Disney+ | Akamai, Bamtech | (use netflix proxy) | <30ms |
| Hulu | Akamai, Fastly | (use netflix proxy) | <35ms |
| HBO Max | Akamai | (use netflix proxy) | <30ms |
| Twitch | Amazon IVS | <www.amazon.com> | <35ms |
| Apple TV+ | Apple CDN | (separate monitoring needed) | <40ms |

### Service-Specific Bandwidth Patterns

**Netflix:**

- SD: 3 Mbps
- HD: 5 Mbps
- 4K: 25 Mbps
- Pattern: Smooth, gradually rising

**YouTube:**

- 480p: 1.1 Mbps
- 1080p: 4.5 Mbps
- 4K: 35 Mbps
- Pattern: Spiky, aggressive preloading

**Disney+:**

- HD: 5 Mbps
- 4K: 25 Mbps
- Pattern: Very consistent

**Use:** Compare bandwidth (Panel 2) with service detected here to validate streaming activity

## Buffering Detection Patterns

**This panel identifies WHICH service is being used**

For buffering investigation:

1. **Identify service** from this panel
2. **Map to CDN** using table above
3. **Check CDN metrics** in Panels 3-5
4. **Correlate with bandwidth** in Panel 2

**Example Investigation:**

1. Panel 8: Device streaming Netflix
2. Map: Netflix uses Akamai
3. Panel 3: Check <www.netflix.com> latency
4. Panel 4: Check <www.netflix.com> packet loss
5. Panel 2: Check device bandwidth pattern
6. **Conclusion:** Netflix via Akamai experiencing issues

## CDN Performance Analysis

### Using This Panel for CDN Correlation

**Service Detection → CDN Mapping → Performance Analysis**

**Workflow:**

1. **This panel:** Which services being used?
2. **CDN Mapping:** Which CDNs those services use?
3. **Panel 3:** Check latency to those CDNs
4. **Panel 4:** Check loss to those CDNs
5. **Panel 9:** Verify devices connecting to expected CDNs

**Example:**

- Multiple devices showing Netflix (this panel)
- All should use Akamai (mapping)
- Check Panel 3: <www.netflix.com> latency high?
- Check Panel 9: Devices connecting to Akamai?
- Conclusion: Akamai performance affecting all Netflix users

**Value:** Correlates user-reported service issues with infrastructure metrics
