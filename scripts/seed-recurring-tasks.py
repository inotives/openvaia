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

    # ROBIN — Trading Operations Engineer
    {
        "key": "ROB-001",
        "title": "System Health Check",
        "description": (
            "Run system health check: verify DB connections, check container status, "
            "review recent error logs, check disk usage. Report any anomalies."
        ),
        "assigned_to": "robin",
        "priority": "medium",
        "tags": ["schedule:daily@09:30", "operations", "monitoring"],
        "schedule_at": "01:30",  # 09:30 SGT
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
        "tags": ["schedule:daily@18:00", "operations", "reporting"],
        "schedule_at": "10:00",  # 18:00 SGT
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
        "schedule_at": "02:00",  # MON 10:00 SGT
        "recurrence_minutes": 10080,  # 7 days
    },
    {
        "key": "ROB-004",
        "title": "Review Mission Board",
        "description": (
            "Check mission board for unclaimed backlog tasks. If any match your skills "
            "(coding, infrastructure, operations), self-assign and start working."
        ),
        "assigned_to": "robin",
        "priority": "low",
        "tags": ["schedule:daily@08:00", "operations", "tasks"],
        "schedule_at": "00:00",  # 08:00 SGT
        "recurrence_minutes": 1440,
    },
]


def main():
    force = "--force" in sys.argv

    schema = os.environ.get("PLATFORM_SCHEMA", "platform")

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
