---
name: experiment_design
description: Hypothesis framework, A/B test methodology, sample size planning, and results analysis workflow
tags: [experimentation, analytics, testing, data-driven]
source: agency-agents/project-management/project-management-experiment-tracker
---

## Experiment Design & Analysis

> ~903 tokens

### Hypothesis Framework

Every experiment starts with a structured hypothesis:

1. **Problem Statement** - Clear issue or opportunity backed by data
2. **Hypothesis** - Testable prediction: "If [change], then [metric] will [direction] by [threshold]"
3. **Primary Metric** - Single KPI with success threshold
4. **Guardrail Metrics** - Secondary measurements that must not degrade

### Experiment Design Template

```
# Experiment: [Name]

## Hypothesis
- Problem: [what data shows]
- Prediction: [if X then Y]
- Primary metric: [KPI + success threshold]
- Guardrail metrics: [metrics that must not regress]

## Design
- Type: [A/B | Multi-variate | Feature flag rollout]
- Population: [target segment + criteria]
- Sample size: [users per variant for 80% power at 95% confidence]
- Duration: [minimum runtime]
- Variants:
  - Control: [current experience]
  - Variant A: [treatment + rationale]

## Risk Assessment
- Potential risks: [negative impact scenarios]
- Mitigation: [safety monitoring + rollback plan]
- Go/No-go thresholds: [decision criteria]

## Implementation
- Technical requirements: [dev + instrumentation needs]
- Launch plan: [soft launch -> full rollout]
- Monitoring: [dashboards + alerts]
```

### Sample Size Checklist

- [ ] Define minimum detectable effect (MDE) based on business value
- [ ] Set statistical power (default: 80%)
- [ ] Set confidence level (default: 95%)
- [ ] Account for baseline conversion rate
- [ ] Calculate required users per variant
- [ ] Estimate calendar time to reach sample size
- [ ] Apply multiple comparison correction if >2 variants

### A/B Test Methodology

1. **Pre-launch**: Validate instrumentation with A/A test or logging check
2. **Randomization**: Ensure random user assignment, check for bias
3. **No peeking**: Do not stop early without pre-defined early stopping rules
4. **Duration**: Run for full business cycles (min 1-2 weeks) to capture variance
5. **Corrections**: Apply Bonferroni or similar when testing multiple variants/metrics

### Results Analysis Workflow

```
1. Data quality check
   - Verify sample sizes match expectations
   - Check for logging gaps or anomalies
   - Confirm balanced assignment across variants

2. Statistical analysis
   - Calculate point estimates + confidence intervals
   - Run appropriate test (t-test, chi-square, Mann-Whitney)
   - Report p-value AND practical effect size
   - Perform segment analysis (device, geo, user cohort)

3. Decision framework
   - Significant + meaningful effect -> SHIP
   - Significant + trivial effect -> EVALUATE cost/benefit
   - Not significant -> DO NOT SHIP (or extend runtime)
   - Negative guardrail impact -> STOP regardless of primary

4. Documentation
   - Record decision + rationale
   - Log unexpected findings
   - Update organizational knowledge base
```

### Results Report Template

```
# Results: [Experiment Name]

## Decision: [Ship / Don't Ship / Extend]
- Primary metric: [X% change, CI: Y-Z%, p=N]
- Guardrail metrics: [all within tolerance / flagged]
- Business impact: [estimated annual effect]

## Analysis
- Sample: [N per variant, duration]
- Method: [statistical test used]
- Segments: [any differential effects]

## Learnings
- Key finding: [main takeaway]
- Unexpected: [surprises]
- Follow-up: [next experiments or iterations]
```

### Experiment Safety Rules

- [ ] Rollback procedure documented before launch
- [ ] Real-time monitoring for user experience degradation
- [ ] Privacy compliance verified (data collection, consent)
- [ ] Maximum exposure limit set for high-risk experiments
- [ ] Escalation path defined for anomalous results
