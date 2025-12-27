#!/bin/bash

# Monitor LG TV (192.168.1.70) for 15 minutes
# Shows real-time DNS queries, bandwidth, and connections

TV_IP="192.168.1.70"
DURATION=900  # 15 minutes in seconds
END_TIME=$(($(date +%s) + DURATION))

echo "🔍 Monitoring LG TV ($TV_IP) for 15 minutes..."
echo "Show will finish around: $(date -j -f %s $END_TIME '+%H:%M:%S')"
echo "Press Ctrl+C to stop early"
echo ""

while [ "$(date +%s)" -lt "$END_TIME" ]; do
    clear
    echo "════════════════════════════════════════════════════════════════"
    echo "📺 LG TV Monitor - $(date '+%H:%M:%S')"
    echo "Time remaining: $(( (END_TIME - $(date +%s)) / 60 )) minutes"
    echo "════════════════════════════════════════════════════════════════"
    echo ""

    # Recent DNS queries (last 30 seconds)
    echo "🌐 Recent DNS Queries (last 30s):"
    podman exec influxdb influx query "
from(bucket: \"network\")
  |> range(start: -30s)
  |> filter(fn: (r) => r._measurement == \"dns_query\" and r.ip == \"$TV_IP\")
  |> filter(fn: (r) => r._field == \"domain\")
  |> keep(columns: [\"_time\", \"_value\"])
  |> sort(columns: [\"_time\"], desc: true)
  |> limit(n: 8)
" --org home 2>/dev/null | tail -n +4 | head -n 8 || echo "  No recent queries"

    echo ""
    echo "📊 Active Connections (current):"
    podman exec influxdb influx query "
from(bucket: \"network\")
  |> range(start: -1m)
  |> filter(fn: (r) => r._measurement == \"connection_state\" and r.ip == \"$TV_IP\")
  |> last()
  |> group(columns: [\"proto\", \"state\"])
  |> sum()
  |> sort(columns: [\"_value\"], desc: true)
  |> limit(n: 5)
" --org home 2>/dev/null | grep -E 'tcp|udp|ESTABLISHED|ACTIVE' | head -n 5 || echo "  No active connections"

    echo ""
    echo "📈 Bandwidth (last minute):"
    podman exec influxdb influx query "
from(bucket: \"network\")
  |> range(start: -1m)
  |> filter(fn: (r) => r._measurement == \"bandwidth\" and r.ip == \"$TV_IP\")
  |> group(columns: [\"direction\"])
  |> sum()
  |> map(fn: (r) => ({ r with _value: float(v: r._value) / 1024.0 / 1024.0 }))
" --org home 2>/dev/null | grep -E 'rx|tx|_value' | tail -n 4 || echo "  No bandwidth data"

    echo ""
    echo "════════════════════════════════════════════════════════════════"

    # Update every 5 seconds
    sleep 5
done

echo ""
echo "✅ Monitoring complete! Show should be finished."
