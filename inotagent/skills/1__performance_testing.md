---
name: performance_testing
description: Load testing methodology, benchmarking workflow, bottleneck identification, and performance budgets
tags: [testing, performance, benchmarking, load-testing]
source: agency-agents/testing/testing-performance-benchmarker
---

## Performance Testing

> ~1600 tokens

### Testing Workflow

1. **Baseline**: Measure current performance across all components before any optimization
2. **Define targets**: Set SLA thresholds with stakeholder alignment (p95 latency, error rate, throughput)
3. **Design scenarios**: Load, stress, spike, endurance tests simulating real user behavior
4. **Execute + measure**: Run tests with statistical analysis (confidence intervals, percentiles)
5. **Identify bottlenecks**: Systematic analysis of DB, app layer, infra, third-party deps
6. **Optimize + validate**: Before/after comparison proving improvement
7. **Monitor**: Continuous regression testing in CI/CD

### Test Types

| Type | Purpose | Approach |
|------|---------|----------|
| Load | Normal conditions | Ramp to expected concurrent users |
| Stress | Breaking point | Exceed capacity, observe degradation + recovery |
| Spike | Sudden burst | Jump to 10x normal, measure response |
| Endurance | Long-term stability | Sustained load for hours, detect memory leaks |
| Scalability | Growth readiness | Incremental load increase, measure linear vs degraded scaling |

### Core Web Vitals Targets

- **LCP** (Largest Contentful Paint): < 2.5s
- **FID** (First Input Delay): < 100ms
- **CLS** (Cumulative Layout Shift): < 0.1
- **Speed Index**: measure visual loading progress

### Key Metrics to Track

**Response time**: p50, p95, p99 latencies (not just averages)
**Throughput**: requests/second at each load level
**Error rate**: target < 1% under normal load
**Resource utilization**: CPU, memory, disk I/O, network at each tier
**Saturation point**: load level where p95 latency exceeds SLA
**Recovery time**: how long to return to normal after stress

### Performance Budget Template

```
Category          | Budget    | Measurement
------------------|-----------|------------------
API response (p95)| < 500ms   | k6/locust
Page load (LCP)   | < 2.5s    | Lighthouse/RUM
Error rate        | < 1%      | monitoring
JS bundle         | < 200KB   | build output
CSS bundle        | < 50KB    | build output
Image (hero)      | < 200KB   | per asset
Time to Interactive| < 3.5s   | Lighthouse
```

### k6 Load Test Stages Pattern

```javascript
export const options = {
  stages: [
    { duration: '2m', target: 10 },   // warm up
    { duration: '5m', target: 50 },   // normal load
    { duration: '2m', target: 100 },  // peak load
    { duration: '5m', target: 100 },  // sustained peak
    { duration: '2m', target: 200 },  // stress
    { duration: '3m', target: 0 },    // cool down
  ],
  thresholds: {
    http_req_duration: ['p(95)<500'],
    http_req_failed: ['rate<0.01'],
  },
};
```

### Bottleneck Identification Checklist

- [ ] **Database**: slow queries (EXPLAIN ANALYZE), missing indexes, connection pool exhaustion, lock contention
- [ ] **Application**: CPU hotspots, memory leaks, blocking I/O, inefficient algorithms, N+1 queries
- [ ] **Infrastructure**: CPU/memory saturation, disk I/O bottleneck, network bandwidth, DNS latency
- [ ] **Third-party**: external API latency, CDN cache miss rate, payment gateway timeout
- [ ] **Frontend**: unoptimized images, render-blocking resources, large JS bundles, layout thrashing

### Performance Report Template

```
# Performance Analysis Report
System: [name]
Date: [date]
Environment: [specs matching production]

## Test Results
- Load Test: [p95 latency, throughput, error rate at target load]
- Stress Test: [breaking point, degradation pattern, recovery time]
- Endurance: [stability over [hours], memory trend, leak detection]

## Bottlenecks Found
1. [Component]: [issue] -> [impact on p95] -> [fix]

## Optimization Results
| Metric | Before | After | Improvement |
|--------|--------|-------|-------------|

## Recommendations
- High Priority: [immediate fixes]
- Medium Priority: [next sprint]
- Long-term: [architectural changes]

## Scalability Assessment
Current capacity: [N concurrent users]
Growth headroom: [Nx before degradation]
Scaling strategy: [horizontal/vertical + specifics]
```
