---
name: research_methodology
description: Ino systematic research approach — check existing, scope, multi-source, cross-reference
tags: [research, methodology]
source: openvaia/v1-migration-seed
---

## Research Methodology

> ~341 tokens

**Before starting any research task:**
1. Search existing reports first -- don't duplicate work:
   ```
   research_search(query="<topic keywords>", tags=["<relevant tags>"])
   memory_search(query="<topic>", tags=["<domain>"])
   ```
2. If a relevant report exists, read it and build on it rather than starting from scratch:
   ```
   research_get(report_id=<id>)
   ```

**During research:**
3. Define scope -- what specific questions need answering? Write them down before browsing.
4. Use multiple sources -- don't rely on a single page. Cross-reference data across:
   - Official documentation
   - API endpoints (test them directly via `shell` + `curl`)
   - Community resources (GitHub issues, forums)
5. Verify claims -- if a doc says "supports X", test it:
   ```
   shell(command="curl -s 'https://api.example.com/endpoint' | python3 -m json.tool")
   ```
6. Note discrepancies -- if sources disagree, document both and flag the conflict.

**After research:**
7. Always save via `research_store` -- this is your primary output.
8. Tag thoroughly -- future searches depend on good tags.
9. If the research reveals a coding task, create it rather than doing it yourself:
   ```
   task_create(title="Implement <finding>", description="Based on research: <summary>")
   ```
