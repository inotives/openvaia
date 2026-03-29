---
name: cloud_cost_optimization
description: Analyze cloud spending, identify waste, recommend right-sizing, and forecast costs across AWS/GCP/Azure.
tags: [devops, cloud, cost, optimization]
source: awesome-openclaw-agents/agents/devops/cost-optimizer
---

## Cloud Cost Optimization

> ~496 tokens

### Cost Analysis Workflow

1. Analyze current spending by service, team, and environment
2. Identify idle, underutilized, and over-provisioned resources
3. Calculate potential savings with confidence levels
4. Prioritize recommendations by savings amount (highest first)
5. Generate implementation plan with CLI commands

### Savings Opportunity Categories

#### Right-Sizing

- Compare actual utilization vs. provisioned capacity
- Flag resources where CPU avg < 20% or memory avg < 30%
- Recommend specific instance type downgrades with expected savings

#### Idle Resource Detection

- Unattached EBS volumes (no instance for 30+ days)
- Unused Elastic IPs
- Idle load balancers with zero traffic
- Old snapshots (>90 days)
- Dev/staging instances running 24/7

#### Reserved Instances / Savings Plans

- Identify stable workloads suitable for reservations
- Calculate break-even points for 1-year vs. 3-year commitments
- Compare no upfront vs. partial upfront vs. all upfront pricing

#### Spot Instances

- Identify fault-tolerant workloads suitable for spot instances
- Calculate savings vs. on-demand pricing

### Cost Report Format

```
Cost Optimization Report -- <month>

Total Spend (MTD): $<amount>
Identified Savings: $<amount>/month (<percent>%)

Top Savings Opportunities:
| # | Resource | Current Cost | Savings | Confidence |
|---|----------|-------------|---------|------------|
```

### Spending Trend Analysis

Track month-over-month by category:
- Compute (EC2/ECS/Lambda)
- Database (RDS/DynamoDB)
- Network (NAT/LB/data transfer)
- Storage (S3/EBS)

Flag categories growing faster than revenue growth.

### Rules

- Always show both the current cost and the potential savings amount
- Include confidence level for savings estimates (high/medium/low)
- Never recommend cost cuts that would compromise reliability without explicit warnings
- Prioritize recommendations by savings amount, highest first
- Distinguish quick wins (<1 hour to implement) from larger projects
