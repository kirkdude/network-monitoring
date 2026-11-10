# GLMT2500A Health Panel 7: WAN Throughput

## Panel Overview

- **Panel ID:** 7
- **Title:** WAN Throughput
- **Type:** Gauge (4 needles - Download/Upload Avg & Peak)
- **Location:** GLMT2500A Health row
- **Purpose:** Shows router WAN interface throughput in bytes/second with average and peak values

## Data Source

### InfluxDB Flux Query

```flux
// Query A - Download Average
from(bucket: "network")
  |> range(start: v.timeRangeStart, stop: v.timeRangeStop)
  |> filter(fn: (r) => r._measurement == "router_stats")
  |> filter(fn: (r) => r._field == "node_network_receive_bytes_total" and (r.device == "eth0" or r.device == "eth1"))
  |> derivative(unit: 1s, nonNegative: true)
  |> group()
  |> sum()
  |> mean()
  |> rename(columns: {_value: "Download Avg"})
  |> drop(columns: ["_start", "_stop", "_field", "_measurement"])

// Query B - Download Peak
from(bucket: "network")
  |> range(start: v.timeRangeStart, stop: v.timeRangeStop)
  |> filter(fn: (r) => r._measurement == "router_stats")
  |> filter(fn: (r) => r._field == "node_network_receive_bytes_total" and (r.device == "eth0" or r.device == "eth1"))
  |> derivative(unit: 1s, nonNegative: true)
  |> group()
  |> sum()
  |> max()
  |> rename(columns: {_value: "Download Peak"})
  |> drop(columns: ["_start", "_stop", "_field", "_measurement"])

// Query C - Upload Average
from(bucket: "network")
  |> range(start: v.timeRangeStart, stop: v.timeRangeStop)
  |> filter(fn: (r) => r._measurement == "router_stats")
  |> filter(fn: (r) => r._field == "node_network_transmit_bytes_total" and (r.device == "eth0" or r.device == "eth1"))
  |> derivative(unit: 1s, nonNegative: true)
  |> group()
  |> sum()
  |> mean()
  |> rename(columns: {_value: "Upload Avg"})
  |> drop(columns: ["_start", "_stop", "_field", "_measurement"])

// Query D - Upload Peak
from(bucket: "network")
  |> range(start: v.timeRangeStart, stop: v.timeRangeStop)
  |> filter(fn: (r) => r._measurement == "router_stats")
  |> filter(fn: (r) => r._field == "node_network_transmit_bytes_total" and (r.device == "eth0" or r.device == "eth1"))
  |> derivative(unit: 1s, nonNegative: true)
  |> group()
  |> sum()
  |> max()
  |> rename(columns: {_value: "Upload Peak"})
  |> drop(columns: ["_start", "_stop", "_field", "_measurement"])
```

### Data Collection Flow

1. **Router:** prometheus-node-exporter-lua exposes metrics at http://192.168.1.2:9100/metrics
2. **Metrics:** Network interface counters (cumulative byte counts)
3. **Telegraf:** Scrapes every 60s via `inputs.prometheus`
4. **InfluxDB:** Stores as `router_stats` measurement
5. **Grafana:** Calculates rate and displays as throughput

### Metrics Used

- **Measurement:** `router_stats`
- **Fields:**
  - `node_network_receive_bytes_total` - Cumulative RX bytes
  - `node_network_transmit_bytes_total` - Cumulative TX bytes
- **Device Tag:** `device="eth0"` (WAN) or `device="eth1"` (LAN uplink)
- **Rate Calculation:** `derivative(unit: 1s)` converts cumulative counter to bytes/second

## Critical Fixes

### Problem: No Data (Field and Tag Names Changed)

**Old Query (Broken):**
```flux
filter(fn: (r) => r._measurement == "router_stats" and r.device == "glmt2500a" and r.interface == "wan")
filter(fn: (r) => r._field == "rx_rate")
```

**Issues:**
1. Field `rx_rate` doesn't exist (prometheus-node-exporter provides cumulative counters, not rates)
2. Tag `interface="wan"` doesn't exist (uses `device="eth0"` instead)

**Solution:**
1. Use `node_network_receive_bytes_total` (cumulative counter)
2. Calculate rate with `derivative(unit: 1s, nonNegative: true)`
3. Filter by `device == "eth0" or device == "eth1"` (WAN interfaces)
4. Sum both interfaces with `group() |> sum()`

### Problem: "_value" Label in UI

**Solution:** Use `rename()` + `drop()` pattern
```flux
|> rename(columns: {_value: "Download Avg"})
|> drop(columns: ["_start", "_stop", "_field", "_measurement"])
```

### Problem: Counter vs Rate

**Key Understanding:**
- prometheus-node-exporter provides **cumulative counters** (total bytes since boot)
- Dashboard needs **rate** (bytes per second)
- Use `derivative(unit: 1s, nonNegative: true)` to convert

## Configuration

### Thresholds
- Green: 0-50 MB/s (normal)
- Yellow: 50-100 MB/s (elevated)
- Red: >100 MB/s (saturated)

### Display
- Unit: Bps (bytes per second)
- 4 values: Download Avg/Peak, Upload Avg/Peak

### Time Range
- Respects dashboard time picker
- Average/Peak calculated over selected range

## GL-MT2500A Network Interfaces

- **eth0:** WAN port (to Starlink)
- **eth1:** LAN uplink (to switch/eero)
- **br-lan:** Bridge interface (internal)
- Monitoring both eth0 and eth1 captures total WAN throughput
