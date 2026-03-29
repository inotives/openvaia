---
name: engineering_retro
description: Weekly engineering retrospective — git telemetry, work sessions, commit patterns, team metrics, shipping streaks
tags: [retrospective, analytics, team]
source: gstack/garrytan/gstack
---
# Engineering Retrospective

Multi-dimensional work analysis using git telemetry for weekly team retrospectives.

## When to Use

- Weekly team retrospective
- Sprint review / end-of-sprint analysis
- Performance review preparation
- Understanding team work patterns

## The Process

### Step 1: Gather Raw Data
Parallel git commands for the time window (default: 7 days):
```
git log --since="7 days ago" --format="%H|%an|%ae|%at|%s" --all
git shortlog --since="7 days ago" -sn --all
git diff --stat HEAD~<commits>
```

### Step 2: Compute Metrics
- Total commits, unique contributors
- Lines added/removed
- Test file ratio (test files changed / total files changed)
- Average commit size

### Step 3: Commit Time Distribution
Hourly histogram — when does the team work?
- Peak hours, after-hours work, weekend activity
- Individual patterns vs team patterns

### Step 4: Work Session Detection
Group commits by 45-minute gaps:

| Session Type | Duration | Meaning |
|-------------|----------|---------|
| **Deep** | 50+ min | Focused implementation or debugging |
| **Medium** | 20-50 min | Feature work, reviews |
| **Micro** | < 20 min | Quick fixes, config changes |

### Step 5: Commit Type Breakdown
Classify by conventional commit prefix:
- `feat:` — new features
- `fix:` — bug fixes
- `refactor:` — code improvements
- `test:` — test additions/changes
- `chore:` — maintenance
- `docs:` — documentation

### Step 6: Hotspot Analysis
Most-changed files:
- High churn = potential instability or active development area
- Files changed by multiple people = coordination needed
- Test files in hotspots = good (tests evolving with code)

### Step 7: PR Size Distribution
| Bucket | Lines Changed | Verdict |
|--------|--------------|---------|
| Small | < 100 | Ideal — easy to review |
| Medium | 100-300 | Acceptable |
| Large | 300-1000 | Hard to review well |
| XL | 1000+ | Break it up |

### Step 8: Per-Contributor Analysis
For each team member:
- Commits, lines changed, areas of focus
- Commit type mix (feature-heavy? fix-heavy?)
- Session patterns (deep work vs micro commits)
- Test discipline (% of commits touching tests)
- Biggest ship of the week

### Step 9: Shipping Streak
Track consecutive days with at least one merge to main:
- Current streak length
- Longest streak this quarter
- Celebrate streaks, investigate gaps

### Step 10: Week-over-Week Trends
If historical data available:
- Velocity trending up or down?
- Test ratio improving?
- PR sizes shrinking (good) or growing?
- Deep sessions increasing?

## Output

```
## Engineering Retro — Week of YYYY-MM-DD

### Highlights
- Ship of the Week: [biggest feature/fix]
- Shipping streak: N days

### Team Metrics
| Metric | This Week | Last Week | Trend |
|--------|-----------|-----------|-------|
| Commits | 47 | 52 | ↓ |
| Contributors | 3 | 3 | → |
| Test ratio | 35% | 28% | ↑ |

### Per-Contributor
**[Name]** — 22 commits, 1.2K LOC
- Focus: auth module, API endpoints
- Sessions: 4 deep, 6 medium, 3 micro
- Highlight: shipped OAuth integration

### Action Items
1. [what to improve next week]
```
