# Network IP Addressing Schema - Clean Design

## Overview

**Network:** 192.168.1.0/24
**Router:** 192.168.1.1 (gateway) + 192.168.1.2 (LAN interface)
**DHCP Pool:** 192.168.1.51-254 (204 addresses)
**Static Range:** 192.168.1.1-50

---

## Design Constraints

### Immovable Devices (LOCKED)
| IP | Device | MAC | Type |
|----|--------|-----|------|
| .1 | Router Gateway | - | Infrastructure |
| .2 | Router LAN | - | Infrastructure |
| .15 | MarantzSR8012 | 00:05:CD:CA:FE:B4 | AV Equipment |
| .20 | SonyDVD | 00:06:76:21:53:ee | AV Equipment |

### Movable Devices
- **All eero devices** - can be reassigned to create clean consecutive blocks
- **WorkMac** - currently at .34, but using DHCP, can be removed from static

---

## Clean Schema Design

### Goals
✓ 5 consecutive IPs per eero (for ethernet ports, WiFi radios, mesh, future)
✓ 8 eero blocks (7 current + 1 future)
✓ Work around locked devices at .15 and .20
✓ Group infrastructure together

### Complete Allocation Map

```
192.168.1.1     Router Gateway (GLMT2500A)
192.168.1.2     Router LAN Interface (GLMT2500A)

─── Infrastructure Block (.3-.9) ───
192.168.1.3     Available for future infrastructure
192.168.1.4     Available for future infrastructure
192.168.1.5     Available for future infrastructure
192.168.1.6     Available for future infrastructure
192.168.1.7     Available for future infrastructure
192.168.1.8     Available for future infrastructure
192.168.1.9     Available for future infrastructure

─── eero-1 Block (.10-.14) ───
192.168.1.10    eero-1 Port 1     (20:be:cd:8f:10:60) [MOVE - was .10]
192.168.1.11    eero-1 Port 2     (20:be:cd:8f:10:61) [MOVE - was .11]
192.168.1.12    eero-1 WiFi Radio (20:be:cd:8f:10:72) [ADD - was .165]
192.168.1.13    eero-1 Reserved
192.168.1.14    eero-1 Reserved

192.168.1.15    MarantzSR8012 (00:05:CD:CA:FE:B4) [LOCKED]

─── Infrastructure Block (.16-.19) ───
192.168.1.16    Available for future infrastructure
192.168.1.17    Available for future infrastructure
192.168.1.18    Available for future infrastructure
192.168.1.19    Available for future infrastructure

192.168.1.20    SonyDVD (00:06:76:21:53:ee) [LOCKED]

─── eero-2-loft Block (.21-.25) ───
192.168.1.21    eero-2-loft Port 1 (9c:57:bc:14:1c:61) [MOVE - was .13]
192.168.1.22    eero-2-loft Port 2 (9c:57:bc:14:1c:60) [MOVE - was .14]
192.168.1.23    eero-2-loft WiFi   (9c:57:bc:14:1c:72) [ADD - was .61]
192.168.1.24    eero-2-loft Reserved
192.168.1.25    eero-2-loft Reserved

─── eero-3 Block (.26-.30) ───
192.168.1.26    eero-3 Main        (60:f4:19:42:af:12) [MOVE - was .16]
192.168.1.27    eero-3 Reserved
192.168.1.28    eero-3 Reserved
192.168.1.29    eero-3 Reserved
192.168.1.30    eero-3 Reserved

─── eero-4 Block (.31-.35) ───
192.168.1.31    eero-4 Main        (60:f4:19:44:39:92) [MOVE - was .19]
192.168.1.32    eero-4 Reserved
192.168.1.33    eero-4 Reserved
192.168.1.34    eero-4 Reserved
192.168.1.35    eero-4 Reserved

─── eero-5 Block (.36-.40) ───
192.168.1.36    eero-5 Main        (60:f4:19:57:4a:72) [MOVE - was .22]
192.168.1.37    eero-5 Reserved
192.168.1.38    eero-5 Reserved
192.168.1.39    eero-5 Reserved
192.168.1.40    eero-5 Reserved

─── eero-6 Block (.41-.45) ───
192.168.1.41    eero-6 Main        (9c:57:bc:13:6e:32) [MOVE - was .25]
192.168.1.42    eero-6 Reserved
192.168.1.43    eero-6 Reserved
192.168.1.44    eero-6 Reserved
192.168.1.45    eero-6 Reserved

─── eero-7 Block (.46-.50) ───
192.168.1.46    eero-7 Main        (9c:57:bc:07:80:32) [MOVE - was .28]
192.168.1.47    eero-7 Reserved
192.168.1.48    eero-7 Reserved
192.168.1.49    eero-7 Reserved
192.168.1.50    eero-7 Reserved

───────────────────────────────────
192.168.1.51-254    DHCP Pool (204 addresses)
```

---

## Changes Required

### Static Reservations to ADD

| MAC | New IP | Device | Action |
|-----|--------|--------|--------|
| 20:be:cd:8f:10:60 | 192.168.1.10 | eero-1-port1 | MOVE from .10 (no change) |
| 20:be:cd:8f:10:61 | 192.168.1.11 | eero-1-port2 | MOVE from .11 (no change) |
| 20:be:cd:8f:10:72 | 192.168.1.12 | eero-1-wifi | **ADD** (was .165 dynamic) |
| 9c:57:bc:14:1c:61 | 192.168.1.21 | eero-2-loft-port1 | **MOVE** from .13 |
| 9c:57:bc:14:1c:60 | 192.168.1.22 | eero-2-loft-port2 | **MOVE** from .14 |
| 9c:57:bc:14:1c:72 | 192.168.1.23 | eero-2-loft-wifi | **ADD** (was .61 dynamic) |
| 60:f4:19:42:af:12 | 192.168.1.26 | eero-3 | **MOVE** from .16 |
| 60:f4:19:44:39:92 | 192.168.1.31 | eero-4 | **MOVE** from .19 |
| 60:f4:19:57:4a:72 | 192.168.1.36 | eero-5 | **MOVE** from .22 |
| 9c:57:bc:13:6e:32 | 192.168.1.41 | eero-6 | **MOVE** from .25 |
| 9c:57:bc:07:80:32 | 192.168.1.46 | eero-7 | **MOVE** from .28 |

### Static Reservations to REMOVE

| MAC | Old IP | Device | Action |
|-----|--------|--------|--------|
| 72:4d:fd:65:22:41 | 192.168.1.34 | WorkMac | **REMOVE** (will get DHCP from pool) |

---

## Benefits of This Schema

### Clean Organization
- **eero-1**: All interfaces in .10-.14 ✓
- **eero-2-loft**: All interfaces in .21-.25 ✓
- **eero-3 through eero-7**: Consecutive 5-IP blocks ✓
- **Infrastructure**: Grouped in .3-.9 and .16-.19 (11 IPs available)

### Easy Troubleshooting
| IP Range | Device |
|----------|--------|
| .10-.14 | eero-1 |
| .21-.25 | eero-2-loft |
| .26-.30 | eero-3 |
| .31-.35 | eero-4 |
| .36-.40 | eero-5 |
| .41-.45 | eero-6 |
| .46-.50 | eero-7 |

See an IP like .23? It's eero-2-loft.
See an IP like .38? It's eero-5.

### Room for Growth
- **eero-8**: Can use .3-.7 or another infrastructure block when needed
- **New eero interfaces**: Each eero has 2-4 reserved IPs for future discovery
- **Infrastructure**: 11 available IPs (.3-.9, .16-.19)

### Why This Works Around the Constraints
- MarantzSR8012 at .15 sits between infrastructure and eeros
- SonyDVD at .20 sits between infrastructure and eeros
- We use .16-.19 as additional infrastructure space (the "gap" created by Sony)

---

## Current eero Inventory

| eero | Location | Base MAC | Active Interfaces | New IP Range |
|------|----------|----------|-------------------|--------------|
| eero-1 | Unknown | 20:be:cd:8f:10:xx | 3 (2 ports + WiFi) | .10-.14 |
| eero-2-loft | Loft | 9c:57:bc:14:1c:xx | 3 (2 ports + WiFi) | .21-.25 |
| eero-3 | Unknown | 60:f4:19:42:af:12 | 1 (Main) | .26-.30 |
| eero-4 | Unknown | 60:f4:19:44:39:92 | 1 (Main) | .31-.35 |
| eero-5 | Unknown | 60:f4:19:57:4a:72 | 1 (Main) | .36-.40 |
| eero-6 | Unknown | 9c:57:bc:13:6e:32 | 1 (Main) | .41-.45 |
| eero-7 | Unknown | 9c:57:bc:07:80:32 | 1 (Main) | .46-.50 |

---

## Implementation Impact

### During Transition
- Brief service interruption as devices renew DHCP leases with new IPs
- Each eero will reconnect automatically (30-60 seconds)
- WorkMac laptop will get new IP from DHCP pool automatically

### After Implementation
- All eero interfaces will have static IPs in <50 range
- Clean, organized addressing scheme
- No more dynamic eero IPs outside expected range
- Easy to add future interfaces or 8th eero

---

## Quick Reference

```
Router:             .1-.2     (2 IPs)
Infrastructure:     .3-.9     (7 IPs available)
eero-1:            .10-.14   (5 IPs) ← Currently has 3 active
Marantz (LOCKED):   .15       (1 IP)
Infrastructure:     .16-.19   (4 IPs available)
Sony (LOCKED):      .20       (1 IP)
eero-2-loft:       .21-.25   (5 IPs) ← Currently has 3 active
eero-3:            .26-.30   (5 IPs) ← Currently has 1 active
eero-4:            .31-.35   (5 IPs) ← Currently has 1 active
eero-5:            .36-.40   (5 IPs) ← Currently has 1 active
eero-6:            .41-.45   (5 IPs) ← Currently has 1 active
eero-7:            .46-.50   (5 IPs) ← Currently has 1 active
DHCP Pool:         .51-.254  (204 IPs)
```

**Total Capacity:**
- 7 eero blocks configured (35 IPs allocated, ~13 active)
- 11 infrastructure IPs available
- Room for 8th eero (can use infrastructure block)
- 2 locked AV devices integrated cleanly
