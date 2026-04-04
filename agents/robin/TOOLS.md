# Tools — Robin Environment

## Runtime
- **Runtime**: inotagent (Python 3.12)
- **Workspace**: `/workspace` (env: `WORKSPACE_DIR`)
- **Trading toolkit**: `/opt/inotagent-trading` — all trading CLI commands
- **DB**: accessed via native tools (task_*, memory_*, research_*) and trading CLI

## Native Tools (22 total)

All tools are native functions — call them directly by name.

### File & Code Tools

**shell** — Execute shell commands (git, make, python, system commands).
```
shell(command="git status", working_dir="/workspace/repos/myrepo", timeout=120)
```

**read_file** — Read file contents.
```
read_file(path="/workspace/repos/myrepo/src/main.py", max_lines=500)
```

**list_files** — List files in a directory.
```
list_files(path="/workspace/repos/myrepo/src", pattern="*.py")
```

**search_files** — Search for text patterns in files (grep-like).
```
search_files(pattern="def main", path="/workspace/repos/myrepo", glob="*.py")
```

**write_file** — Write content to a file (create or overwrite).
```
write_file(path="/workspace/repos/myrepo/src/hello.py", content="print('Hello')")
```

**browser** — Browse web pages.
```
browser(url="https://docs.python.org/3/", action="get_text")
```

### Task Tools

**task_list** — List tasks with filters.
```
task_list(assigned_to="robin", status="todo,in_progress")
task_list(created_by="robin", status="done")  # check delegated tasks
```

**task_create** — Create a new task. Omit `assigned_to` for mission board.
```
task_create(title="Research CRO sentiment", description="WHY: ... WHAT: ... FOLLOW-UP: ...", priority="high", tags=["research", "crypto"])
```

**task_update** — Update status, result, or assignment.
```
task_update(key="ROB-010", status="done", result="Signal scan complete, no signals")
```

### Communication Tools

**send_message** — Send to a platform space.
```
send_message(space_name="public", body="Daily P&L: +$3.50")
```

**discord_send** — Send to Discord channel (human-visible).
```
discord_send(channel_id="<channel_id>", message="Trade executed: 100 CRO @ $0.085")
```

**send_email** — Send email.
```
send_email(to="boss@example.com", subject="Weekly Report", body="...")
```

### Memory Tools

**memory_store** — Store information for future sessions.
```
memory_store(content="CRO momentum works best with RSI<35", tags=["trading", "tuning"], tier="long")
```

**memory_search** — Search stored memories.
```
memory_search(query="CRO strategy", tags=["trading"])
```

### Research Tools

**research_store** — Save a research report (visible to all agents).
```
research_store(title="Weekly Performance Review", summary="- Key points", body="<markdown>", tags=["trading", "weekly-review"], task_key="ROB-013")
```

**research_search** — Search past reports.
```
research_search(query="CRO market", tags=["trading"])
```

**research_get** — Get full report by ID.
```
research_get(report_id=42)
```

### Resource Tools

**resource_search** — Search external resources (URLs, docs, APIs).
```
resource_search(query="coingecko api")
```

**resource_add** — Add a resource reference.
```
resource_add(url="https://api.coingecko.com", name="CoinGecko API", tags=["data", "crypto"])
```

### Skill Tools

**skill_equip** — Load a skill into current conversation.
```
skill_equip(name="trading_signal_workflow")
```

**skill_create** — Propose a new skill (draft, needs human approval).
```
skill_create(name="my_new_skill", description="...", content="...", tags=["trading"])
```

**skill_propose** — Propose a skill evolution (fix, derive, or capture).
```
skill_propose(type="fix", skill_name="trading_signal_workflow", direction="Add BTC filter check", proposed_content="...")
```

### Delegation

**delegate** — Delegate a sub-task to another agent (requires models + config).
```
delegate(task="Analyze CRO on-chain data", context="Need whale movement data for strategy tuning")
```

## Trading CLI

All trading commands via shell from `/opt/inotagent-trading`:
```
shell("cd /opt/inotagent-trading && python -m cli.<module> <command>")
```

| Module | Key Commands |
|--------|-------------|
| `cli.market` | overview, price, ta, fetch-daily, compute-daily-ta, sync-fees, coverage, add-asset/venue/mapping/account/pair |
| `cli.signals` | scan, check --symbol CRO |
| `cli.trade` | buy, sell, cancel, list-orders |
| `cli.portfolio` | balance, pnl, accounts, transfers, snapshot, benchmark, history, reconcile-pnl |
| `cli.strategy` | list, create, view, history, update, activate, deactivate, set-mode |
| `cli.backtest` | run, sweep, list, view |

## Spaces
- **#public** — general announcements
- **#tasks** — task notifications (auto-posted on create/update)

## External CLIs
- **gh** — GitHub CLI
- **git** — pre-configured identity
- **curl** — API calls
- **python3** — scripts from `/workspace/scratch/`
