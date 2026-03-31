# ES-0011 — Autonomous Trading Agent

## Status: DRAFT

## Objective

Give Robin (Trading Operations Engineer) a live crypto.com trading account with 1000 CRO tokens. Robin autonomously trades to grow the portfolio using defined strategies and hard guardrails.

## Approach

Fork the existing [inotives/inotives_cryptos](https://github.com/inotives/inotives_cryptos) repo as Robin's trading repo. This is a production-ready crypto trading system with:
- **ccxt** exchange integration (crypto.com + paper mode)
- **DCA Grid** strategy (1860 lines, volatility-adaptive, fee-corrected)
- **Trend Following** strategy (838 lines, regime-switching, trailing stops)
- **Hybrid capital coordinator** (regime score → dynamic allocation)
- **16+ technical indicators** (ATR, RSI, EMA, MACD, Bollinger, ADX)
- **Data pipeline** (CoinGecko → OHLCV → indicators → regime)
- **Non-interactive CLIs** with JSON output (agent-friendly automation)
- **Paper trading mode** (simulated fills with live market data)
- **27 DB migrations** with full audit trail

No need to build from scratch — Robin operates and improves the existing system.

## Architecture

```
GitHub: inotives/inotives_cryptos (Robin's trading repo)
    ├─ bots/
    │   ├─ data_bot/          — daily pipeline: OHLCV → indicators → regime
    │   ├─ pricing_bot/       — live price ticker polling (60s)
    │   └─ trader_bot/        — strategy dispatcher + hybrid coordinator
    │       └─ strategies/
    │           ├─ base.py         — abstract strategy interface
    │           ├─ dca_grid.py     — volatility-adaptive DCA grid
    │           └─ trend_following.py — momentum + trailing stop
    ├─ common/
    │   ├─ connections/       — exchange layer (ccxt, paper mode)
    │   ├─ data/              — indicators, regime scoring, OHLCV
    │   ├─ config.py          — pydantic settings (env-driven)
    │   └─ tools/             — CLIs: manage_assets, manage_trading, manage_cron
    ├─ db/migrations/         — 27 SQL migrations
    ├─ guardrails.py          — HUMAN-AUTHORED safety limits (PR-protected)
    └─ tests/

Robin's Workspace: /workspace/robin/inotives_cryptos/ (cloned repo)
    └─ Robin operates, monitors, and improves here
```

**Robin's daily workflow:**
1. Run data pipeline via shell: `python -m bots.data_bot.main`
2. Monitor prices: `python -m bots.pricing_bot.main --pair cro/usdt`
3. Execute strategies: `python -m bots.trader_bot.main --paper`
4. Check results: `python -m common.tools.manage_trading list-cycles --json`
5. Adjust params: `python -m common.tools.manage_trading update --strategy-id X --param risk_pct=1.0`
6. If strategy improvement found → create branch, test, submit PR

## Code Access Model

Robin can modify code, but with boundaries enforced via GitHub branch protection and CODEOWNERS:

**Robin CAN change (via PR, human reviews):**

| Area | What | Why Allowed |
|------|------|-------------|
| Strategy files (`strategies/*.py`) | Add new strategies, tune existing logic | Core of Robin's job |
| Indicators (`data/indicators.py`) | Add new technical indicators | Extends analysis capability |
| Regime scoring (`data/market_regime.py`) | Tune weights, add signals | Improves capital allocation |
| Strategy params (via CLI) | Adjust risk_pct, stop distances, thresholds | Runtime tuning, no code change |
| New scripts in `bots/` | Custom monitoring, reporting | Operational tooling |
| Tests (`tests/`) | Add/improve test coverage | Quality improvement |

**Robin CANNOT change (requires human approval via CODEOWNERS):**

| Area | What | Why Protected |
|------|------|---------------|
| `guardrails.py` | Position limits, daily loss cap, stop-loss rules | Safety-critical — LLM must not weaken limits |
| `common/connections/` | Exchange connectivity layer | Core infra — bad change = lost funds |
| `common/db.py` | Database connection pool | Core infra |
| `common/config.py` | Configuration model | Security-sensitive |
| `db/migrations/` | Schema changes | Data integrity |
| `.env*` files | Credentials | Security |

**GitHub enforcement:**
```
# .github/CODEOWNERS
guardrails.py                @inotives
common/connections/           @inotives
common/db.py                  @inotives
common/config.py              @inotives
db/migrations/                @inotives
```

Branch protection on `main`: require PR + 1 approval, no direct push.

## Implementation Phases

### Phase 1: Infrastructure Setup

**Create `inotives/robin-trading` repo:**
- Add `guardrails.py` to `inotives/inotives_cryptos` (human-authored safety limits)
- Add `.github/CODEOWNERS` with protected paths (guardrails, connections, db, config)
- Enable branch protection on `main` (require PR + approval)
- Add `tests/test_guardrails.py` for safety limit validation

**Register repo for Robin:**
```bash
make repo-add URL=https://github.com/inotives/inotives_cryptos NAME=inotives_cryptos TO=robin BY=boss
```
Robin auto-clones on boot to `/workspace/robin/inotives_cryptos/`

**Dependencies (already in repo):**
- `ccxt`, `pandas`, `pandas-ta`, `asyncpg` — already in `pyproject.toml`
- Robin installs via: `cd /workspace/robin/inotives_cryptos && pip install -e .`

**Exchange credentials:**
- Add to `agents/robin/.env`:
  ```env
  CRYPTOCOM_API_KEY=<key>
  CRYPTOCOM_API_SECRET=<secret>
  TRADING_MODE=paper
  ```
- Repo's `common/config.py` already reads from env vars via pydantic-settings

**Database:**
- Trading uses its own schema (`inotives_tradings`) in the shared Postgres
- Robin runs migrations: `dbmate -d db/migrations up`
- Robin seeds assets: `python -m common.tools.manage_assets add-asset --coingecko-id crypto-com-chain`

### Phase 2: Trading Skills

#### `1__inotives_cryptos_operations.md`
Teach Robin how to operate the existing trading system:
- **Data pipeline:** `python -m bots.data_bot.main` — daily OHLCV → indicators → regime
- **Pricing bot:** `python -m bots.pricing_bot.main --pair cro/usdt --interval 60`
- **Trader bot:** `python -m bots.trader_bot.main --paper` (or `--live`)
- **Asset management:** `python -m common.tools.manage_assets` (non-interactive JSON mode)
- **Trading management:** `python -m common.tools.manage_trading` (list/view/update strategies)
- **Paper vs live:** `TRADING_MODE` env var controls execution mode
- **Error handling:** Rate limits, network errors, insufficient funds

#### `1__trading_strategy_cro.md`
CRO-specific strategy configuration for the existing DCA Grid + Trend Following system:
- **Asset:** CRO/USDT on crypto.com
- **DCA Grid params:** grid levels, ATR multipliers, profit targets per volatility regime
- **Trend Following params:** entry conditions (RSI, EMA, ADX, regime score), stop distances
- **Capital allocation:** Regime score drives split between grid (sideways) and trend (momentum)
- **Risk limits:** max capital per cycle, reserve %, stop-loss distances
- How to tune params via CLI: `manage_trading update --strategy-id X --param risk_pct=1.0`

#### `1__trade_execution_safety.md`
Hard guardrails + pre/post-trade checklist:
- **Pre-trade:** Check balance, verify guardrails pass, log rationale to memory
- **During:** Monitor fills, verify stop-loss placed, check circuit breakers
- **Post-trade:** Verify execution, log to trade journal, report to Discord
- **Always:** Use `guardrails.py` validation before any order placement
- **Never:** Bypass guardrails, trade without stop-loss, exceed position limits

#### `1__portfolio_tracking.md`
Daily portfolio management:
- Query trade cycles: `manage_trading list-cycles --json`
- Track: starting balance, current balance, unrealized P&L, realized P&L
- Daily performance report (% change, win rate, avg trade size)
- Weekly summary comparing against CRO HODL benchmark
- Store reports via `research_store` tool

### Phase 3: Hard Guardrails (Code-Level)

**Human creates** `guardrails.py` in the initial repo commit. Robin cannot merge changes to this file without human PR approval. All trade scripts must import it:

```python
# /workspace/robin/trading/guardrails.py

MAX_POSITION_PCT = 0.10       # 10% of portfolio per trade
MAX_DAILY_LOSS_PCT = 0.05     # 5% daily loss limit
MAX_OPEN_POSITIONS = 3        # max concurrent positions
STOP_LOSS_PCT = 0.05          # 5% mandatory stop-loss
MIN_TRADE_SIZE = 10           # minimum 10 CRO per trade
HUMAN_APPROVAL_THRESHOLD = 0.20  # 20% of portfolio needs human approval

def validate_trade(balance, trade_amount, open_positions, daily_pnl):
    """Returns (allowed: bool, reason: str)"""
    if trade_amount > balance * MAX_POSITION_PCT:
        return False, f"Position too large: {trade_amount} > {balance * MAX_POSITION_PCT}"
    if abs(daily_pnl) > balance * MAX_DAILY_LOSS_PCT:
        return False, f"Daily loss limit reached: {daily_pnl}"
    if open_positions >= MAX_OPEN_POSITIONS:
        return False, f"Max open positions reached: {open_positions}"
    if trade_amount > balance * HUMAN_APPROVAL_THRESHOLD:
        return False, f"Needs human approval: {trade_amount} > 20% of portfolio"
    return True, "OK"
```

**These limits are in code, not in prompts — the LLM cannot bypass them.**

### Phase 4: Paper Trading

Before live trading, Robin runs in paper mode:
- Uses ccxt's sandbox/testnet if available, otherwise simulates
- Track simulated trades in a local journal
- Run for 1-2 weeks
- Evaluate: win rate, avg P&L, max drawdown, Sharpe ratio
- Human reviews results before going live

**Paper trading toggle:**
```env
TRADING_MODE=paper   # paper | live
```

Robin's scripts check this and either simulate or execute real orders.

### Phase 5: Live Trading

After paper trading review:
- Switch `TRADING_MODE=live`
- Start with conservative limits (5% position size, 3% daily loss)
- Gradually increase as confidence grows
- Robin reports every trade to Discord immediately
- Daily P&L summary at 18:00 SGT
- Weekly performance review against HODL benchmark

### Phase 6: Recurring Trading Tasks

Add to `seed-recurring-tasks.py`:

| Key | Title | Schedule | Description |
|-----|-------|----------|-------------|
| ROB-010 | Market Analysis | hourly | Fetch CRO price, volume, RSI. Check for entry/exit signals. |
| ROB-011 | Position Monitor | every 15 min | Check open positions, verify stop-losses, check for take-profit levels. |
| ROB-012 | Daily Trading Report | daily@18:00 | P&L summary, trades executed, portfolio vs HODL benchmark. |
| ROB-013 | Weekly Trading Review | weekly@SUN:20:00 | Weekly performance, strategy effectiveness, lessons learned. |

## Implementation Steps

- [ ] Phase 1: Add `guardrails.py` + `.github/CODEOWNERS` to `inotives/inotives_cryptos`
- [ ] Phase 1: Enable branch protection on `main` (require PR + approval)
- [ ] Phase 1: Register repo for Robin via `make repo-add`
- [ ] Phase 1: Add crypto.com credentials to robin's env
- [ ] Phase 1: Robin runs migrations + seeds CRO asset
- [ ] Phase 2: Create `inotives_cryptos_operations` skill
- [ ] Phase 2: Create `trading_strategy_cro` skill
- [ ] Phase 2: Create `trade_execution_safety` skill
- [ ] Phase 2: Create `portfolio_tracking` skill
- [ ] Phase 2: Equip all 4 skills to Robin
- [ ] Phase 3: Human adds `guardrails.py` to repo (PR-protected via CODEOWNERS)
- [ ] Phase 3: Add `tests/test_guardrails.py` — verify limits enforced
- [ ] Phase 3: Robin integrates guardrail checks into trader_bot strategies
- [ ] Phase 4: Paper trading mode for 1-2 weeks
- [ ] Phase 4: Evaluate paper trading results
- [ ] Phase 4: Human review and approval to go live
- [ ] Phase 5: Switch to live mode with conservative limits
- [ ] Phase 5: Monitor first week of live trading closely
- [ ] Phase 6: Add recurring trading tasks

## Guardrails & Safety

| Guardrail | Level | Details |
|-----------|-------|---------|
| Position size limit | Code | Max 10% of portfolio per trade |
| Daily loss limit | Code | Max 5% daily loss, auto-stop trading |
| Stop-loss mandatory | Code | Every position must have stop-loss |
| Max open positions | Code | Max 3 concurrent positions |
| Human approval gate | Code | Trades > 20% of portfolio need Discord approval |
| Paper trading first | Process | 1-2 weeks simulated before live |
| Trade journal | Skill | Every trade logged with rationale |
| Discord reporting | Skill | Every trade reported immediately |
| Weekly review | Task | Mandatory weekly performance review |
| Kill switch | Config | `TRADING_MODE=paper` stops all live trades |
| PR gate for strategy | Git | Robin submits PRs, human reviews before merge |
| Protected guardrails | Git | `guardrails.py` changes require human approval |
| Repo-based iteration | Git | Full git history of strategy evolution |

## Risk Acknowledgment

- This is **real money** (1000 CRO). Robin can lose it.
- Crypto markets are volatile. 1000 CRO can go to 0.
- LLM trading strategies are experimental — no guarantees.
- The guardrails prevent catastrophic loss but not gradual losses.
- Human should review weekly and adjust strategy/limits as needed.

## Dependencies

- [inotives/inotives_cryptos](https://github.com/inotives/inotives_cryptos) — existing trading system with ccxt, strategies, indicators, data pipeline
- [ccxt](https://github.com/ccxt/ccxt) — unified crypto exchange library (MIT license, already in inotives_cryptos)
- crypto.com Exchange account with API access
- Existing inotagent tools: shell, memory, research, Discord, recurring tasks
- ES-0009 (proactive behavior) for autonomous trading task execution

## Success Criteria

- Robin can autonomously execute trades within guardrails
- Paper trading runs for 1-2 weeks with positive or controlled results
- All trades logged, reported, and reviewable
- Portfolio performance tracked against HODL benchmark
- Human can enable/disable trading with a single env var
- No trade executed without stop-loss
- Daily loss limit never exceeded
