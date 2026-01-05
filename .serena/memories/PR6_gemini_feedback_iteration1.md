# PR 6 Gemini Feedback - Iteration 1

**Branch:** fix/infrastructure-dashboard-cpu-panel
**PR URL:** <https://github.com/kirkdude/network-monitoring/pull/6>
**Review Date:** 2026-01-04T23:56:35Z

## Summary

Gemini identified 8 HIGH priority and 2 MEDIUM priority issues in the Flux queries and Telegraf configuration.

## HIGH Priority Issues

### 1. CPU Average Query (infrastructure-status.json:367)

**Issue:** Query fragile - if pivot produces rows where cpu_total is missing/zero or cpu_user/cpu_system are missing, map function will fail.
**Fix:** Add filter after pivot: `|> filter(fn: (r) => exists r.cpu_user and exists r.cpu_system and exists r.cpu_total and r.cpu_total > 0.0)`

### 2. CPU Current Query (infrastructure-status.json:375)

**Issue:** Same fragility as Average query
**Fix:** Same filter as above

### 3. Memory Average Query (infrastructure-status.json:432)

**Issue:** Query fragile - if mem_total is zero or mem_used/mem_total are missing after pivot, map function will fail.
**Fix:** Add filter: `|> filter(fn: (r) => exists r.mem_used and exists r.mem_total and r.mem_total > 0.0)`

### 4. Memory Current Query (infrastructure-status.json:440)

**Issue:** Same fragility as Memory Average query
**Fix:** Same filter as above

### 5. Router Latency Query (infrastructure-status.json:680)

**Issue:** Query not specific enough - includes 192.168.100.1 (Starlink Dishy) which will be incorrectly labeled as 'Starlink' router
**Fix:** Add filter for specific router IPs: `|> filter(fn: (r) => r.url == "192.168.1.2" or r.url == "192.168.2.1")`

### 6. Packet Loss Query (infrastructure-status.json:844)

**Issue:** Map function incomplete - doesn't handle all URLs. Both 192.168.100.1 and 1.1.1.1 fall into else clause and are mislabeled as 'Cloudflare'
**Fix:** Expand if-else chain to handle all URLs

### 7. Jitter Query (infrastructure-status.json:903)

**Issue:** Same incomplete map function as Packet Loss
**Fix:** Expand if-else chain to handle all URLs

### 8. Telegraf Redundant Monitoring (telegraf.conf:35)

**Issue:** 192.168.100.1 (Starlink Dishy) monitored twice - once in infrastructure type and once in starlink_dishy type
**Fix:** Remove 192.168.100.1 from infrastructure block, keep only in starlink_dishy block

## MEDIUM Priority Issues

### 9. Client Monitoring RX (client-monitoring.json:99)

**Issue:** Should filter out Router_DNS for consistency with device-detail.json
**Fix:** Update regex to: `r.device_name !~ /^(GL-iNet_Router.*|Router_DNS|localhost)$/`

### 10. Client Monitoring TX (client-monitoring.json:220)

**Issue:** Same as RX - should filter out Router_DNS
**Fix:** Update regex to: `r.device_name !~ /^(GL-iNet_Router.*|Router_DNS|localhost)$/`
