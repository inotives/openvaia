# Agent Email Send — Execution Plan

## Backstory

Agents produce valuable outputs — research reports, task summaries, data analysis — stored in Postgres. But when the owner is away from the workstation (mobile, traveling), accessing these results requires either opening the Admin UI or asking the agent to re-summarize on Discord, which costs additional LLM tokens and loses the full markdown formatting.

Each agent already has a Gmail address assigned (via `GIT_EMAIL` in `.env`) for git operations. These same accounts can send emails directly.

## Purpose

Add a `send_email` tool that allows agents to send formatted emails (markdown → HTML) to the owner when asked. Primary use case: *"Send me the Raydium research report to my email"* on Discord → agent fetches the report, converts to HTML, sends via Gmail SMTP → owner reads the full formatted report on their phone.

## User Flow

```
Owner on Discord: "email me the DeFi research report"
        ↓
Agent calls research_search to find the report
        ↓
Agent calls research_get to fetch full content
        ↓
Agent calls send_email(to="owner@gmail.com", subject="DeFi Research Report", body=<markdown content>)
        ↓
Tool converts markdown → HTML, sends via Gmail SMTP
        ↓
Agent confirms on Discord: "Report sent to owner@gmail.com"
        ↓
Owner reads full formatted report on phone
```

---

## Technical Design

### Tool Definition

```python
SEND_EMAIL_TOOL = {
    "name": "send_email",
    "description": "Send an email with markdown content (converted to HTML). Restricted to owner email only.",
    "input_schema": {
        "type": "object",
        "properties": {
            "to": {"type": "string", "description": "Recipient email address (must be in allowed list)"},
            "subject": {"type": "string", "description": "Email subject line"},
            "body": {"type": "string", "description": "Email body in markdown (will be converted to HTML)"},
        },
        "required": ["to", "subject", "body"],
    },
}
```

### Email Sending

- Use Python's built-in `smtplib` + `email.mime` — no new dependencies
- Gmail SMTP: `smtp.gmail.com:587` with TLS
- Authenticate with agent's Gmail + App Password
- Convert markdown body to HTML using a lightweight converter
- Send as multipart email (HTML + plain text fallback)

### Security — Email Whitelist

Agents must NOT be able to send emails to arbitrary addresses (prompt injection risk). Restrict via:

- `OWNER_EMAIL` env var in agent's `.env` — the only allowed recipient
- The tool validates `to` against `OWNER_EMAIL` before sending
- If `to` doesn't match, return error: "Email not sent — recipient not in allowed list"

### Credentials

One new env var per agent in `.env`:

```env
GMAIL_APP_PASSWORD=<16-char app password>
OWNER_EMAIL=owner@gmail.com
```

Gmail App Passwords are generated at https://myaccount.google.com/apppasswords (requires 2FA enabled on the Gmail account).

`GIT_EMAIL` (already in `.env`) is used as the sender address.

### Markdown to HTML

Two options:

**Option A (zero dependencies)**: Simple regex-based conversion — handle headers, bold, italic, lists, code blocks, links. Covers 90% of research report formatting. ~40 lines.

**Option B (new dependency)**: Use `markdown` or `mistune` package for full spec compliance. Adds a pip dependency but handles edge cases (tables, nested lists, etc.).

Recommend **Option A for v1** — research reports use straightforward markdown. Add a proper library later if formatting issues arise.

---

## Development Steps

### Step 1: Email tool handler

**File**: `inotagent/src/inotagent/tools/email.py` (new)

- `SendEmailTool` class with `send_email()` method
- Gmail SMTP connection via `smtplib`
- Markdown → HTML conversion (simple regex-based)
- Email whitelist validation against `OWNER_EMAIL`
- Tool definition constant

Estimated: ~80 lines

### Step 2: Register tool

**File**: `inotagent/src/inotagent/tools/setup.py`

- Import and register `send_email` tool (#17)
- Pass `agent_name`, `db_available` for config access

Estimated: ~5 lines

### Step 3: Agent env templates

**Files**: `agents/_template/.env.template`, `agents/ino/.env.template`, `agents/robin/.env.template`

- Add `GMAIL_APP_PASSWORD=` and `OWNER_EMAIL=` fields

Estimated: ~6 lines (2 per template)

### Step 4: Tests

**File**: `inotagent/tests/test_tools.py`

- Test email whitelist validation (allowed address passes, blocked address rejected)
- Test markdown → HTML conversion (headers, bold, code blocks)
- Test send_email with mocked SMTP (verify correct recipients, subject, body)
- Test missing GMAIL_APP_PASSWORD returns graceful error

Estimated: ~40 lines

### Step 5: Update tool count in docs

**Files**: `CLAUDE.md`, `README.md`, `docs/project_summary.md`, `docs/project_details.md`

- Update tool count from 15 → 16 (or whatever the count is after other enhancements)

Estimated: ~10 lines

---

## Summary

| Component | File(s) | Lines |
|---|---|---|
| Email tool handler | `tools/email.py` | ~80 |
| Register tool | `tools/setup.py` | ~5 |
| Env templates | `agents/*/.env.template` | ~6 |
| Tests | `test_tools.py` | ~40 |
| Doc updates | `CLAUDE.md`, `README.md`, etc. | ~10 |
| **Total** | | **~140 lines** |

No new pip dependencies (Option A). No migrations. No new containers. One new tool.

---

## Future Enhancements

- **Attachments**: Send research reports as PDF attachments (requires `weasyprint` or similar)
- **Email templates**: Branded HTML templates with OpenVAIA header/footer
- **Multiple recipients**: Allow a whitelist of emails (e.g., team members) in `platform.yml`
- **Scheduled email digests**: Daily/weekly email summary of agent activity
- **Inbound email**: Agents receive tasks via email (Gmail API watch)


## Status: DONE
