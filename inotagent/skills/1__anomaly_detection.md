---
name: anomaly_detection
description: Monitor time-series metrics for statistically significant deviations using multiple detection methods with seasonality awareness.
tags: [data, monitoring, anomaly, statistics]
source: awesome-openclaw-agents/agents/data/anomaly-detector
---

## Anomaly Detection

> ~616 tokens

### Detection Methods

| Method | Best For | Description |
|--------|----------|-------------|
| Z-score | Normally distributed metrics | Flag values > N standard deviations from mean |
| Modified z-score | Metrics with outliers | Uses median absolute deviation instead of mean |
| IQR | Skewed distributions | Flag values outside 1.5x interquartile range |
| Moving average deviation | Trending metrics | Compare to rolling window average |
| Seasonal decomposition | Metrics with daily/weekly patterns | Account for cyclical patterns |

### Anomaly Types

- **Point anomaly:** Single data point far from expected value
- **Contextual anomaly:** Value unusual for its time context (e.g., low traffic on a weekday)
- **Collective anomaly:** Sequence of values that are anomalous together

### Severity Levels

| Level | Criteria | Action |
|-------|----------|--------|
| INFO | Interesting but within expected variation | Log, no alert |
| WARNING | Unusual, sustained deviation | Monitor closely |
| CRITICAL | Extreme deviation or sustained > threshold | Immediate investigation |

### Alert Configuration Template

```
Metric: <name>
Baseline: <N>-day rolling average of <value> (<granularity>)
Detection method: <method> with <adjustments>

Thresholds:
- WARNING: > <N> standard deviations sustained for <duration>
  (estimated <N> false positives per <period>)
- CRITICAL: > <N> standard deviations or value <threshold> for <duration>
  (estimated <N> false positives per <period>)

Suppression: Suppress alerts when <condition> (e.g., low sample size)
Correlation: Also monitor <related metrics>
```

### Anomaly Report Format

```
Analysis of <metric> (<time window>, <granularity>):
<N> anomalies detected.

Anomaly N (<severity>, confidence <percent>%):
  When: <time range>
  Actual: <value> vs. baseline <value> (<Nx deviation>)
  Method: <detection method used> (<why this method>)
  Correlation: <related signals>
  Likely cause: <hypothesis>
  Suggested investigation: <next steps>
```

### Rules

- Never alert on a single data point; require sustained deviation or extreme magnitude
- Always report: metric name, expected range, actual value, deviation magnitude, confidence level
- Include the detection method used and why it was chosen
- Account for seasonality (hourly, daily, weekly patterns) to reduce false positives
- Correlate anomalies across related metrics to identify root causes
- State false positive rate when configuring detection thresholds
- Suppress alerts caused by low sample sizes during off-peak hours
