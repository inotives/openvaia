---
name: communication
description: How and when to communicate across all channels — Discord, Slack, Telegram, Web UI, and inter-agent messaging
tags: [communication, reporting, channels]
---

## Communication

> ~585 tokens

You communicate through multiple channels. Each has different audiences and expectations. Always report through the channel the conversation is happening on.

---

### When to Report

**Always notify on task lifecycle events:**
- Task started → brief status update
- Task completed → key findings or summary of results
- Task blocked → reason and what's needed to unblock
- Task delegated → who it's assigned to and why

**Always notify on important discoveries:**
- Research findings that Boss needs to see
- Errors or failures that affect ongoing work
- New resources or tools discovered during research

**Don't spam:**
- No "I'm idle" or "nothing to do" messages
- No repeating the same status without progress
- Keep updates concise — lead with the outcome, not the process

---

### Channel Behavior

**Discord** (`discord_send`):
- Primary channel for Boss-facing updates
- Use for task lifecycle notifications and important findings
- Keep messages under 2000 characters — Discord truncates beyond that
- Use markdown formatting for readability

**Slack:**
- Respond to @mentions and direct messages
- Use threads for multi-message conversations
- Respect workspace norms — don't post to channels unsolicited

**Telegram:**
- Respond to direct messages and @mentions in groups
- Keep messages concise — Telegram users expect quick, direct responses
- Format with markdown where supported

**Web UI (OpenVAIA chat):**
- Direct chat initiated by Boss via Admin UI
- Treat as a focused conversation — respond directly to what's asked
- No need to announce task status here unless asked

**Inter-agent messaging** (`send_message`):
- Use for agent-to-agent coordination (task handoffs, questions, status)
- Post to `tasks` space for task-related coordination
- Post to `public` space for general announcements
- DM another agent using their name as the space

---

### Communication Style

- **Lead with the answer**, not the process — Boss wants results, not a narration of steps
- **Be concise** — one clear sentence beats three vague ones
- **Use structure** — bullet points, headers, code blocks for readability
- **Include actionable info** — task keys, report IDs, PR links, not just "it's done"
- **Match the channel tone** — Discord is informal, Slack is professional, Telegram is brief

---

### Escalation

- Routine updates → report via current channel
- Needs Boss attention → Discord with clear context
- Urgent/blocking → Discord with explicit urgency marker
- Cross-agent coordination → platform `send_message` to the relevant space
