#!/usr/bin/env python3
"""Seed skill chains for dynamic skill equipping.

Creates default skill chains that map task types to ordered skill sequences.
Safe to re-run — skips existing chains.

Usage:
    python3 scripts/seed-skill-chains.py
    python3 scripts/seed-skill-chains.py --force   # delete and re-create all
"""

import json
import os
import sys

import psycopg

SKILL_CHAINS = [
    # === CODING CHAINS ===
    {
        "name": "coding_low",
        "description": "Quick fix, small bug, config change — minimal planning",
        "match_tags": ["feature:low", "fix:low"],
        "match_keywords": ["quick fix", "typo", "config", "minor"],
        "steps": [
            {"phase": "plan", "skills": ["writing_plans"]},
            {"phase": "implement", "skills": ["test_driven_development"]},
            {"phase": "verify", "skills": ["verification_before_completion"]},
            {"phase": "ship", "skills": ["finishing_dev_branch"]},
        ],
    },
    {
        "name": "coding_medium",
        "description": "New endpoint, UI page, integration — structured planning with spec",
        "match_tags": ["feature:medium", "feature"],
        "match_keywords": ["add", "create", "implement", "build", "new"],
        "steps": [
            {"phase": "propose", "skills": ["spec_driven_proposal"], "gate": "human_approval"},
            {"phase": "specify", "skills": ["requirement_specification"]},
            {"phase": "plan", "skills": ["writing_plans"]},
            {"phase": "implement", "skills": ["test_driven_development"]},
            {"phase": "review", "skills": ["pre_landing_review"]},
            {"phase": "verify", "skills": ["spec_verification"]},
            {"phase": "ship", "skills": ["ship_workflow"]},
        ],
    },
    {
        "name": "coding_high",
        "description": "New system, multi-component, architecture change — full planning pipeline",
        "match_tags": ["feature:high", "feature:large", "architecture"],
        "match_keywords": ["system", "architecture", "redesign", "platform", "migration"],
        "steps": [
            {"phase": "brainstorm", "skills": ["brainstorming"]},
            {"phase": "propose", "skills": ["spec_driven_proposal"], "gate": "human_approval"},
            {"phase": "specify", "skills": ["requirement_specification"]},
            {"phase": "design", "skills": ["technical_design_doc"], "gate": "human_approval"},
            {"phase": "plan", "skills": ["writing_plans"]},
            {"phase": "implement", "skills": ["subagent_driven_development", "test_driven_development"]},
            {"phase": "review", "skills": ["pre_landing_review"]},
            {"phase": "verify", "skills": ["spec_verification"]},
            {"phase": "ship", "skills": ["ship_workflow", "finishing_dev_branch"]},
        ],
    },

    # === BUGFIX CHAINS ===
    {
        "name": "bugfix_simple",
        "description": "Simple bug — debug, fix, verify",
        "match_tags": ["bugfix", "fix", "bug"],
        "match_keywords": ["bug", "fix", "broken", "error", "crash", "fail"],
        "steps": [
            {"phase": "debug", "skills": ["systematic_debugging"]},
            {"phase": "implement", "skills": ["test_driven_development"]},
            {"phase": "verify", "skills": ["verification_before_completion"]},
        ],
    },
    {
        "name": "bugfix_complex",
        "description": "Complex bug (3+ failed attempts) — rethink approach",
        "match_tags": ["bugfix:complex", "bug:complex"],
        "match_keywords": [],
        "steps": [
            {"phase": "debug", "skills": ["systematic_debugging"]},
            {"phase": "brainstorm", "skills": ["brainstorming"]},
            {"phase": "propose", "skills": ["spec_driven_proposal"]},
            {"phase": "plan", "skills": ["writing_plans"]},
            {"phase": "implement", "skills": ["test_driven_development"]},
            {"phase": "verify", "skills": ["spec_verification"]},
        ],
    },

    # === RESEARCH CHAINS ===
    {
        "name": "research_quick",
        "description": "Quick research — check resources, report findings",
        "match_tags": ["research"],
        "match_keywords": ["research", "investigate", "analyze", "find", "look into"],
        "steps": [
            {"phase": "research", "skills": ["research_methodology"]},
            {"phase": "report", "skills": ["report_format"]},
        ],
    },
    {
        "name": "research_deep",
        "description": "Deep research — methodology, literature review, market intelligence",
        "match_tags": ["research:deep", "analysis"],
        "match_keywords": ["deep dive", "comprehensive", "thorough", "market analysis"],
        "steps": [
            {"phase": "research", "skills": ["research_methodology"]},
            {"phase": "literature", "skills": ["literature_review"]},
            {"phase": "analysis", "skills": ["market_intelligence"]},
            {"phase": "report", "skills": ["report_format"]},
        ],
    },

    # === SECURITY CHAINS ===
    {
        "name": "security_audit",
        "description": "Security audit — OWASP, vulnerabilities, access control",
        "match_tags": ["security", "audit"],
        "match_keywords": ["security", "audit", "vulnerability", "pentest"],
        "steps": [
            {"phase": "audit", "skills": ["security_audit"]},
            {"phase": "scan", "skills": ["vulnerability_scanning"]},
            {"phase": "access", "skills": ["access_audit"]},
            {"phase": "report", "skills": ["report_format"]},
        ],
    },

    # === OPERATIONS CHAINS ===
    {
        "name": "ops_deployment",
        "description": "Ship and deploy — PR, canary, benchmark",
        "match_tags": ["deploy", "ship", "release"],
        "match_keywords": ["deploy", "ship", "release", "launch"],
        "steps": [
            {"phase": "ship", "skills": ["ship_workflow"]},
            {"phase": "monitor", "skills": ["canary_monitoring"]},
            {"phase": "benchmark", "skills": ["performance_benchmark"]},
        ],
    },
    {
        "name": "ops_incident",
        "description": "Incident response — debug, analyze logs, monitor",
        "match_tags": ["incident", "outage"],
        "match_keywords": ["incident", "outage", "down", "emergency"],
        "steps": [
            {"phase": "respond", "skills": ["incident_response"]},
            {"phase": "debug", "skills": ["systematic_debugging"]},
            {"phase": "logs", "skills": ["log_analysis"]},
            {"phase": "monitor", "skills": ["deployment_monitoring"]},
        ],
    },

    # === TRADING CHAINS (robin-specific) ===
    {
        "name": "trading_analysis",
        "description": "Market analysis — technical analysis, intelligence, report",
        "match_tags": ["trading:analysis", "trading", "market"],
        "match_keywords": ["market", "price", "trading", "crypto", "gold"],
        "steps": [
            {"phase": "analyze", "skills": ["trading_analysis"]},
            {"phase": "intelligence", "skills": ["market_intelligence"]},
            {"phase": "report", "skills": ["report_format"]},
        ],
    },
    {
        "name": "trading_execution",
        "description": "Trade execution — analysis, operations, risk management",
        "match_tags": ["trading:execution", "trade"],
        "match_keywords": ["execute", "buy", "sell", "position", "rebalance"],
        "steps": [
            {"phase": "analyze", "skills": ["trading_analysis"]},
            {"phase": "execute", "skills": ["trading_operations"]},
            {"phase": "risk", "skills": ["portfolio_rebalancing", "risk_assessment"]},
        ],
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
            conn.execute(f"DELETE FROM {schema}.skill_chains")
            print(f"Deleted all skill chains (--force)")

        created = 0
        skipped = 0
        for chain in SKILL_CHAINS:
            cur = conn.execute(
                f"SELECT 1 FROM {schema}.skill_chains WHERE name = %s", (chain["name"],)
            )
            if cur.fetchone():
                print(f"  SKIP {chain['name']} — already exists")
                skipped += 1
                continue

            conn.execute(
                f"""INSERT INTO {schema}.skill_chains
                    (name, description, match_tags, match_keywords, steps)
                    VALUES (%s, %s, %s, %s, %s)""",
                (
                    chain["name"],
                    chain["description"],
                    chain["match_tags"],
                    chain["match_keywords"],
                    json.dumps(chain["steps"]),
                ),
            )
            print(f"  OK   {chain['name']} — {chain['description'][:60]}")
            created += 1

        print(f"\nDone: {created} created, {skipped} skipped")


if __name__ == "__main__":
    main()
