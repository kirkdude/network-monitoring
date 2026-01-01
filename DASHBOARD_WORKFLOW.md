# Grafana Dashboard Workflow

## ⚠️ IMPORTANT: Dashboard Editing Rules

### Current Configuration

- **allowUiUpdates: false** - Dashboards are READ-ONLY in Grafana UI
- All changes MUST be made by editing JSON files directly
- Dashboards automatically reload from files when changed

### Why This Matters

Previously, `allowUiUpdates: true` caused:

- ❌ UI edits stored in Grafana database, NOT files
- ❌ Grafana restart = all UI changes lost
- ❌ Files and database out of sync
- ❌ Regression nightmares

## ✅ Proper Workflow for Dashboard Changes

### Step 1: Edit JSON Files

Dashboard files exist in TWO locations (they must stay in sync):

```
grafana-dashboards/              ← Source files (for version control)
grafana-provisioning/dashboards/ ← What Grafana actually loads
```

**Always edit BOTH files identically:**

```bash
# Edit both files
vim grafana-dashboards/streaming-monitor.json
vim grafana-provisioning/dashboards/streaming-monitor.json

# Or copy to keep in sync
cp grafana-dashboards/streaming-monitor.json \
   grafana-provisioning/dashboards/streaming-monitor.json
```

### Step 2: Grafana Auto-Reloads

- Grafana checks for file changes every 10 seconds
- No restart needed for most changes
- Just save the file and refresh your browser

### Step 3: When to Restart Grafana

Only restart when:

- Changing datasource configurations
- Modifying `dashboards.yml` settings
- Grafana isn't picking up changes automatically

```bash
podman restart grafana
```

## 🔧 Making Dashboard Changes

### Method 1: Direct JSON Editing (Recommended)

```bash
# 1. Edit the JSON file
vim grafana-provisioning/dashboards/streaming-monitor.json

# 2. Copy to source directory for git
cp grafana-provisioning/dashboards/streaming-monitor.json \
   grafana-dashboards/streaming-monitor.json

# 3. Grafana auto-reloads in ~10 seconds
# 4. Refresh browser to see changes
```

### Method 2: Export from Grafana (For Complex Changes)

If you need to make visual changes:

```bash
# 1. Temporarily enable UI updates
# Edit grafana-provisioning/dashboards/dashboards.yml:
#   allowUiUpdates: true

# 2. Restart Grafana
podman restart grafana

# 3. Make changes in Grafana UI

# 4. Export dashboard JSON
#    Dashboard Settings → JSON Model → Copy to clipboard

# 5. Save to both locations:
#    - grafana-dashboards/your-dashboard.json
#    - grafana-provisioning/dashboards/your-dashboard.json

# 6. Disable UI updates again
# Edit grafana-provisioning/dashboards/dashboards.yml:
#   allowUiUpdates: false

# 7. Restart Grafana
podman restart grafana
```

## 📁 Directory Structure

```
network-monitoring/
├── grafana-dashboards/              # Version controlled source
│   ├── streaming-monitor.json
│   ├── client-monitoring.json
│   ├── device-detail.json
│   └── all-devices.json
│
├── grafana-provisioning/
│   ├── dashboards/
│   │   ├── dashboards.yml          # Configuration (allowUiUpdates: false)
│   │   ├── streaming-monitor.json  # Must match grafana-dashboards/
│   │   ├── client-monitoring.json
│   │   ├── device-detail.json
│   │   └── all-devices.json
│   └── datasources/
│       └── datasources.yml
```

## 🚫 Common Mistakes to Avoid

1. **DON'T** edit dashboards in Grafana UI (they're read-only now)
2. **DON'T** edit only one copy of the JSON file
3. **DON'T** restart Grafana unnecessarily
4. **DO** always edit both dashboard copies
5. **DO** commit changes to git
6. **DO** test changes before committing

## 🔍 Verifying Your Changes

```bash
# Check if dashboard files are in sync
diff grafana-dashboards/streaming-monitor.json \
     grafana-provisioning/dashboards/streaming-monitor.json

# Should return nothing if files are identical
```

## 🐛 Troubleshooting

### Dashboard not updating?

```bash
# Check Grafana logs
podman logs grafana | grep -i provision

# Force reload by touching the file
touch grafana-provisioning/dashboards/streaming-monitor.json

# Last resort: restart
podman restart grafana
```

### Lost changes after restart?

- This means you edited in Grafana UI instead of the JSON file
- Changes are lost forever (not saved to files)
- Always edit JSON files directly to prevent this

### Files out of sync?

```bash
# Compare all dashboard pairs
for f in grafana-dashboards/*.json; do
  basename=$(basename "$f")
  diff "$f" "grafana-provisioning/dashboards/$basename" && \
    echo "✓ $basename in sync" || \
    echo "✗ $basename OUT OF SYNC"
done
```

## 📝 Git Workflow

```bash
# After making dashboard changes:
git add grafana-dashboards/*.json
git add grafana-provisioning/dashboards/*.json
git commit -m "Update streaming monitor dashboard queries"
git push
```

## 🎯 Best Practices

1. **Single Source of Truth**: Files are the source of truth, not the Grafana database
2. **Keep in Sync**: Always update both dashboard directories
3. **Test First**: Make changes, test in browser, then commit
4. **Small Changes**: Make incremental changes rather than large rewrites
5. **Document Why**: Add comments in git commits explaining dashboard changes
6. **Backup**: The old dashboard versions are in git history

## 📚 Related Files

- `docker-compose.yml` - Grafana container configuration
- `grafana-provisioning/datasources/datasources.yml` - InfluxDB/Prometheus config
- `grafana-provisioning/dashboards/dashboards.yml` - Dashboard provisioning config
