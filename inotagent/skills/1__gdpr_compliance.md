---
name: gdpr_compliance
description: Audit systems for GDPR compliance gaps, map data flows, and generate remediation plans with article references.
tags: [compliance, gdpr, privacy, legal]
source: awesome-openclaw-agents/agents/compliance/gdpr-auditor
---

## GDPR Compliance

> ~743 tokens

*Disclaimer: This is compliance guidance, not legal advice. Consult qualified legal counsel for binding opinions.*

### Compliance Audit Checklist

#### Critical (High Fine Risk)

- [ ] **Lawful basis documented** (Art. 6(1)) -- Identify and document lawful basis for each processing activity
- [ ] **Data Processing Agreements** (Art. 28) -- Signed DPAs with all third-party processors
- [ ] **DSAR process** (Art. 15-20) -- Workflow to handle access, export, and deletion requests within 30 days
- [ ] **Breach notification** (Art. 33-34) -- Process to notify authority within 72 hours

#### Medium Risk

- [ ] **Privacy policy complete** (Art. 13) -- Includes retention periods, lawful basis, DPO contact, complaint rights
- [ ] **Cookie consent** (ePrivacy + Art. 6/7) -- Prior consent for non-essential cookies with granular controls
- [ ] **Data minimization** (Art. 5(1)(c)) -- Only collect data necessary for stated purpose
- [ ] **Records of processing** (Art. 30) -- Documented register of processing activities

#### Recommended

- [ ] **DPIA completed** (Art. 35) -- For high-risk processing activities
- [ ] **Privacy by design** (Art. 25) -- Data protection built into system architecture
- [ ] **Cross-border transfer safeguards** (Art. 44-49) -- SCCs or adequacy decisions for non-EU transfers

### Data Flow Mapping

Document for each data type:
1. Collection point (where/how collected)
2. Storage location (which systems/databases)
3. Processing purpose (why it is processed)
4. Lawful basis (consent, contract, legitimate interest, etc.)
5. Retention period
6. Cross-border transfers (which countries, what safeguards)
7. Processors and sub-processors

### DPO Requirement Assessment (Art. 37)

A DPO is mandatory if any apply:
- Public authority or body
- Core activity involves large-scale systematic monitoring of individuals
- Core activity involves large-scale processing of special category data

Threshold factors: number of EU data subjects, granularity of tracking, session-level profiling.

### Remediation Timeline Template

| Week | Actions |
|------|---------|
| 1-2 | Lawful basis register, privacy policy update |
| 2-3 | DSAR workflow, cookie consent implementation |
| 3-4 | DPA inventory and execution |
| 4-6 | Data flow documentation, DPIA if needed |

### Fine Risk Reference

- Up to 4% of annual global turnover or EUR 20 million (whichever is higher) for serious violations
- Up to 2% or EUR 10 million for administrative violations

### Rules

- Always cite specific GDPR articles when identifying gaps
- Distinguish between legal requirements and recommended best practices
- Flag items requiring formal legal counsel or DPO review
- Prioritize findings by fine risk
- Do not assume consent is the appropriate lawful basis without analysis
- Do not overlook employee data processing
- Do not ignore data processor obligations under Article 28
