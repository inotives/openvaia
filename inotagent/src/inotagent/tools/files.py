"""File tools — read, list, and search files."""

from __future__ import annotations

import fnmatch
import logging
import os
import re

logger = logging.getLogger(__name__)

READ_FILE_TOOL = {
    "name": "read_file",
    "description": "Read the contents of a file.",
    "input_schema": {
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "Absolute path to the file"},
            "max_lines": {"type": "integer", "description": "Max lines to read (default 500)"},
        },
        "required": ["path"],
    },
}

LIST_FILES_TOOL = {
    "name": "list_files",
    "description": "List files in a directory, optionally with glob pattern.",
    "input_schema": {
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "Directory path"},
            "pattern": {"type": "string", "description": "Glob pattern (default '*')"},
        },
        "required": ["path"],
    },
}

SEARCH_FILES_TOOL = {
    "name": "search_files",
    "description": "Search for a regex pattern in files (grep-like).",
    "input_schema": {
        "type": "object",
        "properties": {
            "pattern": {"type": "string", "description": "Regex pattern to search for"},
            "path": {"type": "string", "description": "Directory to search in"},
            "glob": {"type": "string", "description": "File pattern filter (default '*')"},
        },
        "required": ["pattern", "path"],
    },
}

FILE_TOOLS = [READ_FILE_TOOL, LIST_FILES_TOOL, SEARCH_FILES_TOOL]

MAX_OUTPUT_CHARS = 50_000


async def read_file(path: str, max_lines: int = 500) -> str:
    """Read file contents, limited to max_lines."""
    try:
        with open(path, encoding="utf-8", errors="replace") as f:
            lines = []
            for i, line in enumerate(f):
                if i >= max_lines:
                    lines.append(f"\n... (truncated at {max_lines} lines)")
                    break
                lines.append(line)
        return "".join(lines) or "(empty file)"
    except FileNotFoundError:
        return f"Error: File not found: {path}"
    except IsADirectoryError:
        return f"Error: Path is a directory: {path}"
    except PermissionError:
        return f"Error: Permission denied: {path}"


async def list_files(path: str, pattern: str = "*") -> str:
    """List files matching a glob pattern in a directory."""
    try:
        entries = sorted(os.listdir(path))
    except FileNotFoundError:
        return f"Error: Directory not found: {path}"
    except PermissionError:
        return f"Error: Permission denied: {path}"

    matched = [e for e in entries if fnmatch.fnmatch(e, pattern)]

    if not matched:
        return f"No files matching '{pattern}' in {path}"

    lines = []
    for name in matched:
        full_path = os.path.join(path, name)
        suffix = "/" if os.path.isdir(full_path) else ""
        lines.append(f"{name}{suffix}")

    output = "\n".join(lines)
    if len(output) > MAX_OUTPUT_CHARS:
        output = output[:MAX_OUTPUT_CHARS] + "\n... (truncated)"
    return output


async def search_files(pattern: str, path: str, glob: str = "*") -> str:
    """Search for a regex pattern in files under path."""
    try:
        regex = re.compile(pattern)
    except re.error as e:
        return f"Error: Invalid regex pattern: {e}"

    if not os.path.isdir(path):
        return f"Error: Directory not found: {path}"

    matches: list[str] = []
    total_chars = 0

    for root, _dirs, files in os.walk(path):
        for filename in sorted(files):
            if not fnmatch.fnmatch(filename, glob):
                continue
            filepath = os.path.join(root, filename)
            try:
                with open(filepath, encoding="utf-8", errors="replace") as f:
                    for lineno, line in enumerate(f, 1):
                        if regex.search(line):
                            rel = os.path.relpath(filepath, path)
                            entry = f"{rel}:{lineno}: {line.rstrip()}"
                            matches.append(entry)
                            total_chars += len(entry)
                            if total_chars > MAX_OUTPUT_CHARS:
                                matches.append("... (truncated)")
                                return "\n".join(matches)
            except (PermissionError, OSError):
                continue

    if not matches:
        return f"No matches for '{pattern}' in {path}"
    return "\n".join(matches)
