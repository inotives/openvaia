---
name: game_design_systems
description: Gameplay loop templates, economy balancing, mechanic specs, and onboarding checklists for game design
tags: [game-design, gameplay-loops, economy-balance, onboarding, mechanics]
source: agency-agents/game-development/game-designer.md
---

## Game Design Systems

> ~1800 tokens

### Core Gameplay Loop Template

```markdown
# Core Loop: [Game Title]

## Moment-to-Moment (0-30 seconds)
- **Action**: Player performs [X]
- **Feedback**: Immediate [visual/audio/haptic] response
- **Reward**: [Resource/progression/intrinsic satisfaction]

## Session Loop (5-30 minutes)
- **Goal**: Complete [objective] to unlock [reward]
- **Tension**: [Risk or resource pressure]
- **Resolution**: [Win/fail state and consequence]

## Long-Term Loop (hours-weeks)
- **Progression**: [Unlock tree / meta-progression]
- **Retention Hook**: [Daily reward / seasonal content / social loop]
```

### Economy Balance Spreadsheet Template

```
Variable          | Base Value | Min | Max | Tuning Notes
------------------|------------|-----|-----|-------------------
Player HP         | 100        | 50  | 200 | Scales with level
Enemy Damage      | 15         | 5   | 40  | [PLACEHOLDER] - test at level 5
Resource Drop %   | 0.25       | 0.1 | 0.6 | Adjust per difficulty
Ability Cooldown  | 8s         | 3s  | 15s | Feel test: does 8s feel punishing?
```

Rules:
- Every economy variable must have a rationale -- no magic numbers
- All numerical values start as hypotheses -- mark `[PLACEHOLDER]` until playtested
- Build tuning spreadsheets with formulas, not hardcoded values
- Define target curves (XP to level, damage falloff, economy flow) mathematically

### Mechanic Specification Format

```markdown
## Mechanic: [Name]

**Purpose**: Why this mechanic exists in the game
**Player Fantasy**: What power/emotion this delivers
**Input**: [Button / trigger / timer / event]
**Output**: [State change / resource change / world change]
**Success Condition**: [What "working correctly" looks like]
**Failure State**: [What happens when it goes wrong]
**Edge Cases**:
  - What if [X] happens simultaneously?
  - What if the player has [max/min] resource?
**Tuning Levers**: [List of variables that control feel/balance]
**Dependencies**: [Other systems this touches]
```

### Player Onboarding Flow Checklist

```markdown
## Onboarding Checklist
- [ ] Core verb introduced within 30 seconds of first control
- [ ] First success guaranteed -- no failure possible in tutorial beat 1
- [ ] Each new mechanic introduced in a safe, low-stakes context
- [ ] Player discovers at least one mechanic through exploration (not text)
- [ ] First session ends on a hook -- cliff-hanger, unlock, or "one more" trigger
```

### Design Workflow Process

1. **Concept to Design Pillars** -- Define 3-5 non-negotiable player experiences. Every future design decision is measured against these pillars.
2. **Paper Prototype** -- Sketch the core loop on paper or spreadsheet before code. Identify the "fun hypothesis" -- the single thing that must feel good.
3. **GDD Authorship** -- Write mechanics from the player's perspective first, then implementation notes. Include annotated wireframes for complex systems. Flag all `[PLACEHOLDER]` values.
4. **Balancing Iteration** -- Build tuning spreadsheets with formulas. Define target curves mathematically. Run paper simulations before build integration.
5. **Playtest and Iterate** -- Define success criteria before each session. Separate observation (what happened) from interpretation (what it means). Prioritize feel issues over balance issues in early builds.

### Documentation Standards

- Every mechanic documented with: purpose, player experience goal, inputs, outputs, edge cases, failure states
- GDDs are living documents -- version every significant revision with a changelog
- Design from player motivation outward, not feature list inward
- Every system must answer: "What does the player feel? What decision are they making?"
- Never add complexity that doesn't add meaningful choice

### Advanced Economy Design

- Model player economies as supply/demand systems: plot sources, sinks, and equilibrium curves
- Design for player archetypes: whales need prestige sinks, dolphins need value sinks, minnows need earnable aspirational goals
- Implement inflation detection: define the metric (currency per active player per day) and the threshold that triggers a balance pass
- Use Monte Carlo simulation on progression curves to identify edge cases before code

### Systemic Design and Emergence

- Design systems that interact to produce emergent player strategies
- Document system interaction matrices: for every system pair, define whether interaction is intended, acceptable, or a bug
- Playtest specifically for emergent strategies: incentivize playtesters to "break" the design
- Balance for minimum viable complexity -- remove systems that don't produce novel player decisions
