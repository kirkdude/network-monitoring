# GLMT2500A Health Panel 6: Memory Usage

## Panel Overview

- **Panel ID:** 6
- **Title:** Memory Usage
- **Type:** Gauge (dual needle - Average & Peak)
- **Location:** GLMT2500A Health row
- **Purpose:** Shows router memory utilization as percentage with average and peak values over selected time range

## Data Source

### InfluxDB Flux Query

```flux
// Query A - Average Memory
total_mem = from(bucket: "network")
  |> range(start: v.timeRangeStart, stop: v.timeRangeStop)
  |> filter(fn: (r) => r._measurement == "router_stats" and r.device == "glmt2500a")
  |> filter(fn: (r) => r._field == "node_memory_MemTotal_bytes")
  |> last()
  |> findColumn(column: "_value", fn: (key) => true)

from(bucket: "network")
  |> range(start: v.timeRangeStart, stop: v.timeRangeStop)
  |> filter(fn: (r) => r._measurement == "router_stats" and r.device == "glmt2500a")
  |> filter(fn: (r) => r._field == "node_memory_MemAvailable_bytes")
  |> mean()
  |> map(fn: (r) => ({r with _value: (total_mem[0] - r._value) / total_mem[0] * 100.0}))
  |> rename(columns: {_value: "Average"})
  |> drop(columns: ["_start", "_stop", "_field", "_measurement", "device", "host", "location", "url"])

// Query B - Peak Memory
total_mem = from(bucket: "network")
  |> range(start: v.timeRangeStart, stop: v.timeRangeStop)
  |> filter(fn: (r) => r._measurement == "router_stats" and r.device == "glmt2500a")
  |> filter(fn: (r) => r._field == "node_memory_MemTotal_bytes")
  |> last()
  |> findColumn(column: "_value", fn: (key) => true)

from(bucket: "network")
  |> range(start: v.timeRangeStart, stop: v.timeRangeStop)
  |> filter(fn: (r) => r._measurement == "router_stats" and r.device == "glmt2500a")
  |> filter(fn: (r) => r._field == "node_memory_MemAvailable_bytes")
  |> max()
  |> map(fn: (r) => ({r with _value: (total_mem[0] - r._value) / total_mem[0] * 100.0}))
  |> rename(columns: {_value: "Peak"})
  |> drop(columns: ["_start", "_stop", "_field", "_measurement", "device", "host", "location", "url"])
```

### Data Collection Flow

1. **Router:** prometheus-node-exporter-lua exposes metrics at http://192.168.1.2:9100/metrics
2. **Telegraf:** Scrapes endpoint every 60s via `inputs.prometheus`
3. **InfluxDB:** Stores in "network" bucket as `router_stats` measurement
4. **Grafana:** Displays gauge with thresholds

### Metrics Used

- **Measurement:** `router_stats`
- **Fields:**
  - `node_memory_MemTotal_bytes` - Total RAM in bytes
  - `node_memory_MemAvailable_bytes` - Available RAM in bytes (not just free, includes reclaimable cache)
- **Calculation:** `(Total - Available) / Total * 100 = Memory Used %`

## Critical Fixes

### Problem: No Data (Field Names Changed)

**Old Query (Broken):**
```flux
filter(fn: (r) => r._field == "mem_used" or r._field == "mem_total")
```

**Issue:** These fields don't exist in prometheus-node-exporter-lua output

**Solution:** Use `node_memory_MemTotal_bytes` and `node_memory_MemAvailable_bytes`

### Problem: "_value" Label Showing in UI

**Solution:** Use `rename()` + `drop()` pattern after calculation
```flux
|> map(fn: (r) => ({r with _value: (total_mem[0] - r._value) / total_mem[0] * 100.0}))
|> rename(columns: {_value: "Average"})
|> drop(columns: ["_start", "_stop", "_field", "_measurement", "device", "host", "location", "url"])
```

**Key:** Use `{r with ...}` to preserve row, then rename and drop unwanted columns

### Problem: Getting Total Memory Value

**Solution:** Use `findColumn()` to extract scalar value
```flux
total_mem = from(bucket: "network")
  |> filter(fn: (r) => r._field == "node_memory_MemTotal_bytes")
  |> last()
  |> findColumn(column: "_value", fn: (key) => true)

// Now total_mem[0] contains the total bytes as a scalar
```

## Configuration

### Thresholds
- Green: 0-69% (healthy)
- Yellow: 70-84% (elevated)
- Red: 85-100% (critical)

### Display
- Unit: percent
- Min: 0, Max: 100
- Shows both Average and Peak over time range

### Time Range
- Respects dashboard time picker
- Average/Peak calculated over selected range

## Router Capacity

- **Hardware:** 1 GB RAM (GL-MT2500A)
- **Safe range:** <70% memory usage
- **Previous crisis:** Monitoring consumed 341MB (netifyd service)
- **Current state:** ~8-10% used (healthy)
