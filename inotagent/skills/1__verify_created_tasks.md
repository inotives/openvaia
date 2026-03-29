---
name: verify_created_tasks
description: Review workflow for tasks delegated to other agents
tags: [workflow, review]
source: openvaia/v1-migration-seed
---

## Verify Created Tasks

> ~327 tokens
When you create tasks, you are responsible for verifying the result.

1. Check what's ready for review:
   ```
   task_list(created_by="ino", status="review")
   ```
2. Read the task result to get the PR url -- the `result` field contains the PR link.
3. **Verify the work** -- check the PR and the actual code changes:
   - Open the PR to read the summary and diff:
     ```
     browser(url="<PR url from task result>")
     ```
   - Clone/sync the repo and read the changed files directly:
     ```
     shell(command="cd /workspace/repos/<repo-name> && git fetch origin && git diff main..origin/<branch>")
     ```
   - Check if tests pass (if applicable):
     ```
     shell(command="cd /workspace/repos/<repo-name> && git checkout <branch> && make test")
     ```
   - Verify the changes match your original requirements
4. If satisfactory, mark as done:
   ```
   task_update(key="<task_key>", status="done", result="Verified: PR looks good")
   discord_send(channel_id="1482793839583559881", message="verified <task_key> and closed")
   ```
5. If changes needed, send back with feedback:
   ```
   task_update(key="<task_key>", status="todo", result="Changes needed: <feedback>")
   ```
