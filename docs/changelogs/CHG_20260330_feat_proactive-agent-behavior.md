# Changelog — feature/proactive-agent-behavior

Branch started: 2026-03-30

## Changes

### Phase 1: Recurring Exploration Tasks
- Created 8 recurring tasks for proactive agent behavior (no code changes)

**ino (Global Financial Researcher):**
| Key | Title | Schedule |
|-----|-------|----------|
| INO-001 | Morning Market Brief | daily@09:00 |
| INO-002 | End of Day Market Summary | daily@17:00 |
| INO-003 | Price Alert Monitor | hourly |
| INO-004 | Resource Discovery | daily@12:00 |

**robin (Trading Operations Engineer):**
| Key | Title | Schedule |
|-----|-------|----------|
| ROB-001 | System Health Check | daily@09:30 |
| ROB-002 | Daily Operations Log | daily@18:00 |
| ROB-003 | Weekly Engineering Retro | weekly@MON:10:00 |
| ROB-004 | Review Mission Board | daily@08:00 |

- Verified: heartbeat detects pending tasks, agent picks up and executes autonomously

### Phase 2: Idle Behavior Skill
- Created `0__idle_behavior.md` as global skill (injected into all agents)
- Priority-ordered idle actions: mission board → stale research → resource discovery → proactive monitoring → status update
- Guardrails: one action per cycle, create task first (tagged `autonomous:true`), < 10 min, human messages always take priority

### Phase 3: Heartbeat Idle Detection
- Added step 5 to heartbeat: proactive idle behavior trigger
- Three guardrails checked before triggering LLM:
  - `proactive_enabled` config (default: true) — kill switch per agent
  - `proactive_max_daily` config (default: 10) — daily autonomous call budget
  - `proactive_idle_minutes` config (default: 5) — minimum idle time before triggering
- New helper methods: `_check_idle_behavior()`, `_get_agent_config()`, `_get_today_autonomous_count()`, `_is_idle_for()`
- All configurable via `agent_configs` table — no redeploy needed
- Verified: agent triggers autonomous work after 5 min idle, follows idle_behavior skill protocol, creates autonomous tasks, fetches market data

### Phase 3.5: Human Message Priority (Interrupt Pattern)
- Modified `loop.py` to check for pending human messages between tool iterations during autonomous tasks
- Autonomous conversations identified by `conversation_id` starting with `heartbeat-idle-`
- Two interrupt signals checked:
  - Web chat: unprocessed messages in DB (`processed_at IS NULL`)
  - Discord/Slack/Telegram: requests queued at semaphore (`_semaphore._waiters`)
- On interrupt: saves pause note to conversation, returns early, releases semaphore for human request
- Only autonomous tasks are interruptible — human-initiated tasks are never interrupted

### Tuning (post-10h observation)
- Fixed recurring tasks: set `schedule_at` (UTC) and `recurrence_minutes` for all 8 tasks
- Reduced daily autonomous budget: 10 → 6 per agent
- Increased idle trigger interval: 5 min → 15 min
- Added anti-repetition rules to idle_behavior skill (check recent tasks, no same work within 3h)
- Added self-assignment requirement (no more unassigned autonomous tasks)
- Updated idle prompt to enforce diversity and skip cycles when nothing new

### Infrastructure
- Created `scripts/seed-recurring-tasks.py` — seeds recurring tasks on fresh deploy
- Added `make seed-tasks` command
- Hooked into `make clean-slate` (runs after `import-skills`)
