---
name: memory_and_improvement
description: Always-on memory system — real-time learning, memory maintenance, and daily self-review
tags: [memory, self-improvement, learning, review, workflow]
---

## Memory & Self-Improvement

> ~1453 tokens

Memory is your competitive advantage. It compounds — every insight saved today makes you better tomorrow. This skill defines three modes: real-time (during tasks), maintenance (keeping memory clean), and review (end-of-day reflection).

---

### Mode 1: Real-Time (During Every Task)

#### Before Acting — Search First
Before starting any task or making a decision, check what you already know:
```
memory_search(query="<topic>", tags=["<domain>"])
```

Search when:
- Starting a new task — check for related past context
- Boss says: "remember", "recall", "last time", "previously", "before"
- Boss says: "we decided", "we agreed", "the plan was", "as discussed"
- Boss says: "preference", "convention", "standard", "usual", "always", "never"
- A task references a repo, API, or domain you've worked with before
- You're about to make a choice you might have made before

**Act on what you find.** Don't just search — use the results to inform your approach.

#### During Execution — Save Immediately
Don't wait for the daily review. Save learnings the moment they happen:

- A command or API call fails and you find the fix → **save now**
- Boss corrects your approach → **save now**
- You discover a gotcha or non-obvious behavior → **save now**
- An API returns unexpected data or has undocumented limits → **save now**
- You find a workaround for a recurring problem → **save now**

Format:
```
memory_store(content="[what happened] → [what works]", tags=["learning", "<topic>"], tier="long")
```

Examples:
```
memory_store(content="GeckoTerminal OHLCV returns max 1000 candles — paginate with 'before' param", tags=["learning", "geckoterminal", "api"], tier="long")
memory_store(content="Boss prefers comparison tables in research reports, not prose", tags=["preference", "boss", "research"], tier="long")
```

#### After Completion — One-Liner Takeaway
When finishing a task, save a brief outcome if it has reuse value:
```
memory_store(content="Completed INO-005: Solana DEX analysis. Best free API is GeckoTerminal. DeFiLlama good for TVL.", tags=["solana", "dex", "research-outcome"], tier="short")
```

**Don't save** things that are already in code, docs, research reports, or task results.

---

### Mode 2: Maintenance (Keep Memory Clean)

#### Search Before Saving
Always check for existing memories on the topic before creating a new one:
```
memory_search(query="<topic>", tags=["<relevant tag>"])
```
If a related memory exists, decide: update it, add to it, or skip saving.

#### Tier Discipline
- **`tier="long"`** — Durable knowledge: preferences, conventions, decisions, API behaviors, gotchas, Boss instructions. Never auto-pruned.
- **`tier="short"`** — Temporary context: current values, in-progress state, time-sensitive data. Auto-pruned after 30 days.

Promote short-term memories that prove useful over time to long-term.

#### Tag Consistently
Good tags make memories findable. Use:
- Domain tags: `crypto`, `solana`, `trading`, `api`
- Type tags: `learning`, `preference`, `decision`, `gotcha`
- Source tags: `boss`, `research`, `task-outcome`

#### What NOT to Save
- Things already in code or docs (derivable from source)
- One-off debugging steps that won't recur
- Temporary task state (use `task_update` result field instead)
- Information that changes frequently without context (save the pattern, not the number)

---

### Mode 3: Review (End of Daily Cycle)

This runs as a recurring task (`schedule:daily@00:00`). It's your deep reflection — the improvement loop.

#### Phase 1: Gather Data
- `task_list(assigned_to="<your name>", status="done,review")` — what did you complete?
- `research_search` — any reports created or updated?
- `memory_search(tags=["daily_review"])` — read your last review to compare progress

#### Phase 2: Evaluate Quality
For each task or output, honestly assess:
- **Did it succeed?** Was the result accepted, or did it need rework?
- **Was it efficient?** Did you take unnecessary steps or hit avoidable errors?
- **Was the output quality good?** Would Boss be satisfied?
- **Did you use the right tools?** Could `resource_search` or `delegate` have helped?

#### Phase 3: Identify Patterns (Proactive)
Look beyond individual incidents for recurring themes:
- **Repeated tool usage**: Same API/command 3+ times → candidate for a skill or resource
- **Recurring corrections**: Boss gave similar feedback more than once → formalize as a rule
- **Efficiency gaps**: Tasks that consistently take too many iterations → find the bottleneck
- **Missing knowledge**: Topics researched from scratch that should be in memory → save them
- **Quality trends**: Are outputs improving or degrading in specific areas?

#### Phase 4: Formalize Improvements
For patterns worth preserving beyond memory:

**Propose skill evolutions** (preferred — goes through human review):
```
# FIX — repair a broken/outdated skill:
skill_propose(type="fix", skill_name="<existing_skill>", direction="<what's wrong and how to fix>", proposed_content="<fixed content>")

# DERIVED — enhance or combine skills:
skill_propose(type="derived", skill_name="<parent_skill>", direction="<what to improve>", proposed_content="<enhanced content>")

# CAPTURED — extract a novel reusable pattern:
skill_propose(type="captured", proposed_name="<new_name>", direction="<what pattern discovered>", proposed_content="<new skill content>", proposed_tags=["<domain>"])
```

All proposals go to human review — do NOT use `skill_create` for evolution. Use `skill_propose` instead.

**Propose new resources:**
```
resource_add(url="<url>", name="<name>", description="<what it provides>", tags=["<domain>"])
```

#### Phase 5: Summarize
Store a daily review in long-term memory:
```
memory_store(
  content="## Daily Review — <today's date>\n\n### Completed\n<tasks>\n\n### Quality\n<honest self-evaluation>\n\n### Learnings Saved\n<what you stored today>\n\n### Patterns\n<what you noticed>\n\n### Improvements\n<skills/resources proposed>",
  tags=["daily_review", "<today's date>"],
  tier="long"
)
```

---

### Key Principles

- **Memory is always on** — search before acting, save during execution, not just at daily review
- **Proactive > reactive** — don't just fix errors, look for patterns that prevent them
- **Search before saving** — avoid duplicates, build on existing knowledge
- **Small improvements compound** — one learning per task = dramatically better agent in a month
- **Be honest in self-evaluation** — the point is improvement, not looking good
