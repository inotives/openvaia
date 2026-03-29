---
name: trading_operations
description: General trading ops — data health checks, cycle monitoring, asset management
tags: [trading, ops]
source: openvaia/v1-migration-seed
---

## Trading Operations

> ~263 tokens
When working on trading repos, use the repo's management CLIs for operations:

### Data Health
Check data pipeline freshness and indicator computation:
```
shell(command="cd /workspace/repos/<repo-name> && make daily-data", timeout=600)
```

### Trading Cycle Monitoring
Check active trading cycles, positions, and order status:
```
shell(command="cd /workspace/repos/<repo-name> && python -m common.tools.manage_trading --json list-active")
```
Watch for: stale cycles, abnormal positions, failed orders.

### Asset Management
Allowlist assets, verify exchange mappings, check data coverage:
```
shell(command="cd /workspace/repos/<repo-name> && python -m common.tools.manage_assets --json list")
```

### Key Rules
- **No live trades without explicit Boss approval** -- use paper trading for testing
- **No modifying position sizes or risk params** beyond Boss-approved limits
- Always read the repo's CLAUDE.md before working -- it has critical safety rules
- Run tests before pushing any code changes
