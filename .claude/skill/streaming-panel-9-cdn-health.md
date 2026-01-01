# Streaming Panel 9: CDN Connection Health

## Panel Overview

- **Panel ID:** 4
- **Title:** CDN Connection Health
- **Type:** Table
- **Grid Position:** x=12, y=24, width=12, height=10
- **Purpose:** Maps devices to CDN providers based on DNS query patterns, showing which CDN infrastructure each device is using for content delivery

## Data Source

### Current: InfluxDB Flux Query

```flux
import "strings"

from(bucket: "network")
  |> range(start: v.timeRangeStart, stop: v.timeRangeStop)
  |> filter(fn: (r) => r._measurement == "dns_query" and r._field == "domain")
  |> filter(fn: (r) => r._value =~ /akamai|fastly|cloudfront|cdn|limelight|edgecast/)
  |> map(fn: (r) => ({r with
      cdn: if strings.containsStr(v: r._value, substr: "akamai") then "Akamai"
        else if strings.containsStr(v: r._value, substr: "fastly") then "Fastly"
        else if strings.containsStr(v: r._value, substr: "cloudfront") then "CloudFront"
        else if strings.containsStr(v: r._value, substr: "limelight") then "Limelight"
        else if strings.containsStr(v: r._value, substr: "edgecast") then "Edgecast"
        else "Other CDN"
    }))
  |> group(columns: ["device_name", "cdn"])
  |> count()
  |> group()
  |> sort(columns: ["_value"], desc: true)
```

**Query Breakdown:**

1. **Filter CDN domain patterns** from DNS queries
2. **Map domains to CDN providers** using string matching
3. **Group by device and CDN** to show device-CDN relationships
4. **Count connections** to show activity level
5. **Sort by connection count**

### CDNs Detected (5 Major + Others)

- **Akamai:** Netflix, Disney+, HBO Max, Hulu
- **CloudFront:** Prime Video, Twitch, many others
- **Fastly:** Hulu, HBO Max, various services
- **Limelight:** Older content, some legacy services
- **Edgecast:** Various services, less common
- **Other CDN:** Catches unlisted CDN providers

## Current Configuration

### Display Settings

- **Visualization:** Table
- **Columns:** device_name, cdn, Connections (count)
- **Sorting:** By connection count descending
- **Column Override:** _value renamed to "Connections"

## Critical Lessons Learned

### Issue 1: CDN Detection vs Service Detection

**Relationship:**

- Panel 8: Detects streaming SERVICES (Netflix, YouTube, etc.)
- Panel 9: Detects CDN INFRASTRUCTURE (Akamai, CloudFront, etc.)

**Many-to-many relationship:**

- Single service may use multiple CDNs (Netflix uses Akamai + own OCAs)
- Single CDN may serve multiple services (Akamai serves Netflix, Disney+, Hulu)

**Use together:** Service (Panel 8) + CDN (Panel 9) + performance (Panel 3/4) = complete picture

### Issue 2: Generic CDN Domains

**Pattern:** "cdn" in domain name catches many providers

**Ambiguity:** Hard to identify specific CDN from just "cdn" string

**Classified as "Other CDN"** when more specific pattern doesn't match

**Limitation:** Some CDNs may not be specifically identified

### Issue 3: Connection Count Interpretation

**High count doesn't mean high bandwidth:**

- May be many small queries/connections
- Or few high-bandwidth connections

**Better correlation:** Cross-reference Panel 11 (bandwidth) with this panel

## What's Working Well

- ✅ Identifies major CDN providers
- ✅ Maps devices to CDN infrastructure
- ✅ Enables CDN-specific troubleshooting
- ✅ Shows CDN usage diversity
- ✅ Connection counts indicate activity level
- ✅ Sorted for easy scanning

## Current Gaps

- ❌ No bandwidth correlation (connection count ≠ data volume)
- ❌ No CDN node geographic information
- ❌ Limited to 5 specific CDNs (may miss others)
- ❌ No CDN performance overlay (have to cross-reference Panel 3)
- ❌ No indication of CDN health status
- ❌ No service-to-CDN correlation in single view

## Potential Improvements

### 1. Add Bandwidth Per CDN

**What:** Show total bandwidth via each CDN, not just connection count
**How:** Join with bandwidth data from Panel 2

**Display:**

- Device | CDN | Connections | Bandwidth
- LG TV | Akamai | 45 | 15 GB

### 2. Add CDN Health Indicator

**What:** Color-code CDNs by current performance
**How:** Join with Panel 3 (latency) and Panel 4 (loss) data

**Display:** Cell coloring based on QoS:

- Green: Good latency + no loss
- Yellow: Moderate latency
- Red: High latency or loss

### 3. Add Service Mapping Column

**What:** Show which services use each CDN
**How:** Cross-reference with Panel 8 data

**Display:**

- Device | CDN | Services | Connections
- LG TV | Akamai | Netflix, Disney+ | 45

### 4. Expand CDN Detection List

**What:** Add more CDNs (Level 3, Verizon, ChinaCache, etc.)
**How:** Add patterns to string matching logic

## Related Panels

- **Panel 3:** CDN Latency - Performance metrics for CDNs shown here
- **Panel 4:** Packet Loss to CDNs - Quality metrics for CDNs
- **Panel 8:** Streaming Service Detection - Services map to CDNs here
- **Panel 13:** Recent DNS Queries - Raw CDN domain queries

## Investigation Workflow

### Workflow 1: CDN-Specific Quality Issue Investigation

**When Panel 3 shows high latency for specific CDN:**

1. **Identify affected CDN** in Panel 3 (e.g., Akamai >80ms)
2. **Check this panel:** Which devices use that CDN?
3. **Map to services:**
   - Akamai devices likely using Netflix, Disney+, Hulu
   - Verify with Panel 8
4. **Check those devices in Panel 2:** Bandwidth degraded?
5. **Confirm user impact:**
   - Bandwidth reduced + Akamai latency high = CDN issue affecting users
6. **Check Panel 13:** See specific CDN domains being queried

**Diagnosis complete:** Akamai performance issue affecting Netflix/Disney+ users

### Workflow 2: Device CDN Failover Detection

**When device switches CDN providers:**

1. **Monitor this panel over time** (extend time range to 6-24 hours)
2. **Look for CDN changes for single device:**
   - Device initially shows Akamai connections
   - Later shows CloudFront connections
   - Indicates: Service or CDN failover
3. **Correlate with QoS:**
   - Check Panel 3: Was Akamai performing poorly?
   - Check Panel 4: Packet loss on Akamai?
4. **Check Panel 2:** Did bandwidth improve after switch?

**Interpretation:**

- Automatic failover due to CDN issues
- May be service switching (Netflix to Prime Video)
- Or CDN provider failover

### Workflow 3: Multi-CDN Usage Analysis

**When device shows connections to multiple CDNs:**

1. **Normal for multi-service users:**
   - Netflix (Akamai) + YouTube (Google) = Multiple CDN natural
2. **Check Panel 8:** Confirm multiple services detected
3. **Verify correlation:**
   - Each service should map to expected CDN
   - Unexpected CDN usage may indicate app behavior changes

## Common Scenarios & Responses

### Scenario 1: All Devices Using Single CDN (Akamai Dominant)

**Pattern:** 80%+ of connections show Akamai

**Analysis:**

- Netflix is dominant streaming service in household
- May indicate Netflix-heavy usage
- Single point of failure if Akamai has issues

**Investigation:**

1. Check Panel 8: Confirm Netflix dominance
2. Check Panel 3: How is Akamai performing?
3. If Akamai issues arise: All streaming affected

**Risk:** CDN concentration risk

**Actions:**

- Diversify streaming services for CDN redundancy
- Monitor Akamai performance closely (Panel 3)
- Have backup entertainment during Akamai outages

### Scenario 2: Device Shows Unexpected CDN

**Pattern:** Known Netflix device showing CloudFront connections

**Possible Causes:**

1. **Service switched:** User now watching Prime Video
2. **CDN failover:** Netflix using CloudFront as backup
3. **Mixed usage:** Netflix + Prime Video simultaneously
4. **App ads:** App serving ads via different CDN

**Investigation:**

1. Check Panel 8: Which services device detected using?
2. Check Panel 13: Specific domains queried?
3. Check Panel 2: Bandwidth pattern match expected service?

### Scenario 3: CDN Not in Panel 3 But Showing Here

**Pattern:** Device shows "Fastly" but Fastly not monitored in Panel 3

**Limitation:** Panel 3 only monitors 4 endpoints

**Impact:**

- Can't correlate Fastly performance with this usage
- Blind spot in QoS monitoring

**Actions:**

- Document which devices use Fastly
- Consider adding Fastly to Panel 3 monitoring
- Use Panel 13 to identify specific Fastly domains
- Could add custom ping probe for those domains

### Scenario 4: High Connection Count, Low Bandwidth

**Pattern:** Device shows 500+ CDN connections but Panel 11 shows low bandwidth

**Analysis:**

- Many small connections (app metadata, images, etc.)
- Not high-bandwidth streaming
- Background app activity

**Investigation:**

1. Check Panel 2: Is device actually streaming?
2. Check Panel 1: Device in active sessions?
3. If no streaming: Background app refreshes, catalog browsing

**Action:** Normal app behavior, not actual streaming

### Scenario 5: Sudden CDN Appearance

**Pattern:** CDN not seen before suddenly appears with high connection count

**Analysis:** New service usage or CDN routing change

**Investigation:**

1. Check Panel 8: New service detected?
2. Check Panel 13: New domain patterns?
3. Check Panel 2: New device streaming?

**Causes:**

- User started using new streaming service
- Existing service changed CDN provider
- CDN failover to different provider

**Action:**

- If new service: Document baseline
- If CDN change: Monitor performance on new CDN
- If failover: Check why original CDN failed

## Files Referenced

- **Dashboard JSON:** `/Users/kirkl/src/network-monitoring/grafana-dashboards/streaming-monitor.json` (Panel ID 4)
- **Router DNS Daemon:** `/root/bin/dns-monitor-daemon.sh` (captures DNS queries)

## Streaming Quality Metrics

### Service-to-CDN Mapping Reference

| Service | Primary CDN(s) | Panel 3 Proxy | Backup/Alternative CDNs |
|---------|----------------|---------------|-------------------------|
| Netflix | Akamai, Netflix OCA | <www.netflix.com> | Limelight, Level 3 |
| YouTube | Google Global Cache | <www.youtube.com> | Google Cloud CDN |
| Prime Video | CloudFront | <www.amazon.com> | Akamai |
| Disney+ | Akamai, Bamtech | <www.netflix.com> (proxy) | Level 3 |
| Hulu | Akamai, Fastly | <www.netflix.com> (proxy) | Level 3 |
| HBO Max | Akamai, Fastly | <www.netflix.com> (proxy) | CloudFront |
| Twitch | CloudFront, IVS | <www.amazon.com> | Fastly |
| Apple TV+ | Apple CDN | (not monitored) | Akamai |
| Spotify | Fastly, GCP | (not monitored) | Cloudflare |

### Using CDN Mapping for QoS Troubleshooting

**Complete workflow:**

1. **This panel:** Device X uses Akamai
2. **Panel 8:** Device X streaming Netflix
3. **Correlation:** Netflix on Akamai (expected)
4. **Panel 3:** Check <www.netflix.com> latency
5. **Panel 4:** Check <www.netflix.com> packet loss
6. **Diagnosis:** Akamai performance directly affects Netflix on Device X

## Buffering Detection Patterns

### Pattern 1: CDN Switch During Stream

**Signature:** Device shows Akamai connections, then CloudFront appears, Akamai count stops growing

**Interpretation:**

- Service switching (Netflix to Prime Video), or
- CDN failover (Netflix using CloudFront backup)

**Buffering Correlation:**

1. Check Panel 10: Bandwidth drops during transition?
2. Check Panel 13: Timing of DNS queries to new CDN?
3. Brief buffering during CDN switch is expected

### Pattern 2: Multiple Devices Same CDN, All Buffering

**Signature:** Panel 10 shows buffering on devices that this panel shows all use Akamai

**Conclusion:** CDN-specific issue

**Investigation:**

1. Panel 3: Confirm Akamai (netflix.com) latency elevated
2. Panel 4: Check Akamai packet loss
3. This panel: Identify all Akamai-using devices
4. Panel 2: Check if all showing bandwidth degradation

**Root cause:** Akamai CDN node performance issue

## CDN Performance Analysis

### CDN Provider Characteristics

**Akamai:**

- Largest CDN globally
- Netflix primary CDN
- Generally excellent performance
- Peak hour congestion possible in dense areas

**CloudFront (Amazon):**

- Integrated with AWS
- Prime Video, Twitch
- Very reliable, good geographic coverage
- Performance varies by region

**Google Global Cache:**

- YouTube exclusive effectively
- Excellent performance
- Very rarely has issues
- Massive infrastructure

**Fastly:**

- Used by Hulu, HBO Max, others
- Good performance generally
- Smaller than Akamai/CloudFront
- Occasional capacity issues

### CDN Quality Correlation

**Using this panel with Panel 3:**

1. **Identify CDN from this panel**
2. **Map to Panel 3 test target:**
   - Akamai → <www.netflix.com>
   - Google → <www.youtube.com>
   - CloudFront → <www.amazon.com>
3. **Check Panel 3 latency for that target**
4. **Correlate performance with usage**

**Example:**

- This panel: LG TV → Akamai (500 connections)
- Panel 3: <www.netflix.com> → 90ms (yellow/red)
- Conclusion: LG TV Netflix streaming affected by Akamai latency

## Files Referenced

- **Dashboard JSON:** `/Users/kirkl/src/network-monitoring/grafana-dashboards/streaming-monitor.json` (Panel ID 4)
- **Router DNS Daemon:** `/root/bin/dns-monitor-daemon.sh`
