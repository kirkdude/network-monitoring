# Panel 10: Domain Access by Device (Drill-Down)

## Panel Overview

- **Panel ID:** 10
- **Title:** Domain Access by Device (Drill-Down)
- **Type:** Table
- **Grid Position:** x=0, y=42, width=24, height=10 (full width)
- **Purpose:** Shows which devices access which domains with query counts - enables security investigation

## Critical Fix Applied (2025-12-26)

**Issue:** Max series exceeded (> 1001) error

**Solution:** Added `drop(columns: ["_time"])` and `group()` to ungroup before display:

```flux
|> drop(columns: ["_time"])
|> group(columns: ["domain", "device_name"])
|> count()
|> group()  // Ungroup into single table
```

## Data Source

### InfluxDB Flux Query

```flux
from(bucket: "network")
  |> range(start: v.timeRangeStart, stop: v.timeRangeStop)
  |> filter(fn: (r) => r._measurement == "dns_query" and r._field == "domain")
  |> map(fn: (r) => ({r with domain: r._value}))
  |> drop(columns: ["_time"])
  |> group(columns: ["domain", "device_name"])
  |> count()
  |> group()
  |> rename(columns: {_value: "Queries"})
  |> keep(columns: ["domain", "device_name", "Queries"])
  |> sort(columns: ["Queries"], desc: true)
  |> limit(n: 100)
```

## Configuration

**Columns:**

- Domain - Domain name accessed
- Device Name - Device making the queries
- Queries - Count of DNS queries

**Sorting:** Descending by Queries (highest first)

**Limit:** 100 rows (shows top 100 domain-device pairs)

**NOT affected by top_n variable** - shows comprehensive data for investigation

## Use Cases

**Security Investigation:**

1. Click domain in Panel 9 → Panel 10 filters to show which devices access it
2. Investigate suspicious domain: "Who is accessing malware-c2.evil.com?"
3. Correlate with Panel 7 (Client Activity Table) for full device profile

**Examples:**

- `pastebin.com` accessed by IoT device → 🚨 High alert (data exfiltration)
- `github.com` accessed by 50 devices → ✅ Normal (development team)
- Unknown domain accessed by single device → ⚠️ Investigate device

## Related Panels

- **Panel 9:** Top Domains Accessed - Overview of network-wide domain activity
- **Panel 7:** Client Activity Table - Full device metrics
- **Panel 5:** Unique Domains Per Client - Diversity indicator
