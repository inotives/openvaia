---
name: task_workflow_ino
description: Ino research task workflow — investigate, report, store, notify
tags: [workflow, research]
source: openvaia/v1-migration-seed
---

## Task Workflow

> ~441 tokens
1. Check for pending tasks AND tasks you created that need review:
   ```
   task_list(assigned_to="ino", status="todo,in_progress")
   task_list(created_by="ino", status="review")
   ```
   If there are tasks in `review`, verify them first (see verify_created_tasks skill).
2. Pick the highest priority `todo` task and set it to `in_progress`:
   ```
   task_update(key="<task_key>", status="in_progress")
   ```
3. Research the topic -- use `browser` to read docs, APIs, articles:
   ```
   browser(url="https://docs.coingecko.com/v3.0.1/reference/introduction")
   ```
4. For data that needs processing, write quick scripts using `write_file` + `shell`:
   ```
   write_file(path="/workspace/scratch/fetch_tokens.py", content="import requests\n...")
   shell(command="python3 /workspace/scratch/fetch_tokens.py", timeout=300)
   ```
5. Compile findings into a structured report (see report_format skill)
6. Save the report to the database:
   ```
   research_store(title="CoinGecko API Analysis", summary="- Supports 14k tokens\n- Free tier: 30 req/min", body="<full markdown report>", tags=["crypto", "coingecko", "api"], task_key="<task_key>")
   ```
7. Update the task to done with a summary:
   ```
   task_update(key="<task_key>", status="done", result="Research complete. Report saved (id=1)")
   ```
8. **Post summary to Discord #tasks so Boss can see**
9. Move on to the next task

If blocked:
```
task_update(key="<task_key>", status="blocked", result="Reason for block")
discord_send(channel_id="1482793839583559881", message="blocked <task_key>: Reason")
```
