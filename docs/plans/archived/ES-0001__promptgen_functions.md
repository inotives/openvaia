# Prompt Generator Function — Execution Plan

## Backstory

In the OpenVAIA platform, human operators (Boss) communicate with AI agents through Discord, Slack, Telegram, or the Admin UI chat. The quality of agent output depends heavily on how well the instruction is written — vague prompts lead to wasted LLM iterations, unfocused research, or incomplete code.

Most users know *what* they want but struggle to express it in a way that maximizes agent effectiveness. They might type "look into Solana DeFi" when what they really need is a structured prompt that specifies scope, output format, tools to use, and success criteria.

## Purpose

Build a lightweight **Prompt Enhancer** function that converts rough human instructions into well-structured prompts optimized for OpenVAIA agents. This is NOT a full agent — it's a single-pass LLM call with no tools, no memory, no persistence. Think of it as a "prompt spell-checker" that sits between the human and the agent.

**Key constraint**: The enhancer must never enter research mode, deep think mode, or multi-turn conversation. One input → one enhanced prompt → done.

## User Flow

```
Human writes rough idea
        ↓
Prompt Enhancer (single LLM call)
        ↓
Returns structured prompt
        ↓
Human reviews, optionally edits
        ↓
Human sends to agent (copy-paste, or direct "Send to Agent" button)
        ↓
Agent executes with better instructions
```

### Surfaces

1. **Admin UI** — standalone page or modal accessible from agent chat
2. **Discord** — command prefix (e.g., `!prompt <rough idea>`) via an existing agent bot

---

## Technical Design

### Model Selection

- User can choose which LLM model to use from a dropdown (same model registry as agents)
- Default model: a fast, cheap model (e.g., `groq-llama-3.3-70b`) — not the heavy models agents use for reasoning
- Fallback model: auto-retry on failure (e.g., `nvidia-minimax-2.1`)
- Configuration stored in `platform.yml`:

```yaml
prompt_gen:
  default_model: groq-llama-3.3-70b
  fallbacks:
    - nvidia-minimax-2.1
  max_tokens: 1024
```

### Preventing Deep Think / Research

- **No tools** — plain chat completion call, no tool definitions passed
- **System prompt** — explicitly instructs single-pass response, no follow-up questions
- **Low max_tokens** (~1024) — enough for a detailed prompt, not enough for research
- **No reasoning params** — skip NVIDIA NIM `extra_body` thinking/reasoning flags
- **No conversation history** — each call is stateless, no multi-turn

### System Prompt (Draft)

```
You are a prompt engineering expert for the OpenVAIA AI agent platform.

Your job: take the user's rough instruction and rewrite it into a clear, structured prompt that an AI agent can execute effectively.

The agents have these capabilities:
- Shell commands, file read/write, browser (web research)
- Task management (task_create, task_update, task_list)
- Memory (memory_store, memory_search)
- Research reports (research_store, research_search)
- Discord/Slack/Telegram messaging
- Git operations (clone, commit, push via shell)

When enhancing a prompt:
1. Clarify the objective — what exactly should the agent deliver?
2. Specify scope — what's in and out of bounds?
3. Define output format — report, code, summary, data?
4. Mention relevant tools if applicable
5. Add success criteria — how does the human know it's done?

Rules:
- Respond in a single pass. Do not ask follow-up questions.
- Return ONLY the enhanced prompt, no commentary or explanation.
- Keep it concise but thorough — aim for 100-300 words.
- Match the complexity to the task — simple tasks get simple prompts.
```

---

## Development Steps

### Step 1: Platform Config

**File**: `inotagent/platform.yml`

Add `prompt_gen` section with default model, fallbacks, and max_tokens.

**File**: `inotagent/src/inotagent/config/platform.py`

Add `PromptGenConfig` dataclass and load it in `PlatformConfig.from_dict()`.

### Step 2: API Route

**File**: `ui/src/app/api/prompt-gen/route.ts`

- `POST` handler
- Request body: `{ instruction: string, model?: string }`
- Reads `prompt_gen` config from `platform.yml` (or hardcoded defaults)
- Makes a single OpenAI-compatible chat completion call to the selected model
- Returns: `{ enhanced_prompt: string, model_used: string }`
- Implements fallback: try primary model, on failure try fallbacks in order
- No tools, no conversation history, just system prompt + user message

Estimated: ~50 lines

### Step 3: Admin UI Page

**File**: `ui/src/app/prompt-gen/page.tsx`

- Text area for rough instructions
- Model selector dropdown (populated from `/api/models`)
- "Enhance" button → calls `/api/prompt-gen`
- Result display area (read-only text area or markdown render)
- "Copy to Clipboard" button
- Optional: "Send to Agent" dropdown → pre-fills agent chat with the enhanced prompt
- Loading state while LLM is processing

Estimated: ~100 lines

### Step 4: Add to Navigation

**File**: `ui/src/components/AppLayout.tsx`

- Add "Prompt Gen" to sidebar navigation

Estimated: ~5 lines

### Step 5: Discord Integration

**File**: `inotagent/src/inotagent/channels/discord.py` (or a new handler)

- Detect `!prompt <text>` prefix in incoming messages
- Intercept before the agent loop
- Make a single LLM call with the prompt enhancer system prompt
- Return the enhanced prompt to the Discord channel
- User can then copy and send it as a real instruction

Estimated: ~30 lines

### Step 6: Tests

**File**: `inotagent/tests/test_prompt_gen.py` (new)

- Test system prompt is non-empty
- Test config loading (default model, fallbacks, max_tokens)
- Test API route returns enhanced prompt (mocked LLM)
- Test fallback triggers on primary model failure

**File**: `tests/test_ui.py`

- Test `/api/prompt-gen` route exists and returns expected shape

Estimated: ~40 lines

---

## Summary

| Component | File | Lines |
|---|---|---|
| Platform config | `platform.yml` + `platform.py` | ~15 |
| API route | `ui/src/app/api/prompt-gen/route.ts` | ~50 |
| UI page | `ui/src/app/prompt-gen/page.tsx` | ~100 |
| Navigation | `ui/src/components/AppLayout.tsx` | ~5 |
| Discord handler | `inotagent/channels/discord.py` | ~30 |
| Tests | `test_prompt_gen.py` + `test_ui.py` | ~40 |
| **Total** | | **~240 lines** |

No new dependencies. No migrations. No new containers. No new tables.

## Status: DONE
