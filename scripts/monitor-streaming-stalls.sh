#!/bin/bash

# Real-time streaming stall detector for LG TV
# Monitors all active connections and alerts when data flow stops

TV_IP="192.168.1.70"
TEMP_DIR="/tmp/lg-tv-monitor"
mkdir -p "$TEMP_DIR"

echo "🔍 Streaming Stall Monitor - LG TV ($TV_IP)"
echo "Monitoring all active streaming connections..."
echo "Press Ctrl+C to stop"
echo ""

iteration=0

while true; do
    iteration=$((iteration + 1))
    clear
    echo "════════════════════════════════════════════════════════════════"
    echo "📺 Streaming Monitor - $(date '+%H:%M:%S') - Cycle #$iteration"
    echo "════════════════════════════════════════════════════════════════"
    echo ""

    # Get connections and save current state
    # shellcheck disable=SC2029
    ssh root@192.168.1.2 "conntrack -L -s '$TV_IP' 2>/dev/null | grep ESTABLISHED" 2>/dev/null > "$TEMP_DIR/current"

    # Process each connection
    while read -r line; do
        # Extract destination IP (first dst= value)
        dst_ip=$(echo "$line" | awk '{for(i=1;i<=NF;i++) if($i~/^dst=/) {print $i; exit}}' | cut -d= -f2)

        # Extract bytes received (second bytes= value)
        bytes_rx=$(echo "$line" | grep -o 'bytes=[0-9]*' | sed 's/bytes=//' | tail -1)

        if [ -n "$bytes_rx" ] && [ "$bytes_rx" -gt 100000 ]; then
            total_mb=$((bytes_rx / 1024 / 1024))

            # Check if we have previous data
            prev_file="$TEMP_DIR/${dst_ip}.prev"
            if [ -f "$prev_file" ]; then
                prev_bytes=$(cat "$prev_file")
                delta=$((bytes_rx - prev_bytes))
                delta_kb=$((delta / 1024))

                # Status indicator
                if [ "$delta" -gt 10000 ]; then
                    status="✅ STREAMING"
                    speed_kbps=$((delta * 8 / 1024 / 3))
                    printf "%-18s %12s  Total: %5d MB  +%6d KB  (~%d kbps)\n" \
                        "$dst_ip" "$status" "$total_mb" "$delta_kb" "$speed_kbps"
                elif [ "$delta" -gt 0 ]; then
                    status="⚠️  SLOW"
                    printf "%-18s %12s  Total: %5d MB  +%6d KB  (slow)\n" \
                        "$dst_ip" "$status" "$total_mb" "$delta_kb"
                else
                    status="🔴 STALLED"
                    printf "%-18s %12s  Total: %5d MB  +%6d KB  (NO DATA!)\n" \
                        "$dst_ip" "$status" "$total_mb" "$delta_kb"
                fi
            else
                printf "%-18s %12s  Total: %5d MB  (new)\n" \
                    "$dst_ip" "🆕 NEW" "$total_mb"
            fi

            # Save current bytes for next iteration
            echo "$bytes_rx" > "$prev_file"
        fi
    done < "$TEMP_DIR/current"

    echo ""
    echo "Recent DNS queries:"
    # shellcheck disable=SC2029
    ssh root@192.168.1.2 "cat /var/log/dnsmasq.log | grep '$TV_IP'" 2>/dev/null | tail -3 | awk '{print $NF}' | sed 's/^/  /'

    echo ""
    echo "════════════════════════════════════════════════════════════════"
    echo "Legend: ✅=Active | ⚠️=Slow | 🔴=Stalled | 🆕=New"

    sleep 3
done
