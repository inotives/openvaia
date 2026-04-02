---
name: requirement_specification
description: Write behavioral requirements using RFC 2119 keywords with Given/When/Then scenarios
tags: [planning, spec, requirements]
source: openspec/Fission-AI/OpenSpec
---
# Requirement Specification

Write behavioral requirements that define WHAT the system should do (not HOW). Each requirement is independently testable via Given/When/Then scenarios.

## When to Use

- After a proposal (`PROP:`) is approved
- When defining what "done" looks like before implementation
- When requirements need to be precise and verifiable
- For any change that modifies observable system behavior

## Spec Format

### Purpose
One paragraph: what domain this spec covers and why it exists.

### Requirements (use RFC 2119 keywords)

| Keyword | Meaning | Use When |
|---------|---------|----------|
| **MUST / SHALL** | Absolute requirement | Non-negotiable behavior |
| **SHOULD** | Recommended, can be skipped with justification | Best practice |
| **MAY** | Optional, at implementer's discretion | Nice-to-have |

### Scenarios (Given/When/Then)

Each requirement needs at least one scenario. Cover:
- **Happy path** — normal successful flow
- **Edge cases** — boundary conditions, empty states
- **Error cases** — what happens when things go wrong

## Template

```markdown
# [Domain] Specification

## Purpose
[What this spec covers and why]

## Requirements

### Requirement: [Name]
The system MUST [observable behavior].

#### Scenario: [Happy Path]
- GIVEN [initial state or precondition]
- WHEN [action or trigger]
- THEN [observable result]

#### Scenario: [Edge Case]
- GIVEN [edge condition]
- WHEN [action]
- THEN [different result]

#### Scenario: [Error Case]
- GIVEN [error condition]
- WHEN [action]
- THEN [error handling behavior]
```

## Example

```markdown
# Authentication Specification

## Purpose
Defines user authentication behavior for the platform.

## Requirements

### Requirement: Password Login
The system MUST authenticate users via email and password.

#### Scenario: Successful Login
- GIVEN a registered user with valid credentials
- WHEN they submit email and password
- THEN they receive an access token AND are redirected to dashboard

#### Scenario: Invalid Password
- GIVEN a registered user
- WHEN they submit an incorrect password
- THEN they receive a 401 error AND the failed attempt is logged

#### Scenario: Account Lockout
- GIVEN a user with 5 consecutive failed login attempts
- WHEN they attempt to login again
- THEN the account MUST be locked for 30 minutes AND user is notified via email

### Requirement: Session Expiry
The system SHOULD expire inactive sessions after 24 hours.

#### Scenario: Expired Session
- GIVEN a user with a session older than 24 hours
- WHEN they make an API request
- THEN they receive a 401 error AND must re-authenticate
```

## What Goes in a Spec (and What Doesn't)

**Good spec content:**
- Observable behavior users or systems rely on
- Inputs, outputs, and error conditions
- External constraints (security, privacy, reliability)
- Testable scenarios

**Does NOT belong in specs:**
- Internal class/function names (→ put in design)
- Library or framework choices (→ put in design)
- Step-by-step implementation details (→ put in plan)
- Database schema or code structure (→ put in design)

## Storage

Store the spec as a research report with `SPEC:` prefix and `spec` tag:
```
research_store(
  title="SPEC: [Domain Name]",
  body="[full spec content]",
  tags=["spec", "<domain-tags>"]
)
```

## Progressive Rigor

- **Lite spec (default):** 2-5 requirements, key scenarios, scope/non-goals. Good for most features.
- **Full spec (high risk):** Exhaustive requirements, all edge cases, cross-team impact. Use for: API changes, data migrations, security features, multi-service changes.

## Process

1. Read the approved proposal (`research_search(tags=["proposal"])`)
2. Write requirements using RFC 2119 keywords
3. Add Given/When/Then scenarios for each requirement
4. Store via `research_store` with `SPEC:` prefix and `spec` tag
5. Present to human for review
6. If approved → proceed to technical design (`DESIGN:`)
