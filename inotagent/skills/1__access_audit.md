---
name: access_audit
description: Audit user and service account permissions, detect stale accounts, find privilege escalation paths, and enforce least privilege.
tags: [security, iam, access-control, compliance]
source: awesome-openclaw-agents/agents/security/access-auditor
---

## Access Audit

> ~656 tokens

### Audit Workflow

1. Inventory all users, roles, and service accounts
2. Map permissions across cloud platforms (AWS IAM, GCP IAM, Azure AD)
3. Identify over-privileged accounts
4. Detect stale accounts (no login in 90+ days)
5. Analyze privilege escalation paths
6. Generate remediation plan in priority order

### Findings Categories

#### Over-Privileged Accounts

Flag accounts with admin access that:
- Do not need it for their role
- Have not used admin-level actions in 30+ days
- Are service accounts with broader access than required

#### Stale Accounts

| Threshold | Action |
|-----------|--------|
| 30+ days inactive | Flag for review |
| 90+ days inactive | Recommend disable |
| Former employee | Remove immediately |

#### Privilege Escalation Paths

Check for indirect paths to elevated access:
- Users who can create new IAM users
- Roles with `iam:PassRole` for any role
- Users who can modify their own permissions
- Service accounts with overly broad `AssumeRole` permissions

### Audit Report Format

```
Access Audit -- <date>

Accounts Analyzed: <N> users, <N> roles, <N> service accounts
Systems: <scope>

Critical Findings:
1. <N> users with excessive privileges
   | User | Last Activity | Role | Recommendation |

2. <N> stale accounts
   | User | Last Activity | Created |

3. <N> privilege escalation paths
   - <description of each path>

Summary:
| Category | Count | Status |
|----------|-------|--------|
| Over-privileged | N | Action needed |
| Stale accounts | N | Remove or disable |
| Escalation paths | N | Review and restrict |
| Compliant | N | No action |
| Documented exceptions | N | Accepted risk |
```

### Least Privilege Policy Workflow

When scoping down a service account:
1. Review CloudTrail/audit logs for actual API calls made
2. Draft a scoped IAM policy covering only needed actions
3. Test in a non-production environment first
4. Run a full operation cycle to verify
5. Check audit logs for denied actions
6. Once verified, remove the broad policy

### Remediation Priority Order

1. **Immediate:** Remove former employees and contractors
2. **This week:** Scope service accounts to least privilege
3. **This sprint:** Fix privilege escalation paths
4. **Ongoing:** Schedule quarterly access reviews

### Rules

- Always specify the date range and systems covered in any audit report
- Flag any account with admin access unused for 30+ days
- Never recommend removing access without explaining the risk of keeping it
- Always recommend a verification step before revoking access (false positives happen)
- Document exceptions with explicit risk acceptance
