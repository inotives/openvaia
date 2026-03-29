# Tools — {{AGENT_NAME}} Environment

## Runtime
- **Runtime**: inotagent (Python 3.12)
- **Workspace**: `/workspace` (env: `WORKSPACE_DIR`)
- **Repos**: `/workspace/repos/<repo-name>/`
- **DB**: accessed via native tools (task_*, memory_*, research_*) — no raw SQL needed
- **Python**: `psycopg` (v3) is available in the venv — use it for any direct DB queries

## Available Tools (15 total)

All tools are native functions — call them directly by name.

### shell
Execute shell commands (git, gh, make, npm, system commands).
```
shell(command="git status", working_dir="/workspace/repos/myrepo")
```
- `command` (required): The command to run
- `working_dir` (optional): Working directory
- `timeout` (optional): Timeout in seconds (default: 120)

### read_file
Read file contents.
```
read_file(path="/workspace/repos/myrepo/src/main.py")
```
- `path` (required): Absolute path
- `max_lines` (optional): Max lines to read (default: 500)

### list_files
List files in a directory.
```
list_files(path="/workspace/repos/myrepo/src", pattern="*.py")
```
- `path` (required): Directory path
- `pattern` (optional): Glob pattern (default: "*")

### search_files
Search for text patterns in files (grep-like).
```
search_files(pattern="def main", path="/workspace/repos/myrepo", glob="*.py")
```
- `pattern` (required): Regex pattern
- `path` (required): Directory to search
- `glob` (optional): File filter (default: "*")

### write_file
Write content to a file (create or overwrite).
```
write_file(path="/workspace/repos/myrepo/src/hello.py", content="print('Hello World')")
```
- `path` (required): Absolute path
- `content` (required): File content to write

### browser
Browse web pages (documentation, deployments, references).
```
browser(url="https://docs.python.org/3/library/asyncio.html")
```
- `url` (required): URL to visit
- `action` (optional): "get_text", "get_html", "screenshot", "click", "fill"
- `selector` (optional): CSS selector for click/fill
- `value` (optional): Value for fill

### task_list
List tasks with filters.
```
task_list(assigned_to="{{AGENT_NAME_LOWER}}", status="todo,in_progress")
```
- `assigned_to` (optional): Filter by agent
- `status` (optional): Comma-separated: todo, in_progress, blocked, review, done
- `created_by` (optional): Filter by creator

### task_update
Update a task's status, result, or assignment.
```
task_update(key="<task_key>", status="done", result="Summary of what was done")
```
- `key` (required): Task key from task_list (e.g., "ROB-001", "INO-003")
- `status` (optional): New status
- `result` (optional): Result notes
- `assigned_to` (optional): Reassign

### task_create
Create a new task.
```
task_create(title="Fix login bug", priority="high")
```
- `title` (required): Task title
- `assigned_to` (optional): Agent to assign to
- `description` (optional): Details
- `priority` (optional): low, medium, high, critical
- `tags` (optional): List of tags

### send_message
Send a message to a platform space.
```
send_message(space_name="tasks", body="Starting work on <task_key>")
```
- `space_name` (required): "public", "tasks", or agent name for DM
- `body` (required): Message text

### discord_send
Send a message to a Discord channel (for human-visible updates).
```
discord_send(channel_id="1482793839583559881", message="Task <task_key> complete")
```
- `channel_id` (required): Discord channel ID
- `message` (required): Message text

### research_search
Search past research reports (written by any agent).
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

### research_store
Save a research report (available to all agents).
```
research_store(title="Report Title", summary="Key findings", body="<full markdown>", tags=["topic"])
```
- `title` (required): Report title
- `summary` (required): Key findings
- `body` (required): Full markdown report
- `tags` (optional): Topic tags
- `task_key` (optional): Related task key

### memory_store
Store information for future sessions.
```
memory_store(content="Important fact to remember", tags=["topic"], tier="long")
```
- `content` (required): What to remember
- `tags` (required): Categorization tags
- `tier` (optional): "short" (auto-pruned 30d) or "long" (permanent)

### memory_search
Search stored memories.
```
memory_search(query="testing framework", tags=["preference"])
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
- **python3** — for running scripts from `/workspace/scratch/`
