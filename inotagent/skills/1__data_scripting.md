---
name: data_scripting
description: Ino guide for writing data scripts in scratch directory
tags: [scripting, data]
source: openvaia/v1-migration-seed
---

## Data Scripting

> ~258 tokens
Use `/workspace/scratch/` for temporary data scripts. These are disposable -- not production code.

**Best practices:**
- Always use `async` + `asyncio` for API calls -- matches the codebase style
- Handle rate limits with delays between requests:
  ```python
  import asyncio
  await asyncio.sleep(0.5)  # Respect rate limits
  ```
- Parse JSON responses safely:
  ```python
  import json
  data = json.loads(response)
  ```
- Write results to a file for review before reporting:
  ```python
  with open("/workspace/scratch/results.json", "w") as f:
      json.dump(data, f, indent=2)
  ```
- Set appropriate timeouts for long-running scripts:
  ```
  shell(command="python3 /workspace/scratch/fetch_data.py", timeout=300)
  ```
- Clean up scratch files after use -- don't leave stale data lying around
- If a script will be reused, save it to the repo instead of scratch
