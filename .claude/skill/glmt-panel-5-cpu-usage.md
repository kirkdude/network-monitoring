# GLMT2500A Health Panel 5: CPU Usage

## Panel Overview

- **Panel ID:** 5
- **Title:** CPU Usage
- **Type:** Gauge (dual needle - Average & Peak)
- **Location:** GLMT2500A Health row
- **Purpose:** Shows router CPU utilization as percentage with average and peak values over selected time range

## Data Source

### InfluxDB Flux Query

```flux
// Query A - Average CPU
from(bucket: "network")
  |> range(start: v.timeRangeStart, stop: v.timeRangeStop)
  |> filter(fn: (r) => r._measurement == "router_stats" and r.device == "glmt2500a")
  |> filter(fn: (r) => r._field == "node_load1")
  |> mean()
  |> map(fn: (r) => ({r with _value: r._value / 2.0 * 100.0}))
  |> rename(columns: {_value: "Average"})
  |> drop(columns: ["_start", "_stop", "_field", "_measurement", "device", "host", "location", "url"])

// Query B - Peak CPU
from(bucket: "network")
  |> range(start: v.timeRangeStart, stop: v.timeRangeStop)
  |> filter(fn: (r) => r._measurement == "router_stats" and r.device == "glmt2500a")
  |> filter(fn: (r) => r._field == "node_load1")
  |> max()
  |> map(fn: (r) => ({r with _value: r._value / 2.0 * 100.0}))
  |> rename(columns: {_value: "Peak"})
  |> drop(columns: ["_start", "_stop", "_field", "_measurement", "device", "host", "location", "url"])
```

### Data Collection Flow

1. **Router:** prometheus-node-exporter-lua exposes metrics at http://192.168.1.2:9100/metrics
2. **Telegraf:** Scrapes endpoint every 60s via `inputs.prometheus`
3. **InfluxDB:** Stores in "network" bucket as `router_stats` measurement
4. **Grafana:** Displays gauge with thresholds

### Metrics Used

- **Measurement:** `router_stats` (from prometheus-node-exporter-lua)
- **Field:** `node_load1` (1-minute load average)
- **Tags:** `device="glmt2500a"`, `host="network-monitoring"`, `location="network-core"`
- **Calculation:** `node_load1 / 2 cores * 100 = CPU %`

## Critical Fixes

### Problem: No Data (Field Names Changed)

**Old Query (Broken):**
```flux
filter(fn: (r) => r._field == "cpu_user" or r._field == "cpu_system" or r._field == "cpu_total")
```

**Issue:** These fields don't exist in prometheus-node-exporter-lua output

**Solution:** Use `node_load1` as CPU approximation
- GL-MT2500A has 2 cores
- Load average of 0.5 = 25% CPU (0.5 / 2 * 100)
- Load average of 1.0 = 50% CPU
- Load average of 2.0 = 100% CPU

### Problem: "_value" Label Showing in UI

**Old Query:**
```flux
|> map(fn: (r) => ({_value: r._value / 2.0 * 100.0}))
```

**Issue:** Grafana displays "_value" as series name in gauge

**Solution:** Use `rename()` + `drop()` pattern
```flux
|> map(fn: (r) => ({r with _value: r._value / 2.0 * 100.0}))
|> rename(columns: {_value: "Average"})
|> drop(columns: ["_start", "_stop", "_field", "_measurement", "device", "host", "location", "url"])
```

**Key:** Use `{r with _value: ...}` NOT `{_value: ...}` to preserve row structure, then rename and drop

## Configuration

### Thresholds
- Green: 0-59% (healthy)
- Yellow: 60-79% (elevated)
- Red: 80-100% (overloaded)

### Display
- Unit: percent
- Min: 0, Max: 100
- Shows both Average and Peak over time range

### Time Range
- Respects dashboard time picker via `v.timeRangeStart` and `v.timeRangeStop`
- Average/Peak calculated over selected range

## Router Capacity

- **Hardware:** MediaTek MT7621A, 2 cores @ 880 MHz
- **Safe range:** <15% average CPU
- **Previous crisis:** 90% CPU from monitoring overload
- **Current target:** 5-8% total monitoring overhead
