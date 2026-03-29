---
name: dependency_scanning
description: Dependency vulnerability scanning, license compliance, and supply chain risk assessment
tags: [development, security, dependencies, supply-chain]
source: awesome-openclaw-agents/development/dependency-scanner
---

## Dependency Scanning

> ~803 tokens

### Scan Workflow

1. Parse dependency tree (direct + transitive dependencies)
2. Check each dependency version against CVE databases
3. Perform reachability analysis — is the vulnerable code path actually called?
4. Check for outdated packages and calculate upgrade risk
5. Audit licenses for compatibility with project license
6. Check for supply chain anomalies
7. Generate report, prioritized by severity

### Vulnerability Response SLAs

| Severity | CVSS Score | Patch Deadline |
|----------|-----------|----------------|
| Critical | 9.0-10.0  | 24 hours       |
| High     | 7.0-8.9   | 7 days         |
| Medium   | 4.0-6.9   | 30 days        |
| Low      | 0.1-3.9   | Next release   |

### Vulnerability Report Fields

For each vulnerability found, include:

- CVE ID
- CVSS score and severity
- Affected package and installed version
- Fixed version
- Reachability: is the vulnerable code path used in this project?
- Upgrade path and breaking change assessment

### Reachability Analysis

Not all vulnerabilities are exploitable. Check:

- Is the vulnerable function/module imported in the project?
- Is it reachable from any code path (not just installed as transitive dep)?
- Is the vulnerable input vector exposed (e.g., HTTP endpoint, file upload)?

Flag reachability as: Reachable / Conditional / Not Reachable

### License Compliance

**Permissive (generally safe):** MIT, Apache-2.0, BSD-2-Clause, BSD-3-Clause, ISC

**Copyleft (review required):**
- GPL-2.0 / GPL-3.0 — requires derivative works to be open-sourced
- LGPL — OK for dynamic linking, review for static linking
- MPL-2.0 — file-level copyleft, generally manageable

**Restricted (block in commercial/SaaS projects):**
- AGPL-3.0 — network use triggers copyleft (SaaS = immediate alert)
- SSPL — Server Side Public License, similar concern
- BSL — Business Source License, commercial restrictions

### Supply Chain Risk Indicators

Watch for these anomalies:

- [ ] Package maintainer changed in the last 90 days
- [ ] Package name is similar to a popular package (typosquatting)
- [ ] Sudden major version jump with no changelog
- [ ] Unusually large publish (injected payload)
- [ ] Package unpublished and re-published recently
- [ ] New dependencies added that seem unrelated to package purpose

### Auto-Upgrade Policy

- **Patch versions** (1.2.3 -> 1.2.4): Safe for auto-PR. Typically bug fixes only.
- **Minor versions** (1.2.x -> 1.3.0): Review changelog, may include new features. Manual review.
- **Major versions** (1.x -> 2.0): Breaking changes expected. Manual review and migration plan.

Never auto-merge. Auto-PR only, human reviews and merges.

### Lockfile Ecosystems

| Ecosystem | Lockfile | Manifest |
|-----------|----------|----------|
| Node.js   | package-lock.json / yarn.lock / pnpm-lock.yaml | package.json |
| Python    | uv.lock / requirements.txt / poetry.lock | pyproject.toml |
| Go        | go.sum | go.mod |
| Rust      | Cargo.lock | Cargo.toml |
| Java      | (varies) | pom.xml / build.gradle |
