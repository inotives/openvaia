# Tools — Ino Environment

## Runtime
- **Runtime**: inotagent (Python 3.12)
- **Workspace**: `/workspace` (env: `WORKSPACE_DIR`)
- **Repos**: `/workspace/repos/<repo-name>/`
- **Scratch**: `/workspace/scratch/` — for temporary scripts and data
- **DB**: accessed via native tools (task_*, memory_*, research_*) — no raw SQL needed

## Available Tools (15 total)

All tools are native functions — call them directly by name.

### browser — PRIMARY RESEARCH TOOL
Browse web pages, read documentation, fetch API references.
```
browser(url="https://docs.coingecko.com/v3.0.1/reference/introduction")
browser(url="https://api.coingecko.com/api/v3/coins/list", action="get_text")
```
- `url` (required): URL to visit
- `action` (optional): "get_text" (default), "get_html", "screenshot", "click", "fill"
- `selector` (optional): CSS selector for click/fill
- `value` (optional): Value for fill

### shell
Execute shell commands — run scripts, fetch data via curl, process files.
```
shell(command="curl -s 'https://api.coingecko.com/api/v3/ping' | python3 -m json.tool")
shell(command="python3 /workspace/scratch/fetch_data.py", timeout=300)
```
- `command` (required): The command to run
- `working_dir` (optional): Working directory
- `timeout` (optional): Timeout in seconds (default: 120, max: 600 for data scripts)

### read_file
Read file contents — review data, reports, configs.
```
read_file(path="/workspace/repos/inotives_cryptos/docs/research/report.md")
```
- `path` (required): Absolute path
- `max_lines` (optional): Max lines to read (default: 500)

### list_files
List files in a directory.
```
list_files(path="/workspace/repos/inotives_cryptos/docs/research")
```
- `path` (required): Directory path
- `pattern` (optional): Glob pattern (default: "*")

### search_files
Search for text patterns in files (grep-like).
```
search_files(pattern="coingecko", path="/workspace/repos/inotives_cryptos", glob="*.md")
```
- `pattern` (required): Regex pattern
- `path` (required): Directory to search
- `glob` (optional): File filter (default: "*")

### write_file
Write content to a file (create or overwrite). Use for data scripts and reports.
```
write_file(path="/workspace/scratch/fetch_tokens.py", content="import requests\n...")
write_file(path="/workspace/repos/inotives_cryptos/docs/research/2026-03-18_report.md", content="# Report\n...")
```
- `path` (required): Absolute path
- `content` (required): File content to write

### task_list
List tasks with filters.
```
task_list(assigned_to="ino", status="todo,in_progress")
```
- `assigned_to` (optional): Filter by agent
- `status` (optional): Comma-separated: todo, in_progress, blocked, review, done
- `created_by` (optional): Filter by creator

### task_update
Update a task's status, result, or assignment.
```
task_update(key="<task_key>", status="done", result="Research complete. Report in docs/research/")
```
- `key` (required): Task key from task_list (e.g., "INO-001", "ROB-003")
- `status` (optional): New status
- `result` (optional): Result notes
- `assigned_to` (optional): Reassign

### task_create
Create a new task — use this to hand off coding work to a peer agent.
```
task_create(title="Implement CoinGecko token fetcher", assigned_to="<peer_agent>", priority="medium", description="Based on research in docs/research/report.md")
```
- `title` (required): Task title
- `assigned_to` (optional): Agent to assign to (omit for unassigned backlog tasks)
- `description` (optional): Details and requirements
- `priority` (optional): low, medium, high, critical
- `tags` (optional): List of tags

### send_message
Send a message to a platform space.
```
send_message(space_name="tasks", body="Research complete for <task_key>")
```
- `space_name` (required): "public", "tasks", or agent name for DM
- `body` (required): Message text

### discord_send
Send a message to a Discord channel — for reporting findings to Boss.
```
discord_send(channel_id="1482793839583559881", message="✅ <task_key> done: CoinGecko API supports 14k tokens, 30 req/min free tier")
```
- `channel_id` (required): Discord channel ID
- `message` (required): Message text

### research_store — SAVE ALL RESEARCH HERE
Save a research report to the database. Permanent and searchable.
```
research_store(title="CoinGecko API Analysis", summary="- 14k tokens\n- 30 req/min free", body="<full markdown>", tags=["crypto", "coingecko"], task_key="<task_key>")
```
- `title` (required): Report title
- `summary` (required): Key findings (posted to Discord)
- `body` (required): Full markdown report
- `tags` (optional): Topic tags for search
- `task_key` (optional): Related task key

### research_search
Search past research reports by keywords and/or tags. Returns summaries.
```
research_search(query="coingecko api", tags=["crypto"])
```
- `query` (optional): Keyword search
- `tags` (optional): Filter by topic tags

### research_get
Get the full body of a research report by ID.
```
research_get(report_id=1)
```
- `report_id` (required): Report ID from research_search results

### memory_store
Store quick facts and observations (not full reports — use research_store for those).
```
memory_store(content="CoinGecko free tier: 30 req/min", tags=["crypto", "api"], tier="long")
```
- `content` (required): What to remember
- `tags` (required): Categorization tags
- `tier` (optional): "short" (auto-pruned 30d) or "long" (permanent)

### memory_search
Search stored memories.
```
memory_search(query="coingecko rate limit", tags=["crypto"])
```
- `query` (optional): Keyword search
- `tags` (optional): Filter by tags
- `tier` (optional): "short", "long", or "all"

## Spaces
- **#public** — general announcements (all agents)
- **#tasks** — task notifications (auto-posted on create/update)

## External CLIs
- **gh** — GitHub CLI (authenticated via `GITHUB_TOKEN`)
- **git** — pre-configured identity and credentials at boot
- **curl** — for quick API calls
- **python3** — for running data scripts from `/workspace/scratch/`
