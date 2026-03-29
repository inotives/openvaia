---
name: task_workflow_robin
description: Robin coder task workflow — branch, code, PR, review
tags: [workflow, coding]
source: openvaia/v1-migration-seed
---

## Task Workflow

> ~519 tokens
**ONE branch per task, ONE PR at the end.** Do NOT create multiple branches for subtasks -- all related changes go on a single feature branch.

1. Check and sync the task's repo (see repo_management skill)
2. Check for pending tasks:
   ```
   task_list(assigned_to="robin", status="todo,in_progress")
   ```
3. Pick the highest priority `todo` task and set it to `in_progress`:
   ```
   task_update(key="<task_key>", status="in_progress")
   ```
4. Create a feature branch from up-to-date main:
   ```
   shell(command="cd /workspace/repos/<repo-name> && git checkout -b feature/description")
   ```
5. Do the work -- use `read_file`, `write_file`, `shell` to write and edit code directly:
   ```
   read_file(path="/workspace/repos/<repo-name>/src/main.py")
   write_file(path="/workspace/repos/<repo-name>/src/main.py", content="...")
   shell(command="cd /workspace/repos/<repo-name> && python3 -m pytest tests/")
   ```
6. Commit and push:
   ```
   shell(command="cd /workspace/repos/<repo-name> && git add -A && git commit -m 'Description' && git push -u origin feature/description")
   ```
7. Raise a PR:
   ```
   shell(command="cd /workspace/repos/<repo-name> && gh pr create --title 'Title' --body 'Summary of changes'")
   ```
8. Set the task to `review` (NOT `done` -- the creator verifies and closes):
   ```
   task_update(key="<task_key>", status="review", result="PR raised: <url>")
   ```
9. **Notify the task creator:**
   - If created by another agent -> send them a platform message
   - Always post to Discord #tasks for Boss
10. Move on to the next task

**Important:** You set tasks to `review`, not `done`. The task creator reviews and sets `done` after verification.

If blocked:
```
task_update(key="<task_key>", status="blocked", result="Reason for block")
discord_send(channel_id="1482793839583559881", message="blocked <task_key>: Reason")
```
