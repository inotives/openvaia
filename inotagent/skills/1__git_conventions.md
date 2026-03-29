---
name: git_conventions
description: Robin git workflow — branch naming, commit messages, PR descriptions
tags: [git, conventions]
source: openvaia/v1-migration-seed
---

## Git Conventions

> ~316 tokens

**Branch naming:**
- `feature/<short-description>` -- new functionality
- `fix/<short-description>` -- bug fixes
- `chore/<short-description>` -- maintenance, deps, config
- `refactor/<short-description>` -- code restructuring
- Use kebab-case: `feature/add-telegram-channel` not `feature/addTelegramChannel`
- Include task key when available: `feature/ROB-012-add-telegram-channel`

**Commit messages:**
- Format: `<type>: <short description>`
- Types: `feat`, `fix`, `chore`, `refactor`, `test`, `docs`
- Examples:
  - `feat: add Telegram channel integration`
  - `fix: handle empty response from CoinGecko API`
  - `chore: update slack-bolt to v1.21`
- Keep first line under 72 characters
- Add body for complex changes explaining **why**, not what

**PR descriptions:**
- Title matches the primary commit message
- Body includes:
  - **What** -- summary of changes (2-3 sentences)
  - **Why** -- context, task key, or issue reference
  - **Testing** -- what was tested and how
- Link the task key: `Task: ROB-012`
