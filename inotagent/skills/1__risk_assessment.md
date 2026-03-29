---
name: risk_assessment
description: Identify, score, and prioritize enterprise risks with mitigation plans across operational, financial, strategic, and compliance categories.
tags: [compliance, risk, governance, planning]
source: awesome-openclaw-agents/agents/compliance/risk-assessor
---

## Risk Assessment

> ~531 tokens

### Risk Categories

- **Operational:** Key-person dependency, process failures, system outages
- **Financial:** Currency exposure, cash flow, credit risk
- **Strategic:** Market changes, competitor moves, technology shifts
- **Compliance:** Regulatory requirements, data protection, audit gaps
- **Reputational:** Public perception, customer trust, media risk

### Risk Scoring Matrix

Score = Likelihood (1-5) x Impact (1-5)

| Score Range | Level | Response |
|-------------|-------|----------|
| 16-25 | Critical | Immediate action required |
| 10-15 | High | Action plan within 1 week |
| 5-9 | Medium | Monitor and plan |
| 1-4 | Low | Accept or monitor |

### Risk Register Format

```
Risk Assessment -- <context>

| # | Risk | Category | Likelihood | Impact | Score | Priority |
|---|------|----------|-----------|--------|-------|----------|

Scoring: Likelihood (1-5) x Impact (1-5)
```

### Mitigation Strategies

| Strategy | When to Use |
|----------|-------------|
| **Avoid** | Eliminate the activity causing the risk |
| **Transfer** | Insurance, hedging, outsourcing |
| **Reduce** | Controls, processes, technology to lower likelihood or impact |
| **Accept** | Risk is within tolerance; document and monitor |

### Mitigation Plan Template

```
Risk: <description> (Score: <N>)
Strategy: <Avoid/Transfer/Reduce/Accept>
Actions:
- <specific action>
Owner: <person/team>
Cost: <estimated cost>
Deadline: <date>
Success Criteria: <measurable outcome>
```

### Assessment Rules

- Use consistent scoring scales and explain the methodology
- Consider both inherent risk (before controls) and residual risk (after controls)
- Include second-order effects and risk interdependencies
- Present risk acceptance as a valid strategy when appropriate
- Do not exaggerate risks to create unnecessary alarm
- Do not ignore low-probability, high-impact events (tail risks)
- Do not treat risk assessment as a one-time exercise
- Always include cost-benefit consideration in mitigation plans
