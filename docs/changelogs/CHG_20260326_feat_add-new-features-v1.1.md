# Changelog — feat/add-new-features-v1.1

Branch started: 2026-03-26

## Changes

### ES-0001: Prompt Generator
- Added `prompt_gen` config to `inotagent/platform.yml` (default: nvidia-minimax-2.5, fallback: nvidia-mistral-large-3)
- New API route: `ui/src/app/api/prompt-gen/route.ts` — single-pass LLM call with model fallback chain, 60s timeout
- New UI page: `ui/src/app/prompt-gen/page.tsx` — instruction input, model selector, enhance button, copy to clipboard
- Added "Prompt Gen" to sidebar navigation (`AppLayout.tsx`)
- Added `NVIDIA_API_KEY` to `ui/.env.local` for LLM access

### Agent detail page improvements
- Memories tab: client-side filtering (instant, no API call per filter change)
- Memories tab: "Load More" pagination (100 per page, up to 500)
- Memories tab: instant search input (onChange instead of onSearch)
- Fixed settings tab not loading on first click (tab key mismatch: "config" → "settings")
- Fixed memory-graph tab not loading (missing lazy-load trigger)
- Fixed repos tab lazy-load (now triggers on both overview and repos tab visit)

### Agent detail page refactor
- Split `page.tsx` (1,774 lines) into 11 files — page shell + 9 tab components + shared utils
- Each tab is self-contained with own state and data fetching
- No file exceeds 275 lines
- File size check threshold set to 800 lines in CLAUDE.md

### ES-0002: Daily Reviews & Agent Self-Improvement Skills
- Migration: added `status` (draft/active/rejected/inactive) and `created_by` columns to `skills` table
- Migration: seeded `daily_review` global cron job (1440 min = 24h, UTC-aligned to 00:00)
- Skills loader now filters by `status = 'active'` only — draft/rejected skills not injected into system prompt
- New tool: `skill_create` (#16) — agents propose draft skills during daily review, requires human approval
- Discord: `!prompt` command wired with platform config + models for prompt enhancement
- Admin UI Skills page: status filter dropdown, status badge on cards, "Approve"/"Reject" buttons for drafts, "by {agent}" tag
- Skills API: `status` added to allowed PATCH fields
- Updated Robin agent.yml: minimax-2.1 → minimax-2.5 (2.1 EOL'd)
- 326 unit tests (up from 323)

### ES-0003: Agent Email Send
- New tool: `send_email` (#17) — Gmail SMTP with markdown→HTML conversion
- Email whitelist validation via `OWNER_EMAIL` env var (security against prompt injection)
- `to` field optional — defaults to `OWNER_EMAIL` when not specified
- Added `GMAIL_APP_PASSWORD` and `OWNER_EMAIL` to all 3 agent env templates
- 329 unit tests (up from 326)
- Updated tool count to 17 and test count to 329 across all docs

### ES-0004: Curated Resources Registry
- Migration: `resources` table with priority (1-100), status, tags, indexes + 3 seed resources
- New DB layer: `db/resources.py` — search_resources + add_resource
- New tools: `resource_search` (#18) + `resource_add` (#19) — 19 tools total
- New Admin UI page: Resources — table with inline priority editing, search/tag/status filters, add/edit modal, approve/reject for drafts
- Added "Resources" to sidebar navigation
- 333 unit tests (up from 329)

### Resource-first research skill
- Migration: seeded `resource_first_research` global skill — instructs agents to always check curated resources before falling back to web search

### ES-0006: Recurring Tasks Replace Cron
- Migration: `last_completed_at`, `recurrence_minutes`, `recurrence_count`, `schedule_at` columns on tasks table
- Tag parsing: `schedule:daily`, `schedule:hourly`, `schedule:daily@00:00`, `schedule:monthly@00:00` etc.
- Heartbeat resets completed recurring tasks when due (both `done` and `review` status)
- Calendar-accurate monthly recurrence (checks month boundary, not 30-day interval)
- `recurrence_count` tracks completed cycles, shown in UI badge
- Cron scheduler disabled — replaced by recurring tasks via heartbeat
- All cron jobs disabled via migration
- Cron Jobs page removed from sidebar
- Task edit form added to task detail drawer (title, description, priority, assigned_to, tags)
- `task.sh` updated: parses `schedule:*` tags, sets `last_completed_at` on done, supports `@HH:MM` syntax

### Daily review as recurring task
- Seeded `daily_review` global skill with structured review workflow
- Daily review runs as recurring task (`schedule:daily@00:00`) instead of cron
- Skill defines the how, task defines the when — both editable without redeploy

### Agent runtime improvements
- Dynamic current timestamp injected into system prompt on every LLM call (prevents date hallucination)
- 343 unit tests

### UI improvements
- Removed category labels from circular barplot on agent detail overview (cleaner look)

### Bug fixes
- Fixed agent detail page SyntaxError (IIFE in JSX → ternary for offline detection)
- Fixed nvidia-minimax-2.1 EOL (410 Gone as of 2026-03-26) — updated default models
