# Changelog — feat/multi-agent-v1.2

Branch started: 2026-03-28

## Changes

### ES-0007: Multi-Agent Container & Sub-Agents
- Multi-agent mode: `AGENTS=ino,robin` runs multiple agents in one container, shared DB pool + browser + embedding
- New `Dockerfile.agents` — single image with all agent dirs, `AGENTS` env var controls activation
- `config/env.py` — `load_agent_env()` reads per-agent `.env` into dict (no env var collisions)
- `main.py` refactored: `--agent-dir` (single, backward compatible) + `--agents` (multi-agent)
- Channels use agent env dict for token resolution
- Browser singleton shared across agents
- Per-agent workspace subdirectories (`/workspace/{name}/`)
- `delegate` tool (#20) — sub-agents: spawn ephemeral LLM call with skill as system prompt
- `load_skill_by_name()` in `db/skills.py` for sub-agent skill loading
- Old single-agent services moved to `single-agent` profile in docker-compose
- 350 unit tests (up from 343)

### Migration consolidation
- 22 migrations → 5 clean files (no `cron_jobs` table)
- Cron scheduler disabled in `main.py`, cron seeding removed from `bootstrap.py`
- `make import-skills` — imports 58 skills from `inotagent/skills/` (6 global + 52 non-global)
- `make reset-skill NAME=x` — reset single skill to file version
- `make reimport-skills` — force re-import all skills
- Skill file naming: `0__<name>.md` = global, `1__<name>.md` = non-global

### Skill library (81 total: 3 global + 78 non-global)
- Skills moved from `docs/skills/` to `inotagent/skills/`
- 17 skills recovered from old migration seeds (task workflows, git conventions, testing, etc.)
- Merged `self_improvement` + `daily_review` + `memory_usage` → `0__memory_and_improvement.md` (3 modes: real-time, maintenance, review)
- Merged `communication_protocol` + `discord_reporting` → `0__communication.md` (multi-channel, no hardcoded IDs)
- Improved `0__resource_first_research.md` — check past research, time-awareness, explicit browser/curl tool usage
- Token count added to all 81 skill files (below title heading)
- Community skills extracted from awesome-openclaw-agents:
  - development: api_testing, api_documentation, schema_design, qa_testing, issue_triage, pr_review
  - devops: incident_response, deployment_monitoring, log_analysis, cloud_cost_optimization, sla_monitoring
  - security: vulnerability_scanning, access_audit
  - data: data_quality, anomaly_detection, etl_pipeline
  - finance: fraud_detection, revenue_analysis
  - compliance: risk_assessment, gdpr_compliance
  - legal: contract_review
  - business: lead_generation, competitor_pricing_analysis, churn_prediction
  - creative: ux_research, ad_copywriting
  - hr: recruiting, performance_review
  - marketing: seo_content
  - supply-chain: vendor_evaluation
  - saas: sprint_planning, product_ops, saas_analytics
  - productivity: team_coordination
  - education: course_design, literature_review
- Community skills extracted from agency-agents:
  - engineering: system_design, architecture_decisions, query_optimization
  - project-management: experiment_design, project_coordination, task_breakdown
  - product: product_requirements, feedback_analysis, market_intelligence
  - game-development: game_design_systems, godot_scripting, godot_multiplayer
  - testing: accessibility_audit, performance_testing
  - marketing: growth_strategy
  - support: executive_summary, analytics_reporting
  - design: ui_design_systems, frontend_architecture, image_prompting
- Final global skills (3): communication, memory_and_improvement, resource_first_research

### Bug fixes
- Fixed `openclaw_healthy` → `healthy` column rename across DB, heartbeat, API, UI
- Fixed `repo_name` column mismatch in bootstrap.py
- Fixed bootstrap cron seeding removed (cron table no longer exists)
- Fixed TypeScript `Skill` type missing `status` and `created_by` fields
- Fixed agent env vars not loaded in multi-agent mode (NVIDIA_API_KEY missing)
- Fixed agent name showing as comma-separated string in multi-agent mode

### Docs
- Project name: Open Visionary → Open Visio AI Agents
- README: updated architecture diagram (multi-agent), highlights (20 tools, 81 skills, sub-agents, recurring tasks), acknowledgements section for community repos
- CLAUDE.md: full rewrite — multi-agent conventions, skill library, consolidated migrations, updated commands
- project_summary.md + project_details.md: updated for multi-agent, removed cron, added resources/delegate/skills
- Tool count: 20, test count: 350
