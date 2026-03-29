# Phase 2: Tool System

**Goal**: Agent can call tools (opencode, shell, files, platform tools) during its reasoning loop, enabling it to do real work.

**Delivers**: Agent receives a prompt, reasons about what to do, calls tools (primarily opencode for coding), gets results, and produces a final answer — all via tool-use loop.

**Complexity**: Large

## Dependencies

- Phase 1 (Foundation) — agent loop, LLM client, config loading

## What to build

### 2.1 Tool definition format

Use Anthropic's native tool schema as the canonical format. Convert to OpenAI function-calling format when using OpenAI-compatible providers.

```python
# Anthropic format (canonical)
{
    "name": "opencode",
    "description": "Delegate coding work to opencode AI coding assistant. Use for ALL code creation, editing, debugging, and refactoring.",
    "input_schema": {
        "type": "object",
        "properties": {
            "prompt": {
                "type": "string",
                "description": "Description of the coding task"
            },
            "working_dir": {
                "type": "string",
                "description": "Repository directory to work in"
            },
            "session_id": {
                "type": "string",
                "description": "Optional session ID to continue previous work"
            }
        },
        "required": ["prompt"]
    }
}
```

Converter for OpenAI-compatible providers:
```python
def anthropic_to_openai_tools(tools: list[dict]) -> list[dict]:
    """Convert Anthropic tool defs to OpenAI function-calling format."""
    return [{"type": "function", "function": {
        "name": t["name"],
        "description": t["description"],
        "parameters": t["input_schema"],
    }} for t in tools]
```

### 2.2 Tool registry (`tools/registry.py`)

Register tools available to each agent:

```python
class ToolRegistry:
    def __init__(self):
        self._tools: dict[str, ToolHandler] = {}

    def register(self, name: str, handler: ToolHandler, definition: dict):
        """Register a tool with its handler and schema."""

    def get_definitions(self) -> list[dict]:
        """Return all tool definitions for LLM prompt."""

    async def execute(self, name: str, arguments: dict) -> str:
        """Execute a tool call and return the result as a string."""
```

### 2.3 opencode tool — PRIMARY (`tools/opencode.py`)

This is the most important tool. Agents are developers, and opencode does all the coding.

**Two integration modes:**

#### Mode A: `opencode run` (per-task, simpler)
```python
class OpencodeTool:
    async def execute(self, prompt: str, working_dir: str | None = None, session_id: str | None = None) -> str:
        cmd = ["opencode", "run"]
        if session_id:
            cmd.extend(["--session", session_id])
        cmd.append(prompt)

        result = await asyncio.create_subprocess_exec(
            *cmd,
            cwd=working_dir or self.default_dir,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await asyncio.wait_for(result.communicate(), timeout=600)
        return stdout.decode() + (f"\nSTDERR: {stderr.decode()}" if stderr else "")
```

#### Mode B: `opencode serve` + attach (persistent, avoids cold boot)
```python
class OpencodeServer:
    """Manage a persistent opencode server per working directory."""

    async def start(self, working_dir: str, port: int = 4096):
        """Start opencode serve in background."""
        self.process = await asyncio.create_subprocess_exec(
            "opencode", "serve", "--port", str(port),
            cwd=working_dir,
        )
        self.port = port

    async def run(self, prompt: str, session_id: str | None = None) -> str:
        """Send prompt via opencode run --attach."""
        cmd = ["opencode", "run", "--attach", f"http://localhost:{self.port}"]
        if session_id:
            cmd.extend(["--session", session_id])
        cmd.append(prompt)
        result = await asyncio.create_subprocess_exec(*cmd, ...)
        stdout, stderr = await result.communicate()
        return stdout.decode()
```

**Recommendation**: Start with Mode A (simpler). Move to Mode B if cold boot times become a problem.

**Tool definition:**
```python
OPENCODE_TOOL = {
    "name": "opencode",
    "description": (
        "Delegate coding work to opencode AI coding assistant. "
        "Use this for ALL code tasks: creating files, editing code, fixing bugs, "
        "refactoring, reading/understanding code, running tests. "
        "You should NEVER write code directly — always delegate to opencode."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "prompt": {
                "type": "string",
                "description": "Detailed description of the coding task to perform"
            },
            "working_dir": {
                "type": "string",
                "description": "Absolute path to the repository to work in"
            },
            "session_id": {
                "type": "string",
                "description": "Session ID to continue previous work in the same context"
            }
        },
        "required": ["prompt"]
    }
}
```

### 2.4 Shell tool (`tools/shell.py`)

For non-coding commands: git, gh, make, npm, system commands.

```python
SHELL_TOOL = {
    "name": "shell",
    "description": "Execute a shell command. Use for: git, gh, make, npm, system commands. Do NOT use for writing or editing code — use opencode instead.",
    "input_schema": {
        "type": "object",
        "properties": {
            "command": {"type": "string", "description": "The shell command to run"},
            "working_dir": {"type": "string", "description": "Working directory"},
            "timeout": {"type": "integer", "description": "Timeout in seconds", "default": 120}
        },
        "required": ["command"]
    }
}

class ShellTool:
    async def execute(self, command: str, working_dir: str | None = None, timeout: int = 120) -> str:
        proc = await asyncio.create_subprocess_shell(
            command,
            cwd=working_dir,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        try:
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
        except asyncio.TimeoutError:
            proc.kill()
            return f"Command timed out after {timeout}s"

        output = stdout.decode()
        if stderr:
            output += f"\nSTDERR:\n{stderr.decode()}"
        if proc.returncode != 0:
            output += f"\nExit code: {proc.returncode}"
        return output
```

### 2.5 File tools (`tools/files.py`)

For when the agent needs to read files without invoking opencode:

```python
FILE_TOOLS = [
    {
        "name": "read_file",
        "description": "Read the contents of a file",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Absolute path to the file"},
                "max_lines": {"type": "integer", "description": "Max lines to read", "default": 500}
            },
            "required": ["path"]
        }
    },
    {
        "name": "list_files",
        "description": "List files in a directory, optionally with glob pattern",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Directory path"},
                "pattern": {"type": "string", "description": "Glob pattern", "default": "*"}
            },
            "required": ["path"]
        }
    },
    {
        "name": "search_files",
        "description": "Search for a pattern in files (grep-like)",
        "input_schema": {
            "type": "object",
            "properties": {
                "pattern": {"type": "string", "description": "Regex pattern to search for"},
                "path": {"type": "string", "description": "Directory to search in"},
                "glob": {"type": "string", "description": "File pattern filter", "default": "*"}
            },
            "required": ["pattern", "path"]
        }
    }
]
```

### 2.6 Browser tool (`tools/browser.py`)

Web browsing via Playwright for reading docs, checking deployments, scraping reference material.

```python
BROWSER_TOOL = {
    "name": "browser",
    "description": "Browse a web page and extract its content. Use for reading documentation, checking deployments, or fetching reference material.",
    "input_schema": {
        "type": "object",
        "properties": {
            "url": {"type": "string", "description": "URL to visit"},
            "action": {
                "type": "string",
                "enum": ["get_text", "get_html", "screenshot", "click", "fill"],
                "description": "Action to perform. get_text returns readable text, screenshot returns a description.",
                "default": "get_text"
            },
            "selector": {"type": "string", "description": "CSS selector for click/fill actions"},
            "value": {"type": "string", "description": "Value for fill action"}
        },
        "required": ["url"]
    }
}

class BrowserTool:
    def __init__(self):
        self._browser = None
        self._context = None

    async def _ensure_browser(self):
        if not self._browser:
            from playwright.async_api import async_playwright
            self._pw = await async_playwright().start()
            self._browser = await self._pw.chromium.launch(headless=True)
            self._context = await self._browser.new_context()

    async def execute(self, url: str, action: str = "get_text", selector: str | None = None, value: str | None = None) -> str:
        await self._ensure_browser()
        page = await self._context.new_page()
        try:
            await page.goto(url, timeout=30000)

            if action == "get_text":
                return await page.inner_text("body")
            elif action == "get_html":
                return await page.content()
            elif action == "screenshot":
                buf = await page.screenshot()
                return f"[Screenshot taken: {len(buf)} bytes of {url}]"
            elif action == "click":
                await page.click(selector)
                return f"Clicked {selector} on {url}"
            elif action == "fill":
                await page.fill(selector, value)
                return f"Filled {selector} with value on {url}"
        finally:
            await page.close()

    async def close(self):
        if self._browser:
            await self._browser.close()
            await self._pw.stop()
```

Playwright is lazy-loaded — browser only starts on first use. Reuses the same browser instance across calls to avoid repeated startup costs.

### 2.7 Platform tools (`tools/platform.py`)

Port existing `tasks.py` and `messaging.py` as tool handlers. Import the Python functions directly instead of shelling out to `platform_tools.py`.

```python
PLATFORM_TOOLS = [
    {
        "name": "task_list",
        "description": "List tasks with optional filters",
        "input_schema": {
            "type": "object",
            "properties": {
                "assigned_to": {"type": "string"},
                "status": {"type": "string", "description": "Comma-separated: todo,in_progress,blocked,review,done"},
                "created_by": {"type": "string"}
            }
        }
    },
    {
        "name": "task_update",
        "description": "Update a task's status, result, or other fields",
        "input_schema": {
            "type": "object",
            "properties": {
                "key": {"type": "string", "description": "Task key (e.g. INO-001)"},
                "status": {"type": "string"},
                "result": {"type": "string"},
                "assigned_to": {"type": "string"}
            },
            "required": ["key"]
        }
    },
    {
        "name": "task_create",
        "description": "Create a new task",
        "input_schema": {
            "type": "object",
            "properties": {
                "title": {"type": "string"},
                "description": {"type": "string"},
                "assigned_to": {"type": "string"},
                "priority": {"type": "string", "enum": ["low", "medium", "high", "critical"]},
                "tags": {"type": "array", "items": {"type": "string"}}
            },
            "required": ["title", "assigned_to"]
        }
    },
    {
        "name": "send_message",
        "description": "Send a message to a space (channel)",
        "input_schema": {
            "type": "object",
            "properties": {
                "space_name": {"type": "string", "description": "Space name (e.g. 'public', 'tasks')"},
                "body": {"type": "string", "description": "Message body"}
            },
            "required": ["space_name", "body"]
        }
    }
]
```

### 2.8 Memory tools (`tools/memory.py`)

Replaces MEMORY.md. Agent stores and retrieves memories on-demand via tools — not loaded into every request. No embedding model required.

Two tiers of memory:

| | Short-term | Long-term |
|---|---|---|
| **Purpose** | Recent context, decisions, status | Durable knowledge, scripts, patterns, preferences |
| **Examples** | "PR #42 needs test fixes", "deploy after Thursday" | "wrote scripts/analyze_logs.py", "Boss prefers PRs under 300 lines" |
| **Retention** | Auto-pruned after 30 days | Never auto-pruned (manual cleanup only) |
| **Search window** | Last 30 days | All time |

```python
MEMORY_TOOLS = [
    {
        "name": "memory_store",
        "description": "Store information for future reference. Use 'short' for temporary context, 'long' for durable knowledge (scripts, patterns, preferences).",
        "input_schema": {
            "type": "object",
            "properties": {
                "content": {"type": "string", "description": "The memory to store"},
                "tags": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Tags for categorization (e.g. 'script', 'preference', 'decision', 'bug')"
                },
                "tier": {
                    "type": "string",
                    "enum": ["short", "long"],
                    "description": "short = recent context (auto-pruned 30 days). long = durable knowledge (kept forever).",
                    "default": "short"
                }
            },
            "required": ["content", "tags", "tier"]
        }
    },
    {
        "name": "memory_search",
        "description": "Search your memories. Searches both tiers by default. Long-term is always searched (no time limit), short-term limited to last 30 days.",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Keyword search (matches against memory content)"},
                "tags": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Filter by tags (e.g. ['script', 'preference'])"
                },
                "tier": {
                    "type": "string",
                    "enum": ["short", "long", "all"],
                    "description": "Which tier to search. Default: all",
                    "default": "all"
                }
            }
        }
    }
]
```

**Search strategy** (no embedding model needed):

```python
MAX_MEMORY_CHARS = 8000  # ~2000 tokens hard cap per search

class MemoryTool:
    async def search(self, query: str | None = None, tags: list[str] | None = None, tier: str = "all") -> str:
        conditions = [f"agent_name = %s"]
        params: list = [self.agent_name]

        # Tier filter + time window
        if tier == "short":
            conditions.append("tier = 'short'")
            conditions.append("created_at > NOW() - INTERVAL '30 days'")
        elif tier == "long":
            conditions.append("tier = 'long'")
            # No time limit for long-term
        else:  # "all"
            # Short-term: last 30 days. Long-term: all time.
            conditions.append(
                "(tier = 'long' OR (tier = 'short' AND created_at > NOW() - INTERVAL '30 days'))"
            )

        # Tag filter
        if tags:
            conditions.append("tags && %s")
            params.append(tags)

        # Keyword search (Postgres full-text search)
        if query:
            conditions.append("to_tsvector('english', content) @@ plainto_tsquery('english', %s)")
            params.append(query)

        where = " AND ".join(conditions)

        # Long-term results first (more valuable), then short-term by recency
        rows = await conn.execute(
            f"""SELECT content, tags, tier, created_at
                FROM {SCHEMA}.memories
                WHERE {where}
                ORDER BY
                    CASE tier WHEN 'long' THEN 0 ELSE 1 END,
                    created_at DESC
                LIMIT 20""",
            params,
        ).fetchall()

        # Enforce token cap
        results = []
        total_chars = 0
        for row in rows:
            entry = f"[{row['tier']}:{','.join(row['tags'])}] {row['content']}"
            if total_chars + len(entry) > MAX_MEMORY_CHARS:
                break
            results.append(entry)
            total_chars += len(entry)

        if not results:
            return "No memories found."
        return "\n---\n".join(results)

    async def store(self, content: str, tags: list[str], tier: str = "short") -> str:
        await conn.execute(
            f"""INSERT INTO {SCHEMA}.memories (agent_name, content, tags, tier, created_at)
                VALUES (%s, %s, %s, %s, NOW())""",
            (self.agent_name, content, tags, tier),
        )
        return f"Stored in {tier}-term memory with tags: {', '.join(tags)}"
```

### Keyword-triggered memory injection

Instead of the agent deciding to call `memory_search` (which costs an extra LLM round-trip), we detect trigger keywords in the incoming message and auto-inject relevant memories into the prompt *before* the first LLM call.

```
"do you remember the PR approach?"
    ↓ keyword detected: "remember"
    ↓ auto memory_search(query="PR approach")
    ↓ inject results into system prompt
    ↓ LLM sees message + memories in 1 call

"check my email"
    ↓ no keywords matched
    ↓ no memory search
    ↓ 0 extra tokens
```

**Trigger keywords stored in DB** (`platform.config`), not hardcoded:

```python
async def get_memory_trigger_keywords() -> list[str]:
    """Load trigger keywords from platform.config."""
    async with get_connection() as conn:
        row = await conn.execute(
            f"SELECT value FROM {SCHEMA}.config WHERE key = 'memory.trigger_keywords'"
        ).fetchone()
    if not row:
        return []
    return [kw.strip() for kw in row["value"].split(",")]

def should_inject_memory(message: str, keywords: list[str]) -> bool:
    """Check if the message implies needing past context."""
    lower = message.lower()
    return any(kw in lower for kw in keywords)
```

Default seed in config:
```sql
INSERT INTO config (key, value, description) VALUES (
    'memory.trigger_keywords',
    'remember,recall,last time,previously,before,you said,you suggested,you mentioned,we discussed,we agreed,we decided,usual,preference,how did we,what was,what did',
    'Comma-separated keywords that trigger auto memory injection into prompt'
);
```

Add new keywords anytime via SQL — no code change, no redeploy:
```sql
UPDATE config SET value = value || ',as usual,like before,the other day'
WHERE key = 'memory.trigger_keywords';
```

The agent can still call `memory_search` manually via tool call if it decides to — keyword injection is just the fast path that saves an LLM round-trip.

**Why this is better than MEMORY.md:**

| | MEMORY.md (OpenClaw) | memory tools (inotagent) |
|---|---|---|
| **Token cost** | Loaded every request, grows unbounded | 0 tokens unless agent queries |
| **Search** | None — entire file injected | Tag filter + full-text keyword search |
| **Persistence** | File in container, lost on redeploy | Postgres, survives everything |
| **Relevance** | Everything loaded, mostly irrelevant | Agent retrieves only what it needs |
| **Model dependency** | None | None — no embedding model required |

Implementation backed by Postgres full-text search in Phase 4.6.

### 2.9 Tool call loop (update `loop.py`)

Extend the agent loop from Phase 1 to handle tool calls:

```python
async def run(self, message: str, history: list | None = None) -> str:
    messages = (history or []) + [user_msg(message)]
    tools = self.tool_registry.get_definitions()

    response = await self.llm.chat(
        model=..., system=..., messages=messages, tools=tools,
    )

    while response.tool_calls:
        tool_results = []
        for call in response.tool_calls:
            result = await self.tool_registry.execute(call.name, call.arguments)
            tool_results.append(tool_result_msg(call.id, result))

        messages.extend([assistant_msg(response), *tool_results])
        response = await self.llm.chat(
            model=..., system=..., messages=messages, tools=tools,
        )

    return response.content
```

## Files to create

| File | Purpose |
|------|---------|
| `src/inotagent/tools/__init__.py` | Package init |
| `src/inotagent/tools/registry.py` | Tool registry + dispatcher |
| `src/inotagent/tools/executor.py` | Common execution utilities |
| `src/inotagent/tools/opencode.py` | opencode integration (PRIMARY) |
| `src/inotagent/tools/shell.py` | Shell command execution |
| `src/inotagent/tools/files.py` | File read/list/search |
| `src/inotagent/tools/browser.py` | Web browsing (Playwright) |
| `src/inotagent/tools/memory.py` | Memory store + search (backed by pgvector) |
| `src/inotagent/tools/platform.py` | Tasks + messaging (port from runtime/) |
| `tests/test_tools.py` | Tool execution tests |

## Existing code to port

- `core/runtime/tasks.py` → `tools/platform.py` (task_create, task_update, task_list, etc.)
- `core/runtime/messaging.py` → `tools/platform.py` (send_message, get_messages)
- `core/runtime/db.py` → reuse connection pattern (will be async in Phase 4)

## How to verify

1. CLI mode: ask agent "list my tasks" → agent calls `task_list` tool → returns results
2. CLI mode: ask agent "fix the bug in main.py" → agent calls `opencode` tool → opencode does the work → agent reports result
3. CLI mode: ask agent "create a branch and push" → agent calls `shell` tool with git commands
4. CLI mode: ask agent "read the docs at https://example.com" → agent calls `browser` tool → returns page content
5. Tool timeout: shell command exceeding timeout returns error message
6. Unknown tool: returns error to LLM, which adjusts
