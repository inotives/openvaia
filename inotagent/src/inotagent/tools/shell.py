"""Shell tool — execute system commands (git, gh, make, npm, etc.)."""

from __future__ import annotations

import asyncio
import logging

logger = logging.getLogger(__name__)

SHELL_TOOL = {
    "name": "shell",
    "description": (
        "Execute a shell command. Use for: git, gh, make, npm, system commands, "
        "file operations, and code editing."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "command": {"type": "string", "description": "The shell command to run"},
            "working_dir": {"type": "string", "description": "Working directory (absolute path)"},
            "timeout": {"type": "integer", "description": "Timeout in seconds (default 120)"},
        },
        "required": ["command"],
    },
}

# Maximum output length to return to LLM (avoid blowing up context)
MAX_OUTPUT_CHARS = 50_000


async def execute(command: str, working_dir: str | None = None, timeout: int = 120) -> str:
    """Execute a shell command and return stdout + stderr."""
    logger.info(f"Shell: {command}" + (f" (cwd={working_dir})" if working_dir else ""))

    proc = await asyncio.create_subprocess_shell(
        command,
        cwd=working_dir,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )

    try:
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
    except asyncio.TimeoutError:
        proc.kill()
        await proc.communicate()
        return f"Command timed out after {timeout}s"

    output = stdout.decode(errors="replace")
    if stderr:
        output += f"\nSTDERR:\n{stderr.decode(errors='replace')}"
    if proc.returncode != 0:
        output += f"\nExit code: {proc.returncode}"

    if len(output) > MAX_OUTPUT_CHARS:
        output = output[:MAX_OUTPUT_CHARS] + f"\n... (truncated, {len(output)} total chars)"

    return output or "(no output)"
