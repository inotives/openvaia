"""Shell tool — execute system commands (git, gh, make, npm, etc.)."""

from __future__ import annotations

import asyncio
import logging
import os
import signal

logger = logging.getLogger(__name__)

# Hard maximum timeout — LLM cannot override this
MAX_TIMEOUT = 300  # 5 minutes absolute max

SHELL_TOOL = {
    "name": "shell",
    "description": (
        "Execute a shell command. Use for: git, gh, make, npm, system commands, "
        "file operations, and code editing. "
        "IMPORTANT: Do NOT run long-running processes (servers, while True loops, daemons). "
        "Commands have a 120s default timeout (max 300s)."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "command": {"type": "string", "description": "The shell command to run"},
            "working_dir": {"type": "string", "description": "Working directory (absolute path)"},
            "timeout": {"type": "integer", "description": "Timeout in seconds (default 120, max 300)"},
        },
        "required": ["command"],
    },
}

# Maximum output length to return to LLM (avoid blowing up context)
MAX_OUTPUT_CHARS = 50_000


async def execute(command: str, working_dir: str | None = None, timeout: int = 120) -> str:
    """Execute a shell command and return stdout + stderr."""
    # Enforce hard max timeout — LLM cannot bypass
    timeout = min(timeout, MAX_TIMEOUT)

    logger.info(f"Shell: {command}" + (f" (cwd={working_dir})" if working_dir else ""))

    # Use process group so we can kill all children on timeout
    # setsid creates a new group for this command only — safe for other agents
    try:
        proc = await asyncio.create_subprocess_shell(
            command,
            cwd=working_dir,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            preexec_fn=os.setsid,
        )
    except OSError:
        # Fallback if setsid not available (some container runtimes)
        proc = await asyncio.create_subprocess_shell(
            command,
            cwd=working_dir,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

    try:
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
    except asyncio.TimeoutError:
        # Kill entire process group (parent + all children)
        try:
            os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
        except (OSError, ProcessLookupError):
            proc.kill()
        try:
            await asyncio.wait_for(proc.communicate(), timeout=5)
        except (asyncio.TimeoutError, ProcessLookupError):
            pass
        logger.warning(f"Shell: command timed out after {timeout}s — killed process group")
        return f"Command timed out after {timeout}s. Do NOT run long-running processes (servers, loops, daemons)."

    output = stdout.decode(errors="replace")
    if stderr:
        output += f"\nSTDERR:\n{stderr.decode(errors='replace')}"
    if proc.returncode != 0:
        output += f"\nExit code: {proc.returncode}"

    if len(output) > MAX_OUTPUT_CHARS:
        output = output[:MAX_OUTPUT_CHARS] + f"\n... (truncated, {len(output)} total chars)"

    return output or "(no output)"
