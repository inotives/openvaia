---
name: resource_first_research
description: Research workflow — check past work, use curated resources, then browser, with time-awareness
tags: [research, workflow, resources, browser]
---

## Research Workflow

> ~834 tokens

When you receive a research task or need to find information, follow this order. Each step builds on the previous — don't skip ahead.

---

### Step 1: Check Past Research

Before doing any new research, check if this topic has been covered before:

```
research_search(query="<topic keywords>", tags=["<domain>"])
memory_search(query="<topic>", tags=["<domain>"])
```

**If past research exists:**
- Check the date — is it still relevant? Data older than 7 days may be stale for fast-moving topics (crypto prices, market data). Reference material (API docs, guides) stays valid longer.
- If recent and relevant → use it, don't duplicate effort
- If outdated → use as a starting point, verify and update key data points
- If partially relevant → build on it, fill the gaps

**Note the current date** (shown in your system prompt) and compare with past research dates.

---

### Step 2: Search Curated Resources

Use `resource_search` to find vetted, reliable sources:
```
resource_search(tags=["<topic>", "<domain>"])
```

- Curated resources have been prioritized (1-100) — higher score = more reliable
- Read the resource notes for usage tips, rate limits, and auth requirements
- Prefer curated sources over random web search — they're faster and more consistent

---

### Step 3: Fetch Data from Resources

Use the appropriate tool to get data from matched resources:

**For APIs (JSON data):**
```
shell(command="curl -s '<api_url>' | python3 -m json.tool | head -50")
```

**For web pages (documentation, articles, reports):**
```
browser(url="<page_url>", action="get_text")
```

**For structured data extraction:**
```
shell(command="curl -s '<api_url>' | python3 -c \"import sys,json; d=json.load(sys.stdin); print(json.dumps(d['key'], indent=2))\"")
```

Extract and structure the data you need before moving on.

---

### Step 4: Fall Back to Web Search

Only if curated resources are insufficient:

**Use `browser` for web pages:**
```
browser(url="https://relevant-site.com/topic", action="get_text")
```

**Use `shell` + `curl` for APIs:**
```
shell(command="curl -s 'https://api.example.com/endpoint' | python3 -m json.tool | head -100")
```

When doing general web research:
- Start with authoritative sources (official docs, project repos, established data providers)
- Cross-reference data across multiple sources when accuracy matters
- Note which sources worked well — propose them as curated resources later

---

### Step 5: Propose New Resources

If you discover a useful new source during research:
```
resource_add(
  url="<url>",
  name="<short name>",
  description="<what it provides>",
  tags=["<domain>", "<type>"],
  notes="<rate limits, auth, data quality notes>"
)
```

Priority guide:
- 80-100: Primary/authoritative source (official API, project docs)
- 50-79: Good general source (reliable third-party, community reference)
- 20-49: Niche or backup source (works but limited)

---

### Key Principles

- **Don't duplicate work** — always check past research and memory first
- **Time-aware** — note when past data was collected, verify if stale
- **Curated first** — vetted resources save time and produce consistent results
- **Browser for pages, curl for APIs** — use the right tool for the data type
- **Contribute back** — propose good sources via `resource_add` so future research is faster
