---
name: performance_benchmark
description: Performance regression detection — baseline capture, Core Web Vitals, bundle size, regression thresholds
tags: [performance, testing, monitoring]
source: gstack/garrytan/gstack
---
# Performance Benchmark

Comprehensive performance audit with baseline comparison and regression detection.

## When to Use

- Before and after major changes
- Performance optimization work
- Release readiness checks
- Periodic performance audits

## The Process

### Phase 1: Page Discovery
Identify pages to benchmark:
- High-traffic pages (homepage, dashboard, key flows)
- Pages with heavy data loading
- Pages that changed in this release

### Phase 2: Performance Data Collection

**Timing Metrics:**
- TTFB (Time to First Byte)
- FCP (First Contentful Paint)
- LCP (Largest Contentful Paint)
- DOM Interactive / DOM Complete

**Resource Analysis:**
- Total bundle size (JS, CSS, images)
- Slowest loading resources
- Number of network requests
- Transfer size vs uncompressed size

**Core Web Vitals:**
- LCP < 2.5s (good), < 4s (needs improvement), > 4s (poor)
- FID < 100ms (good), < 300ms (needs improvement), > 300ms (poor)
- CLS < 0.1 (good), < 0.25 (needs improvement), > 0.25 (poor)

### Phase 3: Baseline Mode
First run captures baseline. Save metrics for future comparison.

### Phase 4: Regression Detection

| Metric | Regression Threshold | Action |
|--------|---------------------|--------|
| Timing | >50% slower OR >500ms absolute increase | REGRESSION |
| Bundle size | >25% increase | REGRESSION |
| Request count | >30% increase | WARNING |
| Core Web Vitals | Drops to next tier | REGRESSION |

### Phase 5: Slowest Resources Analysis
Identify the top 5 slowest resources:
- Could any be lazy-loaded?
- Are images optimized?
- Are large JS bundles code-split?

### Phase 6: Performance Budget

| Metric | Budget | Industry Standard |
|--------|--------|------------------|
| Total JS | < 300KB gzipped | Varies by app type |
| Total CSS | < 100KB gzipped | |
| LCP | < 2.5s | Google Core Web Vitals |
| Total requests | < 50 | |
| Page weight | < 2MB | |

### Phase 7: Trend Analysis
Compare against historical data if available:
- Is performance improving or degrading over time?
- Which metrics are trending in the wrong direction?

## Output

```
## Performance Benchmark Report

**Date:** YYYY-MM-DD
**Pages tested:** N

### Summary
| Page | LCP | FCP | Bundle | Status |
|------|-----|-----|--------|--------|
| / | 1.8s | 0.9s | 245KB | OK |
| /dashboard | 3.2s | 1.4s | 380KB | REGRESSION |

### Regressions
1. /dashboard LCP: 2.1s → 3.2s (+52%) — REGRESSION

### Recommendations
1. [specific actionable suggestion]
```

## Rules

- **Measure actual performance, not estimates**
- **Baseline is essential** — no baseline = no regression detection
- **Test on realistic data** — empty states perform differently than loaded states
- **Network conditions matter** — document the test environment
