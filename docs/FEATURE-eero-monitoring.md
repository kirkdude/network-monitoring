# eero Mesh WiFi Monitoring

**Status:** Future Work
**Priority:** Medium
**Dependencies:** Router health monitoring, DNS visibility

## Overview

Monitor 7 eero routers creating the home WiFi mesh network.

## eero Architecture

- **Total eero nodes:** 7 routers in mesh configuration
- **ARP addresses per eero:** 5 addresses each
  - 2 for physical Ethernet ports
  - 3 for WiFi interfaces (2.4GHz, 5GHz, 6GHz or client/backhaul radios)
- **IP reservations:** IPs < 50 are reserved for eero routers (192.168.1.1-49)
- **Total ARP entries:** 35 addresses (7 routers × 5 addresses)
- Look into using https://github.com/343max/eero-client

## Monitoring Goals

1. Node online/offline status (all 7 nodes)
2. Client connections per node
3. Mesh backhaul health (connection quality between nodes)
4. DHCP assignments (each eero should have static IP < 50)

## Implementation Approaches

### Approach 1: Network-Based Inference (Recommended First)

**Pros:**
- No external dependencies
- No cloud authentication required
- Simple to implement
- Works even if eero API changes

**Cons:**
- Limited visibility (ping only shows up/down)
- Cannot see client-per-node associations
- Cannot measure mesh backhaul quality directly
- Must infer issues from symptoms

**Implementation:**

1. **Discover eero IPs:**
```bash
ssh root@192.168.1.2
cat /tmp/dhcp.leases | awk '$3 < 50' | sort -t. -k4 -n
uci show dhcp | grep -E "dhcp.@host.*\.mac|dhcp.@host.*\.ip"
```

2. **Add to telegraf.conf:**
```toml
[[inputs.ping]]
  interval = "30s"
  urls = [
    "192.168.1.X",  # eero node 1 - discover actual IPs
    "192.168.1.Y",  # eero node 2
    # ... all 7 nodes
  ]
  count = 3
  [inputs.ping.tags]
    type = "eero_mesh"
```

3. **Infer health from patterns:**
- Online/offline: ping response
- Backhaul issues: latency spikes
- Client distribution: DHCP lease analysis + bandwidth patterns

### Approach 2: eero Cloud API (For Detailed Metrics)

**Pros:**
- Exact client counts per node
- Mesh backhaul signal quality (RSSI)
- Official eero network view
- Node firmware versions
- Historical speed tests

**Cons:**
- Requires eero account credentials
- Unofficial API (may break with updates)
- Cloud dependency
- Rate limited
- More complex implementation

**Implementation:**
```python
# scripts/eero-collector.py
from pyeero import Eero

eero = Eero(session)
eero.login('email', 'password')

network = eero.networks[0]
devices = network.devices  # All 7 eero nodes
clients = network.clients  # All connected clients

for device in devices:
    print(f"eero_status,node_id={device.serial} online={1 if device.online else 0}i")
    print(f"eero_clients,node_id={device.serial} count={len(device.clients)}i")
    print(f"eero_backhaul,node_id={device.serial} rssi={device.backhaul_rssi}i")
```

**Required:**
- eero account with admin access
- Python library: `pyeero` (unofficial)
- Store credentials securely

## Dashboard Requirements

**Grafana Panel: eero Mesh Health**
- 7 status indicators (green/red for each node)
- Ping latency graph (identify backhaul issues)
- Client count per node (if API available)
- Mesh topology visualization

## Implementation Steps

1. **Phase 1: Discovery (30 min)**
   - Identify 7 eero primary IPs
   - Document physical locations
   - Map IPs to locations

2. **Phase 2: Basic Monitoring (1 hour)**
   - Add ping monitoring for all 7 nodes
   - Create dashboard panel
   - Test for 24 hours

3. **Phase 3: API Integration (Optional, 2-3 hours)**
   - Set up eero account API access
   - Implement Python collector script
   - Add detailed metrics to dashboard
   - Test for 1 week

4. **Phase 4: Alerting (1 hour)**
   - Alert on node offline
   - Alert on high latency (backhaul degradation)
   - Alert on client distribution anomalies

## Open Questions

1. What are the 7 primary IPs assigned to eero nodes?
2. What are the physical locations (for labeling)?
3. Is ping-based monitoring sufficient, or needed API detail?
4. Do we need client-per-node tracking?
5. Do we have eero account credentials for API access?

## Success Criteria

- ✅ All 7 eero nodes visible in dashboard
- ✅ Real-time online/offline status
- ✅ Latency tracking shows backhaul health
- ✅ Alerts fire when node goes offline
- ✅ Dashboard shows which node serves which area
- ⚠️ (Optional) Client count per node visible
- ⚠️ (Optional) Mesh backhaul signal strength visible
