# Skill Templates from Community Agent Libraries — Execution Plan

## Backstory

The open-source AI agent community has produced large collections of agent persona templates — for example, [awesome-openclaw-agents](https://github.com/mergisi/awesome-openclaw-agents) has 187 templates across 24 categories (productivity, development, finance, DevOps, security, etc.). Each template is a `SOUL.md` file defining an agent's identity, responsibilities, behavioral guidelines, and domain expertise.

These templates contain valuable domain knowledge and workflow patterns, but they're designed for single-agent systems (one template = one agent). Running 187 containers doesn't make sense. What does make sense is extracting the **reusable domain knowledge** and converting it into OpenVAIA's DB-driven skills system — where any agent can equip the knowledge they need.

## Purpose

Create a workflow and tooling to **convert community agent templates into OpenVAIA skills**. Strip the identity/personality (we have our own agents), keep the workflows, checklists, domain expertise, and behavioral guidelines. Store them as skills that any agent can equip via the Admin UI.

This turns 187 single-purpose agent templates into a **skill library** that our existing agents can mix-and-match from.

## How It Works

```
Community template (SOUL.md / AGENTS.md)
        ↓
Extract domain knowledge:
  - Workflows and checklists
  - Domain-specific rules and guidelines
  - Tool usage patterns
  - Communication style rules (if applicable)
        ↓
Strip identity:
  - Remove name, personality, "You are X" framing
  - Remove channel-specific config
  - Remove references to other ecosystem tools
        ↓
Convert to OpenVAIA skill format:
  - name: snake_case (e.g., code_review_checklist)
  - description: one-liner
  - content: markdown (the extracted knowledge)
  - tags: from the template's category
        ↓
Add to skills DB via Admin UI or migration
        ↓
Agents equip relevant skills as needed
```

### Example Conversion

**Source**: `agents/development/code-reviewer/SOUL.md`

```markdown
# Lens - The Code Reviewer
You are Lens, an AI code reviewer...

## Responsibilities
1. PR Review — check for bugs, security issues, performance
2. Style enforcement — consistent naming, formatting
3. Documentation — verify docstrings, README updates

## Review Checklist
- [ ] No hardcoded secrets
- [ ] Error handling present
- [ ] Tests cover new code paths
- [ ] No N+1 queries
...
```

**Output skill**: `code_review_checklist`

```markdown
## Code Review Checklist

When reviewing code or PRs, verify:

### Security
- No hardcoded secrets or credentials
- No SQL injection or command injection risks
- Input validation at system boundaries

### Quality
- Error handling present for external calls
- Tests cover new code paths
- No N+1 queries or obvious performance issues

### Style
- Consistent naming conventions
- Docstrings on public functions
- README updated if user-facing changes
```

---

## Priority Categories

Based on relevance to our current agents (Ino = researcher, Robin = coder):

### High Priority (directly useful)
| Category | Templates | Maps to Agent |
|---|---|---|
| Development | code-reviewer, bug-hunter, test-writer, migration-helper | Robin |
| Finance | market-analyst, portfolio-tracker, risk-assessor | Ino |
| Data | data-analyst, etl-monitor | Robin |
| Security | security-auditor, dependency-scanner | Robin |
| DevOps | deploy-monitor, infra-checker | Robin |

### Medium Priority (useful with more agents)
| Category | Templates | Future Use |
|---|---|---|
| Productivity | task coordinator, standup, meeting notes | Manager agent |
| Marketing | content writer, SEO analyst | Content agent |
| E-Commerce | product analyst, pricing optimizer | Trading agent |

### Low Priority (niche)
| Category | Templates | Notes |
|---|---|---|
| Healthcare, Legal, HR, Real Estate | Various | Too domain-specific for current agents |
| Voice, Creative | Various | Not applicable to text-based agents |

---

## Development Steps

### Step 1: Clone and audit community templates

Clone `awesome-openclaw-agents` locally. Audit the high-priority categories and identify templates with the most extractable domain knowledge.

Deliverable: A shortlist of 15-20 templates to convert first.

Estimated: ~1 hour (manual review)

### Step 2: Create conversion script

**File**: `scripts/convert-template.sh` or `scripts/convert_template.py`

A helper script that:
1. Takes a SOUL.md file path as input
2. Strips identity sections (name, personality, "You are X")
3. Extracts workflow/checklist/guideline sections
4. Outputs a skill-formatted markdown file
5. Suggests name, description, and tags

This won't be fully automated — templates vary too much in structure. The script handles the common patterns and leaves the rest for manual editing.

Estimated: ~60 lines

### Step 3: Convert high-priority templates

Manually convert 15-20 high-priority templates into skills using the script + manual refinement.

Organize by category:
```
skills/
  development/
    code_review_checklist.md
    debugging_workflow.md
    test_writing_guide.md
    migration_safety.md
  finance/
    market_analysis_framework.md
    risk_assessment.md
    portfolio_review.md
  devops/
    deploy_checklist.md
    incident_response.md
  security/
    security_audit_checklist.md
    dependency_review.md
```

Estimated: ~2-3 hours (manual work)

### Step 4: Seed skills via migration

**File**: `infra/postgres/migrations/YYYYMMDD_add_community_skills.sql`

Insert converted skills into the `skills` table with:
- `global = false` (not auto-equipped — agents choose what they need)
- `enabled = true`
- Tags matching the source category
- Description noting the source template

Estimated: ~50-100 lines (depending on number of skills)

### Step 5: Document the conversion process

**File**: `docs/converting_community_templates.md`

A guide for converting future community templates:
- Where to find templates (awesome-openclaw-agents, other repos)
- What to extract vs what to discard
- Naming conventions for converted skills
- How to add via Admin UI vs migration

Estimated: ~40 lines

### Step 6: Add community attribution

For skills derived from community templates, include a source attribution in the skill description:

```
Adapted from: awesome-openclaw-agents/development/code-reviewer
Source: https://github.com/mergisi/awesome-openclaw-agents
License: MIT
```

This respects the original authors and helps track provenance.

---

## Summary

| Component | File(s) | Effort |
|---|---|---|
| Template audit | Manual review | ~1 hour |
| Conversion script | `scripts/convert_template.py` | ~60 lines |
| Convert 15-20 templates | Manual + script | ~2-3 hours |
| Seed migration | `infra/postgres/migrations/` | ~50-100 lines |
| Documentation | `docs/converting_community_templates.md` | ~40 lines |
| **Total** | | **~4-5 hours + 150 lines** |

No new dependencies. No new tools. One migration. Mostly manual curation work.

---

## Future Enhancements

- **Skill marketplace** — a UI page to browse available community skills by category and one-click equip
- **Auto-conversion pipeline** — use an LLM to batch-convert templates (with human review)
- **Community skill sharing** — agents can export their self-created skills for other OpenVAIA deployments
- **Skill versioning** — track which community template version a skill was derived from
- **Periodic sync** — watch community repos for new templates and flag them for review
