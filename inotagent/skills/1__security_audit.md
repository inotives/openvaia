---
name: security_audit
description: Security audit — secrets archaeology, supply chain, CI/CD, LLM security, OWASP Top 10, STRIDE threat model
tags: [security, audit, compliance]
source: gstack/garrytan/gstack
---
# Security Audit (CSO)

Comprehensive security audit covering attack surface mapping, secrets, dependencies, infrastructure, and LLM-specific risks.

## When to Use

- Before production deployment
- After adding new dependencies or integrations
- Periodic security review (weekly/monthly)
- After a security incident

## Audit Phases

### Phase 0: Stack Detection
- Identify languages, frameworks, databases, cloud services
- Build mental model of the architecture
- Map data flow between components

### Phase 1: Attack Surface Mapping
- List all entry points: APIs, webhooks, forms, file uploads, WebSocket endpoints
- Identify authentication boundaries (what's public vs protected)
- Map trust zones (frontend → backend → database → external APIs)

### Phase 2: Secrets Archaeology
- Scan git history for leaked secrets: `git log -p | grep -i "key\|secret\|token\|password"`
- Check for secrets in environment files committed to repo
- Verify `.gitignore` covers all credential files
- Check if secrets are hardcoded in source (not just env vars)

### Phase 3: Dependency Supply Chain
- Check for known vulnerabilities in dependencies
- Identify unmaintained packages (no updates in 12+ months)
- Look for typosquatting risks in package names
- Verify lock files are committed and dependencies pinned

### Phase 4: CI/CD Pipeline Security
- Are secrets exposed in build logs?
- Can PRs from forks access production secrets?
- Are deployment credentials scoped minimally?
- Is the deployment pipeline auditable?

### Phase 5: Infrastructure
- Open ports, exposed services
- Default credentials on databases/admin panels
- TLS configuration (certificates, cipher suites)
- Network segmentation between services

### Phase 6: Webhook & Integration Audit
- Are incoming webhooks validated (signatures, source IP)?
- Can webhook payloads trigger destructive operations?
- Are outgoing API calls using HTTPS?
- Rate limiting on external-facing endpoints

### Phase 7: LLM & AI Security
- **Prompt injection**: Can user input manipulate LLM behavior?
- **Tool validation**: Are LLM tool calls validated before execution?
- **Output sanitization**: Is LLM output used in SQL/shell/HTML without escaping?
- **Data exfiltration**: Can LLM be tricked into revealing system prompts or credentials?
- **Cost attacks**: Can users trigger expensive LLM calls without rate limits?

### Phase 8: OWASP Top 10 Check

| Risk | What to verify |
|------|---------------|
| Injection | SQL, NoSQL, OS command, LDAP injection vectors |
| Broken Auth | Session management, credential storage, MFA |
| Sensitive Data Exposure | Encryption at rest/transit, PII handling |
| XXE | XML parser configuration |
| Broken Access Control | Authorization checks on every endpoint |
| Security Misconfiguration | Default configs, unnecessary features enabled |
| XSS | Output encoding, Content Security Policy |
| Insecure Deserialization | Untrusted data deserialization |
| Vulnerable Components | Known CVEs in dependencies |
| Insufficient Logging | Security events logged and monitored |

## Output: Security Posture Report

```
## Security Posture Report

**Date:** YYYY-MM-DD
**Scope:** [what was audited]
**Overall Risk:** [LOW / MEDIUM / HIGH / CRITICAL]

### Critical Findings (fix immediately)
1. [finding] — [location] — [remediation]

### High Findings (fix this sprint)
1. [finding] — [location] — [remediation]

### Medium Findings (fix this quarter)
1. [finding] — [location] — [remediation]

### Low Findings (backlog)
1. [finding] — [location] — [remediation]

### Positive Observations
- [what's done well]
```

## Rules

- **Report only, NO code changes** — audit produces findings, not fixes
- **After 3 failed investigation attempts, escalate** — don't guess on security
- **Don't ship uncertain security decisions** — when in doubt, flag it
- **Confidence threshold**: 8/10 for daily audits, 2/10 for comprehensive scans
