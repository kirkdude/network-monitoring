#!/bin/bash
# Quick status check for LG TV streaming

echo "📺 LG TV Streaming Status - $(date '+%H:%M:%S')"
echo "════════════════════════════════════════════════════════════════"
echo ""

# Show latest monitoring output
tail -n 20 /tmp/claude/-Users-kirkl-src-network-monitoring/tasks/bff139b.output 2>/dev/null | \
    grep -A 15 "Streaming Monitor" | tail -n 15

echo ""
echo "To watch live: tail -f /tmp/claude/-Users-kirkl-src-network-monitoring/tasks/bff139b.output"
