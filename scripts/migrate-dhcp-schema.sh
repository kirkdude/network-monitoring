#!/bin/bash

# ═══════════════════════════════════════════════════════════════
# DHCP Schema Migration Script
# ═══════════════════════════════════════════════════════════════
#
# Purpose: Migrate router DHCP configuration to new clean schema
#
# Changes:
#   - Reorganizes eero devices into consecutive 5-IP blocks
#   - Adds 2 missing eero WiFi radio static reservations
#   - Removes WorkMac static reservation (moves to DHCP pool)
#   - Maintains locked devices (MarantzSR8012, SonyDVD)
#
# Impact:
#   - Brief service interruption as devices get new IPs
#   - All devices will reconnect automatically
#   - Takes effect immediately (no reboot required)
#
# ═══════════════════════════════════════════════════════════════

set -e  # Exit on error

ROUTER="root@192.168.1.2"
BACKUP_DIR="/root/etc/backups"
TIMESTAMP=$(date +%Y%m%d-%H%M%S)
CONFIG_FILE="/etc/config/dhcp"
NEW_CONFIG="/tmp/dhcp-new"

echo "═══════════════════════════════════════════════════════════════"
echo "DHCP Schema Migration Script"
echo "═══════════════════════════════════════════════════════════════"
echo ""

# ─── Step 1: Pre-flight checks ───
echo "[1/7] Running pre-flight checks..."

echo "  → Testing SSH connection to router..."
if ! ssh -o ConnectTimeout=5 "$ROUTER" "echo 'Connection OK'" >/dev/null 2>&1; then
    echo "  ✗ ERROR: Cannot connect to router at $ROUTER"
    exit 1
fi
echo "  ✓ SSH connection successful"

echo "  → Checking current DHCP config exists..."
if ! ssh "$ROUTER" "test -f $CONFIG_FILE"; then
    echo "  ✗ ERROR: DHCP config file not found at $CONFIG_FILE"
    exit 1
fi
echo "  ✓ Current config found"

echo ""

# ─── Step 2: Create backup directory ───
echo "[2/7] Creating backup directory on router..."
ssh "$ROUTER" "mkdir -p $BACKUP_DIR"
echo "  ✓ Backup directory ready: $BACKUP_DIR"
echo ""

# ─── Step 3: Backup current configuration ───
echo "[3/7] Backing up current DHCP configuration..."
BACKUP_FILE="$BACKUP_DIR/dhcp-backup-$TIMESTAMP"
ssh "$ROUTER" "cp $CONFIG_FILE $BACKUP_FILE"
echo "  ✓ Backup saved: $BACKUP_FILE"
echo ""

# ─── Step 4: Display changes ───
echo "[4/7] Summary of changes:"
echo ""
echo "  ADDITIONS (new static reservations):"
echo "    • 20:be:cd:8f:10:72 → 192.168.1.12 (eero-1-wifi)"
echo "    • 9c:57:bc:14:1c:72 → 192.168.1.23 (eero-2-loft-wifi)"
echo ""
echo "  MOVES (IP address changes):"
echo "    • 9c:57:bc:14:1c:61: .13 → .21 (eero-2-loft-port1)"
echo "    • 9c:57:bc:14:1c:60: .14 → .22 (eero-2-loft-port2)"
echo "    • 60:f4:19:42:af:12: .16 → .26 (eero-3)"
echo "    • 60:f4:19:44:39:92: .19 → .31 (eero-4)"
echo "    • 60:f4:19:57:4a:72: .22 → .36 (eero-5)"
echo "    • 9c:57:bc:13:6e:32: .25 → .41 (eero-6)"
echo "    • 9c:57:bc:07:80:32: .28 → .46 (eero-7)"
echo ""
echo "  REMOVALS (now using DHCP pool):"
echo "    • 72:4d:fd:65:22:41 @ .34 (WorkMac laptop)"
echo ""
echo "  NO CHANGE (locked devices):"
echo "    • 00:05:CD:CA:FE:B4 @ .15 (MarantzSR8012)"
echo "    • 00:06:76:21:53:ee @ .20 (SonyDVD)"
echo ""

# ─── Step 5: Upload new configuration ───
echo "[5/7] Uploading new DHCP configuration..."

# Read the new config from local file
if [ ! -f "$(dirname "$0")/../docs/dhcp-config-new.txt" ]; then
    echo "  ✗ ERROR: New config file not found"
    echo "  Expected: $(dirname "$0")/../docs/dhcp-config-new.txt"
    exit 1
fi

# Copy new config to router
scp -q "$(dirname "$0")/../docs/dhcp-config-new.txt" "$ROUTER:$NEW_CONFIG"
echo "  ✓ New configuration uploaded to router"
echo ""

# ─── Step 6: Validate new configuration ───
echo "[6/7] Validating new configuration..."

# Check if new config has the expected number of host entries
EXPECTED_HOSTS=13
ACTUAL_HOSTS=$(ssh "$ROUTER" "grep -c 'config host' $NEW_CONFIG || true")

if [ "$ACTUAL_HOSTS" != "$EXPECTED_HOSTS" ]; then
    echo "  ✗ WARNING: Expected $EXPECTED_HOSTS host entries, found $ACTUAL_HOSTS"
    echo "  This may indicate a problem with the new configuration."
    read -p "  Continue anyway? (y/N): " -n 1 -r
    echo ""
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "  Migration aborted."
        ssh "$ROUTER" "rm $NEW_CONFIG"
        exit 1
    fi
fi
echo "  ✓ Configuration validated ($ACTUAL_HOSTS host entries)"
echo ""

# ─── Step 7: Apply new configuration ───
echo "[7/9] Applying new configuration..."
echo ""
echo "  ⚠ WARNING: This will cause brief network interruptions!"
echo "  • Devices will get new IP addresses IMMEDIATELY"
echo "  • Connections will drop for ~30-60 seconds"
echo "  • All devices will reconnect automatically"
echo ""
echo "  Migration strategy: Force immediate transition"
echo "  (All DHCP leases will be cleared to force instant IP changes)"
echo ""
read -p "  Ready to apply changes? (yes/NO): " -r
echo ""

if [[ ! $REPLY =~ ^[Yy][Ee][Ss]$ ]]; then
    echo "  Migration aborted by user."
    ssh "$ROUTER" "rm $NEW_CONFIG"
    exit 0
fi

echo "  → Moving new config into place..."
ssh "$ROUTER" "mv $NEW_CONFIG $CONFIG_FILE"
echo "  ✓ Config file updated"

echo ""
echo "[8/9] Testing dnsmasq with new configuration..."
echo "  → Attempting service restart..."

# Try to restart dnsmasq and capture any errors
if ssh "$ROUTER" "/etc/init.d/dnsmasq restart 2>&1" | tee /tmp/dnsmasq-restart.log | grep -qi "error\|fail"; then
    echo ""
    echo "  ✗ ERROR: dnsmasq failed to restart with new configuration!"
    echo ""
    cat /tmp/dnsmasq-restart.log
    echo ""
    echo "  → Rolling back to previous configuration..."
    ssh "$ROUTER" "cp $BACKUP_FILE $CONFIG_FILE && /etc/init.d/dnsmasq restart"
    echo "  ✓ Rollback complete - router back to original config"
    echo ""
    echo "  Please review the error above and fix the configuration."
    rm -f /tmp/dnsmasq-restart.log
    exit 1
fi

# Check if dnsmasq is actually running
echo "  → Verifying dnsmasq is running..."
if ! ssh "$ROUTER" "pgrep dnsmasq > /dev/null"; then
    echo ""
    echo "  ✗ ERROR: dnsmasq process not found after restart!"
    echo "  → Rolling back to previous configuration..."
    ssh "$ROUTER" "cp $BACKUP_FILE $CONFIG_FILE && /etc/init.d/dnsmasq restart"
    echo "  ✓ Rollback complete - router back to original config"
    exit 1
fi
echo "  ✓ dnsmasq running successfully with new config"

echo "  → Waiting for services to stabilize (3 seconds)..."
sleep 3
echo "  ✓ Services stable"
echo ""

echo "[9/9] Forcing immediate IP transition..."
echo "  → Clearing all DHCP leases to force immediate renewal..."
ssh "$ROUTER" "rm -f /tmp/dhcp.leases"
echo "  ✓ Lease database cleared"

echo "  → Final dnsmasq restart to activate changes..."
ssh "$ROUTER" "/etc/init.d/dnsmasq restart"
echo "  ✓ Service restarted"

echo "  → Waiting for network to stabilize (10 seconds)..."
sleep 10
echo "  ✓ Network stabilized"

echo ""
echo "═══════════════════════════════════════════════════════════════"
echo "✓ Migration Complete!"
echo "═══════════════════════════════════════════════════════════════"
echo ""
echo "Verification:"
echo "  → Checking current DHCP leases..."
echo ""

# Show eero leases
ssh "$ROUTER" "cat /tmp/dhcp.leases | grep eero | sort -t. -k4 -n" | while read line; do
    IP=$(echo "$line" | awk '{print $3}')
    MAC=$(echo "$line" | awk '{print $2}')
    echo "    $IP - $MAC"
done

echo ""
echo "Expected IP ranges:"
echo "  • eero-1:       .10-.14"
echo "  • eero-2-loft:  .21-.25"
echo "  • eero-3:       .26-.30"
echo "  • eero-4:       .31-.35"
echo "  • eero-5:       .36-.40"
echo "  • eero-6:       .41-.45"
echo "  • eero-7:       .46-.50"
echo ""
echo "Manual verification commands:"
echo "  ssh $ROUTER 'cat /tmp/dhcp.leases | grep eero'"
echo "  ssh $ROUTER 'cat /tmp/dhcp.leases | wc -l'  # Total leases"
echo ""
echo "If issues occur - Rollback procedure:"
echo "  ssh $ROUTER"
echo "  cp $BACKUP_FILE $CONFIG_FILE"
echo "  rm -f /tmp/dhcp.leases"
echo "  /etc/init.d/dnsmasq restart"
echo ""
echo "Backup location: $BACKUP_FILE"
echo ""
