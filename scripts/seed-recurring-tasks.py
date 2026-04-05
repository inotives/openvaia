#!/usr/bin/env python3
"""Seed recurring tasks for proactive agent behavior.

Creates scheduled tasks for each agent. Safe to re-run — skips existing keys.

Usage:
    python3 scripts/seed-recurring-tasks.py
    python3 scripts/seed-recurring-tasks.py --force   # delete and re-create all
"""

import os
import sys

import psycopg

# Recurring task definitions
# schedule_at is in UTC (SGT = UTC+8)
RECURRING_TASKS = [
    # INO — Global Financial Researcher
    {
        "key": "INO-001",
        "title": "Morning Market Brief",
        "description": (
            "Compile a brief summary of overnight market movements: BTC, ETH, gold, S&P 500. "
            "Include key price levels, notable news, and sentiment indicators. Post findings as a research report."
        ),
        "assigned_to": "ino",
        "priority": "medium",
        "tags": ["schedule:daily@09:00", "research", "markets"],
        "schedule_at": "01:00",  # 09:00 SGT
        "recurrence_minutes": 1440,
    },
    {
        "key": "INO-002",
        "title": "End of Day Market Summary",
        "description": (
            "Summarize the day's market activity: price changes, volume, notable events. "
            "Compare with morning brief. Post as research report."
        ),
        "assigned_to": "ino",
        "priority": "medium",
        "tags": ["schedule:daily@17:00", "research", "markets"],
        "schedule_at": "09:00",  # 17:00 SGT
        "recurrence_minutes": 1440,
    },
    {
        "key": "INO-003",
        "title": "Price Alert Monitor",
        "description": (
            "Check top 5 crypto assets (BTC, ETH, SOL, PAXG, XAU) for >5% price movements "
            "in the last hour. If significant movement detected, post alert with analysis to Discord."
        ),
        "assigned_to": "ino",
        "priority": "high",
        "tags": ["schedule:hourly", "monitoring", "alerts"],
        "schedule_at": None,  # interval-based, no fixed time
        "recurrence_minutes": 60,
    },
    {
        "key": "INO-004",
        "title": "Resource Discovery",
        "description": (
            "Check curated resources for new research material. Search for recent reports, "
            "data sources, or tools relevant to crypto and macro research."
        ),
        "assigned_to": "ino",
        "priority": "low",
        "tags": ["schedule:daily@12:00", "research", "resources"],
        "schedule_at": "04:00",  # 12:00 SGT
        "recurrence_minutes": 1440,
    },

    # ROBIN — Operations
    {
        "key": "ROB-001",
        "title": "System Health Check",
        "description": (
            "Run system health check: verify DB connections, check poller status "
            "(cli.market poller-status), review recent error logs. Report any anomalies to Discord."
        ),
        "assigned_to": "robin",
        "priority": "medium",
        "tags": ["schedule:daily@01:30", "operations", "monitoring"],
        "schedule_at": "01:30",
        "recurrence_minutes": 1440,
    },
    {
        "key": "ROB-002",
        "title": "Daily Operations Log",
        "description": (
            "Review what ran today: heartbeat cycles, tasks processed, messages handled, "
            "any errors or timeouts. Write a brief operations log."
        ),
        "assigned_to": "robin",
        "priority": "low",
        "tags": ["schedule:daily@22:00", "operations", "reporting"],
        "schedule_at": "22:00",
        "recurrence_minutes": 1440,
    },
    {
        "key": "ROB-003",
        "title": "Weekly Engineering Retro",
        "description": (
            "Run weekly engineering retrospective: analyze git commits, work sessions, "
            "shipping streaks. Use the engineering_retro skill. Post report."
        ),
        "assigned_to": "robin",
        "priority": "medium",
        "tags": ["schedule:weekly@MON:10:00", "retrospective", "team"],
        "schedule_at": "10:00",
        "recurrence_minutes": 10080,
    },
    {
        "key": "ROB-004",
        "title": "Review Mission Board",
        "description": (
            "Check mission board for unclaimed backlog tasks. If any match your skills "
            "(coding, infrastructure, operations, trading), self-assign and start working. "
            "Follow the task_management skill: check WHY, WHAT, FOLLOW-UP."
        ),
        "assigned_to": "robin",
        "priority": "low",
        "tags": ["schedule:daily@08:00", "operations", "tasks"],
        "schedule_at": "08:00",
        "recurrence_minutes": 1440,
    },

    # ROBIN — Trading: DCA Grid + Signal Scan
    {
        "key": "ROB-010",
        "title": "Hourly Trading Decisions",
        "description": (
            "Hourly trading decision loop. Grid monitoring is handled by TA poller (every 60s, no LLM). "
            "Robin focuses on decisions that need reasoning: "
            "1. cli.grid status — check if any cycles need opening, regime transitions, or adjustments. "
            "2. For each asset with no active grid cycle: evaluate entry conditions → cli.grid open if conditions pass. "
            "3. Check regime score: if RS crossed 65 → cancel unfilled grid levels, note for trend follow. "
            "4. cli.signals scan — check swing strategies (momentum, trend follow) for entry signals. "
            "5. If signal found and guards pass, execute trade per trading_signal_workflow skill. "
            "6. If blocked by filters, log reason and wait."
        ),
        "assigned_to": "robin",
        "priority": "high",
        "tags": ["schedule:hourly", "trading", "signals", "grid"],
        "schedule_at": None,
        "recurrence_minutes": 60,
    },
    {
        "key": "ROB-011",
        "title": "Daily Market Overview + Sentiment + P&L",
        "description": (
            "Daily trading review with sentiment analysis. "
            "1. cli.market overview — check prices, regime, TA for all assets. "
            "2. cli.market fetch-sentiment — fetch Fear & Greed Index. "
            "3. Read top crypto headlines (browser tool) and score sentiment. "
            "   Store score: cli.market sentiment --news-score <score>. "
            "4. cli.portfolio pnl --period today — review today's P&L. "
            "5. cli.portfolio balance — check positions across venues. "
            "6. cli.grid status — review active/expired grid cycles. "
            "7. cli.portfolio snapshot — take daily snapshot. "
            "8. Post to Discord: daily P&L + sentiment summary + grid cycle status."
        ),
        "assigned_to": "robin",
        "priority": "medium",
        "tags": ["schedule:daily@10:00", "trading", "portfolio", "market"],
        "schedule_at": "10:00",
        "recurrence_minutes": 1440,
    },
    {
        "key": "ROB-012",
        "title": "Daily Data Refresh",
        "description": (
            "Fetch latest data and recompute indicators. "
            "1. cli.market fetch-daily — fetch daily OHLCV from CoinGecko for all assets. "
            "2. cli.market compute-daily-ta — recompute daily TA indicators. "
            "3. cli.market fetch-sentiment — update Fear & Greed Index. "
            "4. cli.market coverage — check for data gaps. "
            "5. cli.market sync-fees — sync trading fees from exchange."
        ),
        "assigned_to": "robin",
        "priority": "medium",
        "tags": ["schedule:daily@02:00", "trading", "data"],
        "schedule_at": "02:00",
        "recurrence_minutes": 1440,
    },
    {
        "key": "ROB-013",
        "title": "Weekly Trading Performance Review",
        "description": (
            "Weekly review of all trading activity. "
            "1. cli.portfolio pnl --period week — weekly P&L. "
            "2. cli.portfolio benchmark --days 7 — strategy vs HODL. "
            "3. cli.grid status — review all grid cycles (active, expired, closed). "
            "4. cli.market sentiment — check 7-day sentiment trend. "
            "5. Review each strategy: win rate, consecutive losses, drawdown. "
            "6. If any strategy has 3+ consecutive losses → deactivate and report. "
            "7. If grid fill rate is low → consider adjusting grid spacing. "
            "8. Post weekly summary to Discord with CONTINUE/PAUSE/ADJUST per strategy."
        ),
        "assigned_to": "robin",
        "priority": "medium",
        "tags": ["schedule:weekly@SUN:12:00", "trading", "review"],
        "schedule_at": "12:00",
        "recurrence_minutes": 10080,
    },
    {
        "key": "ROB-014",
        "title": "Weekly Backtest Re-evaluation",
        "description": (
            "Re-run backtests with latest data for active strategies. "
            "1. cli.backtest run --strategy <name> --from <6mo_ago> --to today — for each active strategy. "
            "2. Compare with previous backtest. If performance degrading, run param sweep. "
            "3. Check if grid params need updating based on changed volatility regime. "
            "4. Report findings to Discord with recommendations."
        ),
        "assigned_to": "robin",
        "priority": "low",
        "tags": ["schedule:weekly@SUN:13:00", "trading", "backtest"],
        "schedule_at": "13:00",
        "recurrence_minutes": 10080,
    },
]


def main():
    force = "--force" in sys.argv

    schema = os.environ.get("PLATFORM_SCHEMA", "openvaia")

    with psycopg.connect(
        host=os.environ["POSTGRES_HOST"],
        port=int(os.environ.get("POSTGRES_PORT", "5432")),
        user=os.environ["POSTGRES_USER"],
        password=os.environ["POSTGRES_PASSWORD"],
        dbname=os.environ["POSTGRES_DB"],
        autocommit=True,
    ) as conn:
        if force:
            keys = [t["key"] for t in RECURRING_TASKS]
            placeholders = ",".join(["%s"] * len(keys))
            conn.execute(
                f"DELETE FROM {schema}.tasks WHERE key IN ({placeholders})", keys
            )
            print(f"Deleted {len(keys)} recurring tasks (--force)")

        created = 0
        skipped = 0
        for task in RECURRING_TASKS:
            # Check if already exists
            cur = conn.execute(
                f"SELECT 1 FROM {schema}.tasks WHERE key = %s", (task["key"],)
            )
            if cur.fetchone():
                print(f"  SKIP {task['key']} — already exists")
                skipped += 1
                continue

            conn.execute(
                f"""INSERT INTO {schema}.tasks
                    (key, title, description, status, priority, assigned_to, created_by,
                     tags, schedule_at, recurrence_minutes)
                    VALUES (%s, %s, %s, 'done', %s, %s, 'system', %s, %s, %s)""",
                (
                    task["key"],
                    task["title"],
                    task["description"],
                    task["priority"],
                    task["assigned_to"],
                    task["tags"],
                    task["schedule_at"],
                    task["recurrence_minutes"],
                ),
            )
            print(f"  OK   {task['key']} — {task['title']}")
            created += 1

        print(f"\nDone: {created} created, {skipped} skipped")


if __name__ == "__main__":
    main()
