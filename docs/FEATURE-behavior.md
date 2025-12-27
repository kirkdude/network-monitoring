# Feature: Device Behavior-Based Anomaly Detection

## Overview

Monitor network behavior by device type with type-specific thresholds for anomaly detection.

## Problem Statement

Different device types have different "normal" behavior patterns:

- IoT devices uploading 5 Mbps = 🚨 **High alert** (likely compromised/botnet)
- Workstation uploading 50 Mbps = ⚠️ **Medium alert** (could be legitimate backup)
- Streaming device downloading 500 Mbps = ✅ **Normal** (4K streaming)

Generic thresholds across all devices create:

- **False negatives:** Compromised IoT device uploading 10 Mbps looks "normal" compared to workstations
- **False positives:** Legitimate high-bandwidth devices trigger alerts

## Proposed Solution

### Device Type Registry

Extend `/root/etc/device-registry.conf` with device types:

```conf
# Format: MAC|IP|Name|Type
a8:23:fe:2c:58:c5|192.168.1.70|LGwebOSTV|streaming
2c:aa:8e:1e:88:59|192.168.1.203|WyzeCam|iot
ea:2b:7b:22:74:9c|192.168.1.124|Macmini|workstation
```

**Device Types:**

- `iot` - IoT devices (cameras, sensors, smart home)
- `mobile` - Phones, tablets
- `workstation` - Computers, laptops
- `streaming` - TVs, Apple TV, gaming consoles
- `network` - Routers, switches, access points
- `server` - NAS, home servers
- `unknown` - Unclassified devices

### Behavior Thresholds by Type

**Upload Thresholds (Mbps):**

```
Type          | Normal  | Warning | Critical | Rationale
------------- | ------- | ------- | -------- | ---------
iot           | < 1     | 1-5     | > 5      | Should barely upload
mobile        | < 10    | 10-25   | > 25     | Photos/backups acceptable
workstation   | < 25    | 25-50   | > 50     | Cloud sync, backups
streaming     | < 5     | 5-15    | > 15     | Upstream for calls only
network       | < 50    | 50-100  | > 100    | Management traffic
server        | < 100   | 100-500 | > 500    | Legitimate if hosting
unknown       | < 5     | 5-10    | > 10     | Treat as suspicious
```

**Download Thresholds (Mbps):**

```
Type          | Normal   | Warning  | Critical | Rationale
------------- | -------- | -------- | -------- | ---------
iot           | < 10     | 10-50    | > 50     | Updates only
mobile        | < 100    | 100-300  | > 300    | Video streaming
workstation   | < 300    | 300-500  | > 500    | Heavy usage
streaming     | < 500    | 500-1000 | > 1000   | 4K/8K streaming
network       | < 100    | 100-300  | > 300    | Firmware/logs
server        | < 1000   | varies   | varies   | Context-dependent
unknown       | < 10     | 10-50    | > 50     | Treat as suspicious
```

**Upload/Download Ratio Thresholds:**

```
Type          | Normal  | Suspicious | Critical
------------- | ------- | ---------- | --------
iot           | < 0.1   | 0.1-0.5    | > 0.5
mobile        | < 0.3   | 0.3-0.7    | > 0.7
workstation   | < 0.4   | 0.4-0.8    | > 0.8
streaming     | < 0.1   | 0.1-0.3    | > 0.3
server        | varies  | varies     | varies
```

## Dashboard Panels

### New Dashboard: "Device Behavior Analysis"

**Panel 1: Behavior Violations by Severity**

- Table showing devices violating their type-specific thresholds
- Columns: Device, Type, Current Upload, Threshold, Severity, Duration
- Sorted by severity (Critical > Warning > Normal)
- Color-coded rows

**Panel 2: IoT Upload Activity (High Priority)**

- Time series of ALL IoT device uploads
- Horizontal threshold line at 5 Mbps (critical)
- Any spike above threshold = immediate investigation
- Because: IoT should NEVER upload significantly

**Panel 3: Upload/Download Ratio Anomalies**

- Devices with unusual upload ratios for their type
- Scatter plot: X=download, Y=upload, colored by type
- Type-specific "normal zones" shaded
- Outliers are potential threats

**Panel 4: Type-Based Bandwidth Distribution**

- Stacked area chart showing bandwidth by device type over time
- Quickly see if IoT traffic is growing (bad sign)
- Normal pattern: streaming >> workstation >> mobile >> IoT

**Panel 5: Unknown Device Activity**

- All "unknown" type devices with any significant traffic
- Forces classification: either add to registry or isolate
- Security: unknowns are threats until proven otherwise

**Panel 6: Behavior Change Detection**

- Devices whose current behavior deviates from 7-day baseline
- Example: IoT camera uploading 2 Mbps when 7-day avg is 0.1 Mbps
- Percentage deviation + absolute change

## Implementation Steps

1. **Phase 1:** Add device types to registry (manual classification of 100 devices)
2. **Phase 2:** Modify export scripts to include device_type tag in InfluxDB
3. **Phase 3:** Create new dashboard with behavior panels
4. **Phase 4:** Add alerting rules for critical violations (Grafana alerts)

## Future Enhancements

- **Auto-classification:** Use ML to suggest device types based on traffic patterns
- **Baseline learning:** Automatically establish per-device normal ranges
- **Threat intelligence:** Compare domains accessed by device type (IoT accessing pastebin = bad)
- **Temporal analysis:** Flag off-hours activity by device type (IoT at 3 AM = suspicious)

---

**Status:** 📋 **Planned** - Placeholder for future implementation
**Priority:** High (security visibility gap)
**Estimated Effort:** 2-3 days (registry classification + dashboard + testing)
