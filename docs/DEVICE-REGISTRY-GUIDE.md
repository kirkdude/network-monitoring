# Device Name Registry Guide

## Overview

Your network monitoring system uses a hybrid device identification approach:
- **Manual names** for devices you care about (Living Room TV, Kirks Laptop)
- **Automatic names** for everything else (Hostname + Vendor, or fallback to MAC)

---

## Adding Custom Device Names

### Quick Steps

1. **SSH to router:**
   ```bash
   ssh root@192.168.1.2
   ```

2. **Edit device registry:**
   ```bash
   vi /root/etc/device-registry.conf
   ```

3. **Add device entries** (format: `MAC=Name`):
   ```
   a8:23:fe:2c:58:c5=Living Room LG TV
   80:f5:05:xx:xx:xx=Kirks Apple TV
   0a:1d:54:8f:c5:02=Kirks iPhone 15
   ```

4. **Save and exit:**
   - Press `ESC`
   - Type `:wq`
   - Press `ENTER`

5. **Wait 30 seconds** for next Prometheus scrape

6. **Check Grafana dashboard** - device should show new name

---

## Finding MAC Addresses

### Method 1: From Router

```bash
ssh root@192.168.1.2 "cat /tmp/dhcp.leases"
```

**Output format:**
```
timestamp MAC_ADDRESS IP_ADDRESS HOSTNAME client-id
1766215920 a8:23:fe:2c:58:c5 192.168.1.70 LGwebOSTV ...
```

### Method 2: From Grafana

1. Open "All Devices Table" dashboard
2. Find the device in the table
3. Note the MAC Address column

### Method 3: From Daily Report

Check the generated report at:
`~/network-monitoring/reports/client-activity-YYYY-MM-DD.md`

---

## Device Name Hierarchy

The system uses this priority order to name devices:

**1. Manual Registry** (Highest Priority)
- File: `/root/etc/device-registry.conf`
- Format: `MAC=Custom Name`
- Example: `a8:23:fe:2c:58:c5=Living Room LG TV`

**2. Hostname + Vendor**
- Hostname from DHCP lease
- Vendor from OUI lookup
- Example: `LGwebOSTV (LG Electronics)`

**3. Hostname Only**
- When vendor not in OUI database
- Example: `iPhone`, `Macmini`

**4. Vendor Only**
- When no hostname announced
- Example: `Apple Inc.`

**5. MAC Address** (Last Resort)
- When no other data available
- Example: `a0:66:2b`

---

## Current Device Names

Based on your latest scan, here are some devices you might want to manually name:

| Current Name | IP | MAC | Suggested Manual Name |
|--------------|----|----|---------------------|
| MD-DS3PDC4 (Apple Inc.) | 192.168.1.109 | 80:f5:05 | Living Room Apple TV |
| LGwebOSTV (LG Electronics) | 192.168.1.70 | a8:23:fe:2c:58:c5 | Living Room LG TV |
| WYZECP1_JEF-2CAA8E2FFE41 | 192.168.1.243 | 2f:fe:41 | Backyard Wyze Cam |
| NarwalRobotics | 192.168.1.170 | 6f:be:0a | Robot Vacuum |
| Tonal-080300900067727 | 192.168.1.200 | 01:c6:3a | Gym Tonal |
| 43TCLRokuTV | 192.168.1.95 | bb:7a:53 | Bedroom Roku TV |
| bosch-dishwasher-... | 192.168.1.235 | 68:23:0f | Kitchen Dishwasher |

---

## Editing Tips

### Adding Multiple Devices

```bash
# /root/etc/device-registry.conf
80:f5:05:xx:xx:xx=Living Room Apple TV
a8:23:fe:2c:58:c5=Living Room LG TV
0a:1d:54:8f:c5:02=Kirks iPhone 15
ea:2b:7b:22:74:9c=Mac Mini Server
6f:be:0a:xx:xx:xx=Robot Vacuum
01:c6:3a:xx:xx:xx=Gym Tonal
bb:7a:53:xx:xx:xx=Bedroom Roku TV
```

### Naming Conventions

**Recommended format:**
- `Location Device Type` - e.g., "Living Room Apple TV"
- `Owner's Device` - e.g., "Kirks iPhone"
- `Function` - e.g., "Guest WiFi"

**Avoid:**
- Very long names (> 50 characters)
- Special characters: `"`, `\`, newlines
- Duplicate names (each device should be unique)

---

## Verification

### Check Device Name is Applied

1. **From router:**
   ```bash
   ssh root@192.168.1.2 "/root/bin/resolve-device-name.sh '192.168.1.70' 'a8:23:fe:2c:58:c5'"
   ```
   Should output: `Living Room LG TV` (if you added it)

2. **From Prometheus:**
   ```bash
   curl http://192.168.1.2:9100/metrics | grep 'device_name="Living Room LG TV"'
   ```

3. **From Grafana:**
   - Open: http://localhost:3000/d/14cf33bf-29ea-41cd-9447-28e5e92b18f1/all-network-devices
   - Search for "Living Room LG TV"
   - Should appear in table

---

## Troubleshooting

### Device Name Not Showing

**Check manual registry format:**
```bash
ssh root@192.168.1.2 "cat /root/etc/device-registry.conf"
```

**Common issues:**
- Typo in MAC address
- Missing `=` separator
- Extra spaces
- Wrong case (MACs are case-insensitive but must match format)

**Test resolution:**
```bash
ssh root@192.168.1.2 "/root/bin/resolve-device-name.sh 'IP' 'MAC'"
```

### Device Shows Old Name

- Wait 30 seconds for next Prometheus scrape
- Force Grafana dashboard refresh (Ctrl+R or Cmd+R)
- Check Prometheus target is UP: http://localhost:9090/targets

### Changes Not Persisting After Router Reboot

- Registry file is in `/root/etc/` which persists across reboots
- Verify file still exists: `ssh root@192.168.1.2 "cat /root/etc/device-registry.conf"`
- If missing, recreate it

---

## OUI Vendor Database

### Current Vendors in Database

The system includes these vendors:
- Apple Inc.
- LG Electronics
- Google Inc.
- Amazon Technologies
- eero Inc. (mesh WiFi)
- Wyze Labs (cameras)
- Robert Bosch (appliances)
- Ring Inc. (doorbells/cameras)

### Adding More Vendors

Edit: `/root/etc/oui-vendors.txt`

```bash
ssh root@192.168.1.2 "vi /root/etc/oui-vendors.txt"
```

Add entries in format: `OUI=Vendor Name`
```
A1:B2:C3=Vendor Name Inc.
```

**To find OUI:**
- First 3 octets of MAC address
- Look up at: https://maclookup.app/
- Or check manufacturer website

---

## Dashboard Access

### All Devices Table (Primary View)
**URL:** http://localhost:3000/d/14cf33bf-29ea-41cd-9447-28e5e92b18f1/all-network-devices

**Features:**
- Shows ALL 90+ devices (paginated 25 per page)
- Search by device name
- Sort by any column (bandwidth, connections, etc.)
- Click any row → drill down to Device Detail

### Device Detail (Drill-Down View)
**URL:** http://localhost:3000/d/66bdd5ca-674b-46db-b177-59920156e784/device-detail

**Features:**
- Select device from dropdown
- Bandwidth trends over time
- Connection patterns
- Protocol breakdown
- DNS activity

---

## Examples

### Example 1: Name Your Apple TV

1. Find MAC address:
   ```bash
   cat ~/network-monitoring/reports/client-activity-2025-12-19.md | grep "MD-DS3PDC4"
   ```
   Output: `MD-DS3PDC4 (Apple Inc.) | 192.168.1.109 | 80:f5:05`

2. Add to registry:
   ```bash
   ssh root@192.168.1.2
   echo "80:f5:05:xx:xx:xx=Living Room Apple TV" >> /root/etc/device-registry.conf
   ```

3. Wait 30 seconds and check Grafana

### Example 2: Name Your Work Laptop

1. Identify by high bandwidth usage in "All Devices Table"
2. Note MAC address from table
3. Add to registry with descriptive name
4. Device now shows as "Work Laptop" instead of generic hostname

---

**Changes take effect within 30 seconds - no router restart needed!**
