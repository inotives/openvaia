# Phase 1: Foundation

**Goal**: Agent can load config, build a prompt, call an LLM, and return a response — tested via CLI.

**Delivers**: A working agent loop you can test from the terminal. No Discord, no tools, no persistence yet — just config loading + LLM API calls.

**Complexity**: Medium

## Dependencies

- None (first phase)

## What to build

### 1.1 Project scaffold

Set up the Python package with uv:

```
inotagent/
├── src/inotagent/
│   ├── __init__.py
│   └── ...
├── tests/
├── pyproject.toml
└── uv.lock
```

**pyproject.toml** dependencies:
```toml
[project]
name = "inotagent"
requires-python = ">=3.12,<3.13"
dependencies = [
    "anthropic>=0.40",
    "httpx>=0.27",
    "pyyaml>=6.0",
    "psycopg[binary]>=3.2",
    "discord.py>=2.4",
    "tiktoken>=0.8",
    "playwright>=1.48",
]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"
```

### 1.2 Config loading (`inotagent/config/`)

Load the existing config file formats:

**`config/models.py`** — Parse `core/models.yml`:
```python
@dataclass
class ModelConfig:
    id: str                    # e.g. "nvidia-glm5"
    provider: str              # e.g. "nvidia"
    model: str                 # e.g. "z-ai/glm5"
    api_key_env: str           # e.g. "NVIDIA_API_KEY"
    base_url: str | None       # e.g. "https://integrate.api.nvidia.com/v1"
    context_window: int        # e.g. 200000
    max_tokens: int            # e.g. 16384

def load_models(path: str) -> dict[str, ModelConfig]:
    """Load models.yml → dict keyed by model id."""
```

**`config/agent.py`** — Parse agent.yml + read AGENTS.md and TOOLS.md:
```python
@dataclass
class AgentConfig:
    name: str                  # from AGENT_NAME env
    model_id: str              # resolved: agent.yml → platform.yml → first in registry
    fallbacks: list[str]       # fallback model ids
    system_prompt: str         # AGENTS.md + TOOLS.md combined
    channels: dict             # minimal: just token_env per channel (settings loaded from DB at runtime)
    parallel: bool             # True = concurrent conversations, False = sequential queue (default)

def load_agent_config(agent_dir: str, models: dict) -> AgentConfig:
    """Load agent.yml + workspace files → AgentConfig.

    System prompt = AGENTS.md (persona, role, workflows)
                  + TOOLS.md (behavioral rules only, ~200 tokens)

    MEMORY.md is NOT loaded into system prompt. Memory is stored in
    pgvector and accessed on-demand via the memory_search tool.

    Detailed tool schemas are NOT in the system prompt — they go in
    the LLM API `tools` parameter (function calling). No duplication.
    """
```

**TOOLS.md format** — behavioral rules only, not usage docs:
```markdown
## Code-first approach
You are a developer. Solve problems by writing and running code, not by processing data in your context.
- For data analysis: read a sample to understand structure, then write a script to process it
- For log investigation: use grep/awk to filter first, only read relevant lines
- For code review: use git diff, read specific files, don't load entire repos
- For testing: write and run tests, don't mentally execute code
- NEVER dump large data into your context. Write code to handle it.

## Reuse before reinvent
Before writing new code:
1. Check scripts/ directory for existing scripts that solve the problem
2. Search memory for past solutions: memory_search(tags=["script"], query="what you need")
3. Check if existing CLI tools already handle it (run --help)
4. Only write new code if nothing reusable exists

When you write a useful script:
1. Include a metadata header at the top of the file:
   ```
   """
   Script: <filename>
   Purpose: <what it does>
   Usage: <how to run it>
   Author: <agent name>
   Created: <date>
   """
   ```
2. Save it to scripts/ directory
3. Store a long-term memory: memory_store(content="scripts/<name> — <purpose>. Usage: <usage>", tags=["script", ...], tier="long")

## Tool rules
- Always use the opencode tool for coding. Never write code directly.
- Use shell for git, gh, make, npm. Run --help if unsure about flags.
- Use browser to read documentation or check deployments.
- Check your task queue before starting new work.
- Report task status updates via task_update after completing work.
```

~300 tokens. The LLM already knows *how* to call each tool from the
function-calling schema. TOOLS.md only tells it *when* and *why*.

**`config/platform.py`** — Parse platform.yml:
```python
@dataclass
class PlatformConfig:
    default_model: str
    channels: dict

def load_platform_config(path: str) -> PlatformConfig:
```

### 1.3 LLM client (`inotagent/llm/`)

Unified interface across providers:

**`llm/client.py`** — Abstract interface:
```python
@dataclass
class LLMMessage:
    role: str                  # "user", "assistant", "tool"
    content: str | list        # text or content blocks
    tool_calls: list | None    # tool use requests
    tool_call_id: str | None   # for tool results

@dataclass
class LLMResponse:
    content: str               # text response
    tool_calls: list[ToolCall] # tool calls requested
    usage: TokenUsage          # input/output tokens
    stop_reason: str           # "end_turn", "tool_use", etc.

class LLMClient(Protocol):
    async def chat(
        self,
        model: str,
        system: str,
        messages: list[LLMMessage],
        tools: list[dict] | None = None,
        max_tokens: int = 4096,
    ) -> LLMResponse: ...
```

**`llm/anthropic.py`** — Anthropic provider (uses official SDK):
```python
class AnthropicClient:
    """Wraps anthropic.AsyncAnthropic for Anthropic models."""

    async def chat(self, model, system, messages, tools, max_tokens):
        # Uses anthropic SDK directly
        # Tool format is native (Anthropic schema)
```

**`llm/openai_compat.py`** — OpenAI-compatible provider (NVIDIA, Groq, Ollama, OpenAI):
```python
class OpenAICompatClient:
    """Uses httpx to call OpenAI-compatible /v1/chat/completions."""

    async def chat(self, model, system, messages, tools, max_tokens):
        # Convert Anthropic tool format → OpenAI function format
        # POST to base_url/chat/completions
        # Convert response back to LLMResponse
```

**`llm/tokens.py`** — Token counting:
```python
def count_tokens(text: str, model: str) -> int:
    """Estimate token count. Use tiktoken for OpenAI-compat, anthropic for Claude."""

def truncate_history(messages: list, max_tokens: int, model: str) -> list:
    """Remove oldest messages to fit within context window, keeping system prompt."""
```

### 1.4 Agent loop (`inotagent/loop.py`)

The core reasoning loop (no tools in Phase 1):

```python
class AgentLoop:
    def __init__(self, config: AgentConfig, llm: LLMClient, models: dict[str, ModelConfig]):
        self.config = config
        self.llm = llm
        self.models = models
        # Concurrency control: sequential (default) or parallel
        self._semaphore = asyncio.Semaphore(1 if not config.parallel else 5)

    async def run(self, message: str, history: list[LLMMessage] | None = None) -> str:
        async with self._semaphore:
            return await self._run_inner(message, history)

    async def _run_inner(self, message: str, history: list[LLMMessage] | None = None) -> str:
        model_config = self.models[self.config.model_id]
        system = self.config.system_prompt  # AGENTS.md + TOOLS.md behavioral rules

        # Auto-inject memory if trigger keywords detected (Phase 2+)
        # Keywords loaded from platform.config, not hardcoded
        # e.g. "remember", "last time", "you suggested" → search memory → inject
        # This saves an LLM round-trip vs agent calling memory_search as a tool
        memory_context = await self._maybe_inject_memory(message)
        if memory_context:
            system += "\n\n## Relevant memories:\n" + memory_context

        messages = (history or []) + [LLMMessage(role="user", content=message)]

        response = await self.llm.chat(
            model=model_config.model,
            system=system,
            messages=messages,
            max_tokens=model_config.max_tokens,
        )

        return response.content
```

### 1.5 CLI test runner (`inotagent/main.py`)

Simple REPL for testing:

```python
async def cli_mode():
    """Interactive CLI for testing the agent loop."""
    config = load_agent_config(...)
    models = load_models(...)
    llm = create_client(models[config.model_id])
    loop = AgentLoop(config, llm, models)

    print(f"inotagent [{config.name}] ready. Type messages, Ctrl+C to exit.")
    history = []
    while True:
        user_input = input("> ")
        response = await loop.run(user_input, history)
        print(response)
        history.append(LLMMessage(role="user", content=user_input))
        history.append(LLMMessage(role="assistant", content=response))
```

### 1.6 Model fallback

When the primary model fails (rate limit, timeout, API error), try fallback models:

```python
async def chat_with_fallback(self, model_id: str, fallbacks: list[str], **kwargs) -> LLMResponse:
    for mid in [model_id] + fallbacks:
        try:
            return await self._get_client(mid).chat(model=self.models[mid].model, **kwargs)
        except (RateLimitError, TimeoutError, APIError) as e:
            logger.warning(f"Model {mid} failed: {e}, trying next")
    raise AllModelsFailed(f"All models failed: {[model_id] + fallbacks}")
```

## Files to create

| File | Purpose |
|------|---------|
| `src/inotagent/__init__.py` | Package init |
| `src/inotagent/main.py` | Entry point, CLI mode |
| `src/inotagent/loop.py` | Agent reasoning loop |
| `src/inotagent/config/agent.py` | Agent config loader |
| `src/inotagent/config/models.py` | Model registry loader |
| `src/inotagent/config/platform.py` | Platform config loader |
| `src/inotagent/llm/client.py` | LLM types and protocol |
| `src/inotagent/llm/anthropic.py` | Anthropic provider |
| `src/inotagent/llm/openai_compat.py` | OpenAI-compatible provider |
| `src/inotagent/llm/tokens.py` | Token counting + truncation |
| `pyproject.toml` | Package config |
| `tests/test_config.py` | Config loading tests |
| `tests/test_llm.py` | LLM client tests |

## Existing code to reuse

- `core/models.yml` — model registry format (parse as-is)
- `core/platform.yml` — platform defaults (parse as-is)
- `agents/*/agent.yml` — agent config format (parse as-is)
- `agents/*/AGENTS.md`, `TOOLS.md` — read as plain text for system prompt
- `core/runtime/config.py` — `get_agent_name()`, `get_platform_schema()` patterns

## How to verify

1. `uv run python -m inotagent --agent-dir agents/robin` launches CLI mode
2. Type a message → get response from configured LLM
3. Test with NVIDIA model (primary) → verify fallback to secondary on simulated failure
4. Config loads correctly from existing YAML files
5. Token counting returns reasonable numbers
