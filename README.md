# Network Monitoring Stack
## GL-MT2500A Router + Mac Mini Monitoring - Phase 2

Professional network visibility using Grafana dashboards, Prometheus metrics collection, and real-time alerting. 100% open source with zero subscription costs.

## Architecture

This monitoring stack runs on the Mac Mini and collects metrics from the GL-MT2500A router:

- **Prometheus**: Metrics collection and storage (1 year retention)
- **Grafana**: Visualization dashboards
- **InfluxDB**: Time-series data storage
- **ntopng**: Deep packet inspection (optional)
- **collectd**: System metrics collector

## Services & Ports

| Service | Port | URL | Credentials |
|---------|------|-----|-------------|
| Grafana | 3000 | http://localhost:3000 | admin / changeme123 |
| Prometheus | 9090 | http://localhost:9090 | none |
| InfluxDB | 8086 | http://localhost:8086 | admin / changeme123 |
| ntopng | 3001 | http://localhost:3001 | auto-login |

## Quick Start

### Prerequisites

1. **Docker Desktop installed** on Mac Mini
2. **Router exporter running** on GL-MT2500A at port 9100
3. **SSH access** to router configured

### Start the Monitoring Stack

```bash
cd ~/src/network-monitoring

# Start all services
docker-compose up -d

# Check status
docker-compose ps

# View logs
docker-compose logs -f
```

### Access Grafana

1. Open http://localhost:3000
2. Login: `admin` / `changeme123`
3. Import dashboards (see below)

## Importing Grafana Dashboards

Once Grafana is running, import these pre-built dashboards:

### Method 1: Import by ID

1. Go to **Dashboards → Import**
2. Enter dashboard ID
3. Select **Prometheus** as data source
4. Click **Import**

**Recommended Dashboards:**

| Dashboard ID | Name | Purpose |
|--------------|------|---------|
| **11147** | OpenWRT Overview | Router CPU, memory, network interfaces |
| **1860** | Node Exporter Full | Detailed system metrics |
| **11074** | Network Traffic | Bandwidth usage per interface |
| **7362** | Prometheus Stats | Prometheus performance monitoring |

### Method 2: Direct Links

- OpenWRT Overview: https://grafana.com/grafana/dashboards/11147
- Node Exporter Full: https://grafana.com/grafana/dashboards/1860
- Network Traffic: https://grafana.com/grafana/dashboards/11074

## Configuration Files

### prometheus.yml
Defines scraping targets and intervals. Currently configured to scrape:
- Router at `192.168.1.2:9100` every 15 seconds
- Prometheus self-monitoring

**Important**: The router target uses default instance labeling (`192.168.1.2:9100` format) which is required for Grafana dashboard variables to work correctly. Custom labels like `alias`, `device_type`, and `location` are added without overriding the instance label.

### prometheus-rules.yml
Alert definitions including:
- **Security alerts**: High connection count, port scanning, data exfiltration
- **System alerts**: High CPU, memory, disk usage
- **Network alerts**: Bandwidth spikes, new devices
- **LG TV alerts**: Update attempt detection

### grafana-provisioning/datasources/datasources.yml
Auto-configures Prometheus and InfluxDB as data sources in Grafana.

## Monitoring Capabilities

### Current Monitoring (Phase 2)
- ✅ Router CPU, memory, network interface metrics
- ✅ Active connections per device
- ✅ Bandwidth usage tracking
- ✅ Real-time alerting on anomalies
- ✅ 1 year data retention
- ✅ Professional Grafana dashboards

### Planned Enhancements (Phase 3)
- Bandwidth analysis per device (nlbwmon)
- DNS query analytics from AdGuard Home
- Baseline behavior establishment
- Anomaly detection tuning
- Threat intelligence integration

## Alerting Rules

Alerts are defined in `prometheus-rules.yml` and include:

### Network Security Alerts
- High connection count (>1000 connections for 5m)
- New device detection
- Bandwidth spikes (>100 MB/s)
- LG TV update attempts
- Port scanning detection
- Large data transfers (>50 MB/s upload for 10m)
- Unusual night-time activity (2 AM - 6 AM)

### System Health Alerts
- Router high CPU (>80% for 5m)
- Router high memory (>90% for 5m)
- Router down (unreachable for 2m)
- Router high disk (>85% for 10m)

## Troubleshooting

### No data in Grafana dashboards

1. **Check Prometheus targets:**
   - Open http://localhost:9090/targets
   - Verify router target is **UP**
   - If DOWN, check router exporter is running

2. **Verify router exporter:**
   ```bash
   ssh root@192.168.1.2
   /etc/init.d/prometheus-node-exporter-lua status
   curl http://192.168.1.2:9100/metrics
   ```

3. **Check router firewall:**
   - Port 9100 must be accessible from Mac Mini
   - Test: `curl http://192.168.1.2:9100/metrics` from Mac

### Containers not starting

```bash
# Check container status
docker-compose ps

# View logs for specific service
docker-compose logs prometheus
docker-compose logs grafana

# Restart all services
docker-compose restart
```

### High disk usage

```bash
# Check Prometheus data size
docker volume ls
docker system df -v

# Reduce retention if needed (edit docker-compose.yml)
# Change: '--storage.tsdb.retention.time=365d'
# To:     '--storage.tsdb.retention.time=180d'
docker-compose up -d --force-recreate prometheus
```

### Reload Prometheus configuration

```bash
# After editing prometheus.yml or prometheus-rules.yml
docker-compose exec prometheus kill -HUP 1

# Or restart Prometheus
docker-compose restart prometheus
```

## Commands Reference

### Docker Compose

```bash
# Start services
docker-compose up -d

# Stop services
docker-compose down

# View logs
docker-compose logs -f [service_name]

# Restart single service
docker-compose restart [service_name]

# Remove all data (DESTRUCTIVE)
docker-compose down -v
```

### Prometheus

```bash
# Check configuration
docker-compose exec prometheus promtool check config /etc/prometheus/prometheus.yml

# Check rules
docker-compose exec prometheus promtool check rules /etc/prometheus/rules.yml

# Reload configuration
docker-compose exec prometheus kill -HUP 1
```

### Grafana

```bash
# Reset admin password
docker-compose exec grafana grafana-cli admin reset-admin-password newpassword

# Install plugin
docker-compose exec grafana grafana-cli plugins install <plugin-name>
docker-compose restart grafana
```

## Maintenance

### Daily (Automated)
- Prometheus scrapes router every 15 seconds
- Alerts evaluated every 60 seconds
- Grafana dashboards auto-refresh

### Weekly
- Review dashboards for anomalies
- Check disk space: `docker system df -v`
- Review alert notifications

### Monthly
- Update threat intelligence feeds (Phase 3)
- Review and tune alert thresholds
- Backup Grafana dashboards
- Check for container updates: `docker-compose pull`

## Router Prerequisites

The GL-MT2500A router must have these packages installed:

```bash
ssh root@192.168.1.2
opkg update

# Required: Prometheus exporter
opkg install prometheus-node-exporter-lua
opkg install prometheus-node-exporter-lua-nat_traffic
opkg install prometheus-node-exporter-lua-netstat

# Enable and start
/etc/init.d/prometheus-node-exporter-lua enable
/etc/init.d/prometheus-node-exporter-lua start

# Verify
curl http://localhost:9100/metrics
```

## Security Notes

### Default Passwords
⚠️ **Change these before exposing to network:**
- Grafana: `admin` / `changeme123`
- InfluxDB: `admin` / `changeme123`

### Firewall Configuration
Services are bound to `localhost` by default. To access from other devices:
1. Update port bindings in `docker-compose.yml`
2. Configure Mac firewall appropriately
3. Consider using reverse proxy with authentication

## Data Storage

All data is stored in Docker volumes:
- `prometheus_data`: Time-series metrics (1 year retention)
- `grafana_data`: Dashboards and settings
- `influxdb_data`: InfluxDB storage
- `ntopng_data`: Deep packet inspection data

**Backup strategy:**
```bash
# Backup Grafana dashboards
docker-compose exec grafana grafana-cli admin export-dashboard > backup.json

# Backup volumes (when stopped)
docker-compose down
tar czf backup-$(date +%F).tar.gz prometheus_data/ grafana_data/
docker-compose up -d
```

## Cost Analysis

### 100% Open Source (Free)
- ✅ Prometheus: FREE
- ✅ Grafana: FREE
- ✅ InfluxDB: FREE
- ✅ ntopng Community: FREE
- ✅ collectd: FREE
- **Total: $0/month**

### Optional Paid Upgrades
- ntopng Pro: $150/year (advanced DPI)
- Grafana Enterprise: $299/year (advanced alerting)

**Recommendation:** Start with free tier, upgrade only if needed.

## Next Steps

### Phase 2 Completion Checklist
- [x] Create monitoring stack configuration
- [ ] Start Docker containers
- [ ] Verify Prometheus scraping router
- [ ] Import Grafana dashboards
- [ ] Test alerting rules
- [ ] Document baseline metrics

### Phase 3 Planning
- Add bandwidth analysis per device (nlbwmon)
- Integrate DNS query analytics from AdGuard Home
- Establish baseline behavior patterns (2 weeks)
- Configure advanced anomaly detection
- Set up threat intelligence feeds
- Configure notification channels (email/Slack)

## References

### Documentation
- [Prometheus Docs](https://prometheus.io/docs/)
- [Grafana Docs](https://grafana.com/docs/)
- [OpenWRT Monitoring](https://openwrt.org/docs/guide-user/perf_and_log/statistic.overview)

### Community Dashboards
- [Grafana Dashboard Library](https://grafana.com/grafana/dashboards/)
- [OpenWRT Dashboard 11147](https://grafana.com/grafana/dashboards/11147)

### Related Documentation
- Phase 1: See `FEATURE-NETWORK-MONITORING.md` in GL-MT2500A docs
- Router Setup: See `FEATURE-ROUTER-MIGRATION.md`

---

**Project:** Network Monitoring Stack
**Phase:** Phase 2 (Full Monitoring)
**Status:** Ready for deployment
**Last Updated:** 2025-12-18
