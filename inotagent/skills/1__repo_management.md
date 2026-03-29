---
name: repo_management
description: How to check, clone, and sync repos before working
tags: [repo, git]
source: openvaia/v1-migration-seed
---

## Repo Management

> ~242 tokens
Repos are assigned to you via the `agent_repos` table.

**When a task references a repo:**
1. Check if the repo exists locally:
   ```
   list_files(path="/workspace/repos")
   ```
2. If the repo is NOT in `/workspace/repos/`:
   ```
   shell(command="git clone <repo_url> /workspace/repos/<repo-name>")
   ```
3. If already cloned, sync to latest:
   ```
   shell(command="cd /workspace/repos/<repo-name> && git checkout main && git pull origin main")
   ```
4. **Read the repo's instructions before working** -- check for these files in order:
   ```
   read_file(path="/workspace/repos/<repo-name>/CLAUDE.md")
   read_file(path="/workspace/repos/<repo-name>/AGENTS.md")
   read_file(path="/workspace/repos/<repo-name>/README.md")
   ```
   Follow any conventions, project structure, or setup steps documented there.
