# Feature: Dynamic Streaming Device Detection

## Problem Statement

### Current Implementation
The `streaming-ping-orchestrator.py` script uses **hard-coded IP addresses** to identify streaming devices:

```python
STREAMING_DEVICES = ["192.168.1.70", "192.168.1.95", "192.168.1.109"]
```

### Issues with Hard-Coded IPs

1. **IP addresses can change** - These are in DHCP pool (.51-.254), not static reservations
2. **Wrong device mappings** - IP .109 currently has a Wyze Camera, not an Apple TV
3. **Incomplete device coverage** - Missing multiple streaming devices:
   - Apple TV "Loft"
   - Apple TV "Downstairs"
   - Sony DVD upstairs
   - Roku TV (43TCLRokuTV)
   - LG TV (LGwebOSTV)
4. **Maintenance burden** - Must manually update script when devices change IPs
5. **Poor scalability** - Adding new streaming devices requires code changes

### User's Streaming Device Inventory

| Device Type | Name/Location | Current Status | Notes |
|-------------|---------------|----------------|-------|
| Apple TV | Loft | Unknown IP | Need to identify |
| Apple TV | Downstairs | Unknown IP | Need to identify |
| Sony DVD | Downstairs | Static IP .20 | Has static reservation |
| Sony DVD | Upstairs | Unknown IP | Need to identify |
| Roku TV | Bedroom? | Was .95? | 43TCLRokuTV |
| LG TV | Living Room | Static IP .70 | LGwebOSTV - has reservation |

---

## Solution: Dynamic Device Detection

### High-Level Approach

**Query InfluxDB for devices matching streaming capability patterns, then monitor their bandwidth.**

**Benefits:**
- ✅ No hard-coded IP addresses
- ✅ Automatically discovers new streaming devices
- ✅ Resilient to IP changes
- ✅ Uses existing infrastructure (InfluxDB, device registry)
- ✅ No additional router queries needed
- ✅ Works with device naming conventions

---

## Technical Design

### Option A: Query by Device Name Pattern (Recommended)

**Concept:** Query InfluxDB's `dhcp_lease` measurement for devices matching streaming device patterns.

**Device Name Patterns:**
- Contains "Apple TV" or "AppleTV"
- Contains "Roku"
- Contains "LG" and "TV"
- Contains "Sony DVD"
- Explicitly listed in configuration (for edge cases)

**Implementation Flow:**

```
┌─────────────────────────────────────────────────────────┐
│ 1. Query InfluxDB for Active Streaming Devices         │
│    - Search dhcp_lease measurement (last 2 minutes)    │
│    - Filter by device_name patterns                    │
│    - Extract: device_name, ip, mac                     │
│    - Cache results for 60s (DHCP collection interval)  │
└─────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────┐
│ 2. Query Bandwidth for Discovered Devices              │
│    - Use IPs from step 1                               │
│    - Check bandwidth in last 60s                       │
│    - Threshold: >1 MB = streaming active               │
└─────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────┐
│ 3. If Streaming Detected: Ping CDNs                    │
│    - Netflix, YouTube, Amazon, Cloudflare              │
│    - Output metrics to InfluxDB                        │
└─────────────────────────────────────────────────────────┘
```

### InfluxDB Query Strategy

**Step 1: Discover Streaming Devices**

```python
query = f'''
from(bucket: "{INFLUXDB_BUCKET}")
  |> range(start: -2m)
  |> filter(fn: (r) => r._measurement == "dhcp_lease")
  |> filter(fn: (r) =>
      r.device_name =~ /(?i)apple.?tv/ or
      r.device_name =~ /(?i)roku/ or
      r.device_name =~ /(?i)lg.*tv/ or
      r.device_name =~ /(?i)sony.*dvd/
  )
  |> last()
  |> group()
  |> keep(columns: ["device_name", "ip", "mac"])
'''
```

**Returns:**
```
[
  {device_name: "Loft Apple TV", ip: "192.168.1.108", mac: "xx:xx:xx"},
  {device_name: "Downstairs Apple TV", ip: "192.168.1.110", mac: "yy:yy:yy"},
  {device_name: "43TCLRokuTV", ip: "192.168.1.94", mac: "zz:zz:zz"},
  {device_name: "LGwebOSTV", ip: "192.168.1.70", mac: "aa:aa:aa"},
  ...
]
```

**Step 2: Check Bandwidth for These Devices**

```python
# Build dynamic IP list from step 1
device_ips = [device['ip'] for device in discovered_devices]
device_filter = " or ".join([f'r.ip == "{ip}"' for ip in device_ips])

query = f'''
from(bucket: "{INFLUXDB_BUCKET}")
  |> range(start: -60s)
  |> filter(fn: (r) =>
      r._measurement == "bandwidth" and
      r.direction == "rx" and
      ({device_filter})
  )
  |> aggregateWindow(every: 60s, fn: sum, createEmpty: false)
  |> filter(fn: (r) => r._value > {BANDWIDTH_THRESHOLD})
  |> count()
'''
```

---

## Implementation Plan

### Phase 1: Configuration-Based Discovery

**Changes to `streaming-ping-orchestrator.py`:**

1. **Add device pattern configuration** (lines 38-50):

```python
# Streaming device detection patterns
STREAMING_DEVICE_PATTERNS = [
    "apple.*tv",      # Matches: "Apple TV", "AppleTV", "apple-tv"
    "roku",           # Matches: "Roku", "RokuTV", "TCLRoku"
    "lg.*tv",         # Matches: "LG TV", "LGwebOSTV", "LG-TV"
    "sony.*dvd",      # Matches: "Sony DVD", "SonyDVD"
]

# Optional: Explicit device name list (overrides patterns)
EXPLICIT_STREAMING_DEVICES = [
    # "Custom Device Name",  # Add devices that don't match patterns
]

# Cache duration for device discovery (should match DHCP collection interval)
DEVICE_CACHE_TTL = 60  # seconds
```

2. **Add device discovery function**:

```python
def discover_streaming_devices(client):
    """
    Query InfluxDB to discover streaming devices by name pattern.

    Returns:
        list: List of dicts with keys: device_name, ip, mac
    """
    # Build Flux regex pattern from STREAMING_DEVICE_PATTERNS
    pattern_conditions = " or ".join([
        f'r.device_name =~ /(?i){pattern}/'
        for pattern in STREAMING_DEVICE_PATTERNS
    ])

    # Add explicit devices if configured
    if EXPLICIT_STREAMING_DEVICES:
        explicit_conditions = " or ".join([
            f'r.device_name == "{name}"'
            for name in EXPLICIT_STREAMING_DEVICES
        ])
        pattern_conditions = f"({pattern_conditions}) or ({explicit_conditions})"

    query = f'''
    from(bucket: "{INFLUXDB_BUCKET}")
      |> range(start: -2m)
      |> filter(fn: (r) => r._measurement == "dhcp_lease")
      |> filter(fn: (r) => {pattern_conditions})
      |> last()
      |> group()
      |> keep(columns: ["device_name", "ip", "mac"])
    '''

    try:
        result = client.query_api().query(query, org=INFLUXDB_ORG)
        devices = []
        for table in result:
            for record in table.records:
                devices.append({
                    'device_name': record.values.get('device_name', 'Unknown'),
                    'ip': record.values.get('ip', ''),
                    'mac': record.values.get('mac', '')
                })

        sys.stderr.write(f"INFO: Discovered {len(devices)} streaming devices\n")
        for device in devices:
            sys.stderr.write(f"  - {device['device_name']} @ {device['ip']}\n")

        return devices
    except Exception as e:
        sys.stderr.write(f"ERROR: Failed to discover streaming devices: {e}\n")
        return []
```

3. **Add caching mechanism**:

```python
import time

# Global cache
_device_cache = {
    'devices': [],
    'timestamp': 0
}

def get_streaming_devices(client):
    """
    Get streaming devices with caching.

    Returns:
        list: Cached or freshly discovered devices
    """
    global _device_cache
    current_time = time.time()

    # Check if cache is still valid
    if (current_time - _device_cache['timestamp']) < DEVICE_CACHE_TTL:
        sys.stderr.write(f"INFO: Using cached device list ({len(_device_cache['devices'])} devices)\n")
        return _device_cache['devices']

    # Cache expired, refresh
    devices = discover_streaming_devices(client)
    _device_cache['devices'] = devices
    _device_cache['timestamp'] = current_time

    return devices
```

4. **Update `is_streaming_active()` function** to use dynamic devices:

```python
def is_streaming_active(client):
    """
    Query InfluxDB to determine if any streaming device has >1 Mbps bandwidth.
    Uses dynamic device discovery instead of hard-coded IPs.

    Returns:
        bool: True if streaming detected, False otherwise
    """
    # Get current streaming devices (cached)
    devices = get_streaming_devices(client)

    if not devices:
        sys.stderr.write("INFO: No streaming devices discovered, skipping bandwidth check\n")
        return False

    # Build filter for discovered device IPs
    device_ips = [d['ip'] for d in devices if d['ip']]
    if not device_ips:
        sys.stderr.write("WARN: Discovered devices have no IPs\n")
        return False

    device_filter = " or ".join([f'r.ip == "{ip}"' for ip in device_ips])

    # Query bandwidth (unchanged from original)
    query = f'''
    from(bucket: "{INFLUXDB_BUCKET}")
      |> range(start: -60s)
      |> filter(fn: (r) =>
          r._measurement == "bandwidth" and
          r.direction == "rx" and
          ({device_filter})
      )
      |> aggregateWindow(every: 60s, fn: sum, createEmpty: false)
      |> filter(fn: (r) => r._value > {BANDWIDTH_THRESHOLD})
      |> count()
    '''

    # Rest of function unchanged...
```

5. **Update main loop** to show discovered devices:

```python
def main():
    # ... existing setup code ...

    sys.stderr.write("═══════════════════════════════════════════\n")
    sys.stderr.write("Opportunistic CDN Ping Orchestrator Started\n")
    sys.stderr.write("═══════════════════════════════════════════\n")
    sys.stderr.write(f"Check interval: {CHECK_INTERVAL}s\n")
    sys.stderr.write(f"Bandwidth threshold: {BANDWIDTH_THRESHOLD:,} bytes\n")
    sys.stderr.write(f"Device cache TTL: {DEVICE_CACHE_TTL}s\n")
    sys.stderr.write(f"Streaming device patterns: {STREAMING_DEVICE_PATTERNS}\n")
    sys.stderr.write("═══════════════════════════════════════════\n\n")

    # Rest of main loop unchanged...
```

### Phase 2: Device Registry Enhancement (Optional Future Work)

**Goal:** Enrich device names in InfluxDB using the manual device registry.

**Approach:**
1. Modify `dhcp.py` collector to call `/root/bin/resolve-device-name.sh`
2. Store enriched names in `device_name` tag
3. No changes needed to orchestrator (already uses `device_name`)

**Implementation:**
```python
# In dhcp.py collector
def _enrich_device_names(self, leases):
    """Call router's resolve-device-name.sh for friendly names"""
    for lease in leases:
        ip = lease.get('ip')
        mac = lease.get('mac')
        result = self.connection.execute(
            f"/root/bin/resolve-device-name.sh '{ip}' '{mac}'"
        )
        lease['device_name'] = result.strip() or lease['hostname']
    return leases
```

**Benefits:**
- Streaming devices get friendly names like "Loft Apple TV"
- Pattern matching becomes more accurate
- No hard-coded IPs anywhere in system

---

## Configuration Examples

### Minimal Configuration (Use Patterns Only)

```python
# Auto-discovers: Apple TVs, Roku, LG TV, Sony DVDs
STREAMING_DEVICE_PATTERNS = [
    "apple.*tv",
    "roku",
    "lg.*tv",
    "sony.*dvd",
]
EXPLICIT_STREAMING_DEVICES = []
```

### Enhanced Configuration (Add Explicit Devices)

```python
# Patterns plus specific devices
STREAMING_DEVICE_PATTERNS = [
    "apple.*tv",
    "roku",
    "lg.*tv",
    "sony.*dvd",
]

EXPLICIT_STREAMING_DEVICES = [
    "Loft Apple TV",           # From device registry
    "Downstairs Apple TV",     # From device registry
    "Living Room LG TV",       # If renamed in registry
]
```

### Exclusion Support (Future Enhancement)

```python
# Exclude specific devices from detection
EXCLUDE_PATTERNS = [
    "wyze",    # Wyze cameras not streaming devices
    "ring",    # Ring cameras not streaming devices
]
```

---

## Testing Strategy

### Unit Tests

**Test device pattern matching:**
```python
def test_device_patterns():
    test_cases = [
        ("Apple TV", True),
        ("apple-tv-loft", True),
        ("AppleTV", True),
        ("RokuTV", True),
        ("43TCLRokuTV", True),
        ("LGwebOSTV", True),
        ("Sony DVD Player", True),
        ("Wyze Camera", False),
        ("iPhone", False),
    ]
    # ... assert pattern matches
```

**Test caching logic:**
```python
def test_device_cache():
    # First call should query InfluxDB
    devices1 = get_streaming_devices(client)

    # Second call within TTL should use cache
    devices2 = get_streaming_devices(client)
    assert devices1 == devices2

    # After TTL expires, should refresh
    time.sleep(DEVICE_CACHE_TTL + 1)
    devices3 = get_streaming_devices(client)
    # Should have queried InfluxDB again
```

### Integration Tests

**Test with real InfluxDB:**
1. Insert test DHCP lease data with known device names
2. Run `discover_streaming_devices()`
3. Verify correct devices are discovered
4. Verify IPs are correctly extracted

**Test bandwidth detection:**
1. Insert bandwidth data for discovered devices
2. Verify streaming detection triggers correctly
3. Verify CDN pings are initiated

### Manual Verification

**After deployment:**
```bash
# Watch orchestrator logs
docker logs -f telegraf 2>&1 | grep -E "Discovered|streaming"

# Should see:
# INFO: Discovered 5 streaming devices
#   - Loft Apple TV @ 192.168.1.108
#   - Downstairs Apple TV @ 192.168.1.110
#   - 43TCLRokuTV @ 192.168.1.94
#   - LGwebOSTV @ 192.168.1.70
#   - Sony DVD @ 192.168.1.20
# INFO: Streaming detected from 2 devices
```

---

## Migration Path

### Step 1: Update Device Registry (Manual - On Router)

**Ensure all streaming devices have friendly names:**

```bash
ssh root@192.168.1.2
vi /root/etc/device-registry.conf

# Add entries for streaming devices:
XX:XX:XX:XX:XX:XX=Loft Apple TV
YY:YY:YY:YY:YY:YY=Downstairs Apple TV
ZZ:ZZ:ZZ:ZZ:ZZ:ZZ=Upstairs Sony DVD
# (LG TV and Roku already have names from DHCP hostname)
```

### Step 2: Deploy Updated Orchestrator

```bash
cd ~/src/network-monitoring

# Update streaming-ping-orchestrator.py with changes above

# Restart Telegraf to load new script
docker-compose restart telegraf

# Verify it's working
docker logs -f telegraf 2>&1 | grep "Discovered"
```

### Step 3: Verify Device Discovery

```bash
# Check if devices are being discovered correctly
docker logs telegraf 2>&1 | grep -A 10 "Discovered"

# Expected output:
# INFO: Discovered 5 streaming devices
#   - Loft Apple TV @ 192.168.1.108
#   - Downstairs Apple TV @ 192.168.1.110
#   ...
```

### Step 4: Monitor for Issues

**Watch for:**
- Devices not being discovered (pattern mismatch)
- Wrong devices being classified as streaming
- Cache not updating (stuck with old IPs)

**Troubleshooting:**
```bash
# Force cache refresh by restarting Telegraf
docker-compose restart telegraf

# Check DHCP lease data in InfluxDB
docker exec -it influxdb influx query 'from(bucket: "network") |> range(start: -5m) |> filter(fn: (r) => r._measurement == "dhcp_lease") |> last()'
```

---

## Success Metrics

### Functional Metrics
- ✅ All 5+ streaming devices automatically discovered
- ✅ Streaming detection works without hard-coded IPs
- ✅ Device IP changes don't break detection
- ✅ New streaming devices automatically included

### Performance Metrics
- ✅ Device discovery query < 500ms
- ✅ Bandwidth query performance unchanged
- ✅ Cache hit rate > 90% (avoids redundant queries)
- ✅ No increase in InfluxDB query load

### Operational Metrics
- ✅ Zero manual IP updates needed over 30 days
- ✅ No false positives (non-streaming devices triggering CDN pings)
- ✅ No false negatives (streaming devices not detected)

---

## Future Enhancements

### 1. Configurable Patterns via Environment Variables

```bash
# In docker-compose.yml
environment:
  - STREAMING_PATTERNS=apple.*tv,roku,lg.*tv,sony.*dvd
  - STREAMING_EXPLICIT=Loft Apple TV,Custom Device
```

### 2. Adaptive Bandwidth Threshold

```python
# Different thresholds for different device types
DEVICE_THRESHOLDS = {
    "apple.*tv": 2_000_000,    # 4K streaming needs more
    "roku": 1_000_000,          # HD streaming
    "lg.*tv": 1_500_000,        # Smart TV apps
}
```

### 3. Device Activity Tracking

```python
# Track when each device was last seen streaming
streaming_activity,device_name=Loft_Apple_TV,ip=192.168.1.108 last_active=<timestamp>,total_sessions=42i
```

### 4. Smart TV App Detection

```python
# Detect which app is streaming based on DNS queries
# Correlate bandwidth + DNS to identify Netflix vs YouTube vs Amazon
```

### 5. Multi-Device Streaming

```python
# If multiple devices streaming, prioritize CDN pings to active services
# E.g., if Apple TV streaming Netflix, ping Netflix CDN more frequently
```

---

## Rollback Plan

If dynamic detection causes issues:

1. **Revert to hard-coded IPs** (temporary):
   ```bash
   git revert <commit-hash>
   docker-compose restart telegraf
   ```

2. **Fix device registry** (if names incorrect):
   ```bash
   ssh root@192.168.1.2
   vi /root/etc/device-registry.conf
   # Correct device names to match patterns
   ```

3. **Add explicit device list** (if patterns too broad):
   ```python
   # Disable patterns, use explicit list only
   STREAMING_DEVICE_PATTERNS = []
   EXPLICIT_STREAMING_DEVICES = [
       "Exact Device Name 1",
       "Exact Device Name 2",
   ]
   ```

---

## Files to Modify

| File | Changes | Lines |
|------|---------|-------|
| `scripts/streaming-ping-orchestrator.py` | Replace hard-coded IPs with dynamic discovery | ~150 new lines |
| `docker-compose.yml` | Add optional environment variables for patterns | ~5 lines |
| `docs/DATA-COLLECTION-METHODS.md` | Document dynamic device detection method | ~30 lines |

**Total estimated changes:** ~200 lines of code

---

## Implementation Effort

| Phase | Effort | Priority |
|-------|--------|----------|
| Update orchestrator script | 2-3 hours | HIGH |
| Test with real devices | 1 hour | HIGH |
| Update device registry on router | 30 mins | HIGH |
| Deploy and verify | 30 mins | HIGH |
| Documentation updates | 1 hour | MEDIUM |
| Future enhancements | 4-6 hours | LOW |

**Total: 5-6 hours for core functionality**

---

## Approval

Once this feature plan is approved, implementation will proceed in the following order:

1. ✅ Update `streaming-ping-orchestrator.py` with dynamic device discovery
2. ✅ Add device name patterns configuration
3. ✅ Implement caching mechanism
4. ✅ Test device discovery with current InfluxDB data
5. ✅ Update device registry on router for friendly names
6. ✅ Deploy to production
7. ✅ Monitor and verify correct operation
8. ✅ Update documentation

**Ready for implementation: YES** ✓
