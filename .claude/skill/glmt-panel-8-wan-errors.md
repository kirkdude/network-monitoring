# GLMT2500A Health Panel 8: WAN Errors/Drops

## Panel Overview

- **Panel ID:** 8
- **Title:** WAN Errors/Drops (period)
- **Type:** Stat
- **Location:** GLMT2500A Health row
- **Purpose:** Shows count of network errors and dropped packets on WAN interfaces during selected time period

## Data Source

### InfluxDB Flux Query

```flux
from(bucket: "network")
  |> range(start: v.timeRangeStart, stop: v.timeRangeStop)
  |> filter(fn: (r) => r._measurement == "router_stats")
  |> filter(fn: (r) => r._field == "node_network_receive_errs_total" or r._field == "node_network_receive_drop_total")
  |> filter(fn: (r) => r.device == "eth0" or r.device == "eth1")
  |> difference(nonNegative: true)
  |> group()
  |> sum()
  |> last()
  |> map(fn: (r) => ({r with _field: if r._field == "node_network_receive_errs_total" then "Errors" else "Dropped"}))
  |> drop(columns: ["_start", "_stop", "_measurement", "device"])
```

### Data Collection Flow

1. **Router:** prometheus-node-exporter-lua exposes metrics at http://192.168.1.2:9100/metrics
2. **Metrics:** Network error counters (cumulative since boot)
3. **Telegraf:** Scrapes every 60s via `inputs.prometheus`
4. **InfluxDB:** Stores as `router_stats` measurement
5. **Grafana:** Calculates delta over time range

### Metrics Used

- **Measurement:** `router_stats`
- **Fields:**
  - `node_network_receive_errs_total` - Cumulative receive errors
  - `node_network_receive_drop_total` - Cumulative dropped packets
- **Device Tag:** `device="eth0"` or `device="eth1"` (WAN interfaces)
- **Calculation:** `difference()` shows new errors/drops in the selected time period

## Critical Fixes

### Problem: No Data (Field and Tag Names Changed)

**Old Query (Broken):**
```flux
filter(fn: (r) => r._measurement == "router_stats" and r.device == "glmt2500a" and r.interface == "wan")
filter(fn: (r) => r._field == "rx_errors" or r._field == "rx_dropped")
```

**Issues:**
1. Fields `rx_errors`, `rx_dropped` don't exist
2. Tag `interface="wan"` doesn't exist
3. Filter used wrong `device` value (should be interface name, not router name)

**Solution:**
1. Use `node_network_receive_errs_total` and `node_network_receive_drop_total`
2. Filter by `device == "eth0" or device == "eth1"` (interface names)
3. Use `difference()` before `group()` to calculate delta per interface

### Problem: "_value" Label in UI

**Solution:** Use `map()` to rename _field + `drop()` unwanted columns
```flux
|> map(fn: (r) => ({r with _field: if r._field == "node_network_receive_errs_total" then "Errors" else "Dropped"}))
|> drop(columns: ["_start", "_stop", "_measurement", "device"])
```

**Key:** Rename _field (not _value) to show "Errors" and "Dropped" as separate series

### Problem: Difference vs Derivative

**Understanding:**
- `difference()` - Shows total change in time range (errors since range start)
- `derivative()` - Shows rate of change (errors per second)

**For Error Counts:** Use `difference()` because we want total count, not rate

## Configuration

### Thresholds
- Green: 0-99 errors (normal)
- Yellow: 100-999 errors (concerning)
- Red: 1000+ errors (critical)

### Display
- Unit: short (count)
- Shows separate values for Errors and Dropped packets
- textMode: "value_and_name" (shows both number and type)

### Time Range
- Respects dashboard time picker
- Shows errors/drops that occurred during selected period
- Counter reset on router reboot

## Troubleshooting

### High Error Count

If errors > 100:
```bash
# Check interface stats on router
ssh root@192.168.1.2
cat /sys/class/net/eth0/statistics/rx_errors
cat /sys/class/net/eth0/statistics/rx_dropped

# Check for hardware issues
dmesg | grep -i error
logread | grep -i eth
```

### Common Causes
- Cable issues (physical layer errors)
- MTU mismatch
- Buffer overruns during traffic spikes
- Hardware defects

## GL-MT2500A WAN Interfaces

- **eth0:** Primary WAN port (Gigabit Ethernet)
- **eth1:** Secondary/failover port
- Monitoring both ensures all WAN traffic is captured
