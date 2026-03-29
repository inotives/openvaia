---
name: canary_monitoring
description: Post-deploy canary monitoring — baseline comparison for console errors, performance regressions, page failures
tags: [deployment, monitoring, operations]
source: gstack/garrytan/gstack
---
# Canary Monitoring

Post-deploy health monitoring using baseline comparison. Alert on changes, not absolutes.

## Core Principle

**Alert on CHANGES vs baseline, not absolute values.** Don't cry wolf — require 2+ consecutive checks before alerting.

## When to Use

- After deploying to production
- After infrastructure changes
- Continuous production health monitoring

## The Process

### Phase 1: Baseline Capture
Before deployment, capture current state:
- Page load times for key pages
- Console error count
- HTTP error count (4xx, 5xx)
- Core Web Vitals (LCP, FID, CLS)

### Phase 2: Page Discovery
Auto-detect key pages to monitor:
- Navigation links, sitemap, route config
- Focus on user-critical paths (login, dashboard, checkout)

### Phase 3: Post-Deploy Monitoring Loop
Check every 60 seconds:

| Check | Severity | Threshold |
|-------|----------|-----------|
| Page load failure | CRITICAL | Any page returns 5xx or timeout |
| New console errors | HIGH | Errors not present in baseline |
| Performance regression | MEDIUM | 2x slower than baseline |
| New 404s | LOW | URLs that previously worked |

### Phase 4: Health Verdict

| Status | Meaning |
|--------|---------|
| **HEALTHY** | No regressions detected |
| **DEGRADED** | Medium/Low issues, still functional |
| **BROKEN** | Critical/High issues, rollback recommended |

### Phase 5: Baseline Update
If deployment is healthy after monitoring window, update baseline for future comparisons.

## Rules

- **Persist 2+ consecutive checks** before alerting (avoid false positives)
- **Compare against baseline**, not against arbitrary thresholds
- **Monitor user-critical paths first** — not every page needs canary
- **Include rollback instructions** in any BROKEN verdict
- **Capture evidence** — exact error messages, timestamps, affected URLs
