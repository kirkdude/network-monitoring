# Panel 11: Upload Bandwidth Over Time

## Panel Overview

- **Panel ID:** 11
- **Title:** Upload Bandwidth Over Time (Top ${top_n})
- **Type:** Time Series (Line Graph)
- **Grid Position:** x=0, y=16, width=24, height=8 (full width, below download panel)
- **Purpose:** Shows upload bandwidth trends over time with security-focused device selection
- **Created:** 2025-12-26 (companion to Panel 3 for cleaner legend display)

## Why This Panel Exists

**Original Problem:**

- Combined download+upload in single panel = 2N legend entries (confusing)
- With top_n=10: 20 lines in legend made tracking difficult

**Solution:**

- Panel 3: Download bandwidth (N devices, N legend entries)
- Panel 11: Upload bandwidth (same N devices, N legend entries)
- **Cleaner:** Each panel has manageable legend
- **Consistent:** Same devices in both panels (same scoring algorithm)

## Data Source

### InfluxDB Flux Query

```flux
selectedDevices = from(bucket: "network")
  |> range(start: v.timeRangeStart, stop: v.timeRangeStop)
  |> filter(fn: (r) => r._measurement == "bandwidth")
  |> drop(columns: ["_time"])
  |> group(columns: ["device_name", "direction"])
  |> sum()
  |> pivot(rowKey: ["device_name"], columnKey: ["direction"], valueColumn: "_value")
  |> map(fn: (r) => ({
      device_name: r.device_name,
      download_bytes: if exists r.rx then r.rx else 0,
      upload_bytes: if exists r.tx then r.tx else 0,
      upload_bps: (if exists r.tx then float(v: r.tx) else 0.0) * 8.0 / (float(v: uint(v: v.timeRangeStop) - uint(v: v.timeRangeStart)) / 1000000000.0),
      score: float(v: if (if exists r.rx then r.rx else 0) > (if exists r.tx then r.tx else 0) then (if exists r.rx then r.rx else 0) else (if exists r.tx then r.tx else 0)) + (if ((if exists r.tx then float(v: r.tx) else 0.0) * 8.0 / (float(v: uint(v: v.timeRangeStop) - uint(v: v.timeRangeStart)) / 1000000000.0)) > 10000000.0 then 999999999999.0 else 0.0)
  }))
  |> group()  // CRITICAL: Ungroup before findColumn to get all devices
  |> sort(columns: ["score"], desc: true)
  |> limit(n: ${top_n})
  |> findColumn(fn: (key) => true, column: "device_name")

from(bucket: "network")
  |> range(start: v.timeRangeStart, stop: v.timeRangeStop)
  |> filter(fn: (r) => r._measurement == "bandwidth" and r.direction == "tx")
  |> filter(fn: (r) => contains(value: r.device_name, set: selectedDevices))
  |> group(columns: ["device_name"])
  |> aggregateWindow(every: v.windowPeriod, fn: sum, createEmpty: false)
  |> map(fn: (r) => ({ r with _value: float(v: r._value) * 8.0 / (float(v: uint(v: v.windowPeriod)) / 1000000000.0) }))
```

## Security-Focused Selection Algorithm

**Identical to Panel 3** - ensures same devices appear in both panels.

**Scoring:** `score = max(download_bytes, upload_bytes) + upload_bonus`

- **Upload bonus:** 999999999999 if device uploads > 10 Mbps
- **Result:** High uploaders ALWAYS in top N (exfiltration detection)

**Example Scenarios:**

1. Device: 500 MB download, 50 MB upload
   - Score: 500000000 + 999999999999 = guaranteed top N
   - **Appears in both panels** (high both ways)

2. Device: 10 MB download, 25 MB upload
   - Score: 25000000 + 999999999999 = guaranteed top N
   - **Appears in both panels** (upload bonus triggers)
   - **Security value:** Catches potential exfiltration even with low download

3. Device: 5 MB download, 8 MB upload
   - Score: max(5000000, 8000000) = 8000000 (no bonus)
   - May not appear (depends on other devices)

## Critical Implementation Details

See Panel 3 skill documentation for complete technical details on:

- Float conversion to prevent type errors
- `group()` before `findColumn()` to prevent single device bug
- `aggregateWindow()` for time series data
- Scoring algorithm mathematics

## Configuration

**Thresholds (same as download):**

- Green: 0-1 Mbps
- Yellow: 1-10 Mbps
- Red: >10 Mbps

**Time Range:** Respects dashboard time range variable and top_n selector

## Related Panels

- **Panel 3:** Download Bandwidth Over Time (same device selection)
- **Panel 2:** Top ${top_n} Bandwidth Users (Upload) - snapshot view with LCD gauge
- **Panel 7:** Client Activity Table - shows upload column for all devices
