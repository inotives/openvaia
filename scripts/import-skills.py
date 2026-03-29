#!/usr/bin/env python3
"""Import skill files from inotagent/skills/ into the platform.skills DB table.

Filename prefix determines scope:
  0__<name>.md → global skill (injected into all agents)
  1__<name>.md → non-global skill (available in library, agents equip via UI)

Usage:
    python3 scripts/import-skills.py              # import new skills (skip existing)
    python3 scripts/import-skills.py --force      # delete all imported skills, re-import
    python3 scripts/import-skills.py --reset NAME # delete one skill, re-import from file
"""

import os
import re
import sys
from pathlib import Path

import psycopg


def parse_skill_file(path: Path) -> dict | None:
    """Parse a skill markdown file with frontmatter."""
    content = path.read_text()

    # Extract frontmatter between --- markers
    match = re.match(r"^---\n(.*?)\n---\n(.*)$", content, re.DOTALL)
    if not match:
        print(f"  SKIP {path.name} — no frontmatter")
        return None

    frontmatter, body = match.group(1), match.group(2).strip()

    # Parse frontmatter fields
    skill = {"content": body, "_path": path}
    for line in frontmatter.split("\n"):
        if ":" in line:
            key, val = line.split(":", 1)
            key = key.strip()
            val = val.strip()
            if key == "tags":
                val = [t.strip().strip("'\"") for t in val.strip("[]").split(",") if t.strip()]
            skill[key] = val

    if not skill.get("name"):
        print(f"  SKIP {path.name} — no name in frontmatter")
        return None

    return skill


def import_skill(conn, schema: str, skill: dict, force: bool = False) -> str:
    """Import a single skill. Returns 'ok', 'skip', or 'err'."""
    name = skill["name"]
    description = skill.get("description", "")
    tags = skill.get("tags", [])
    source = skill.get("source", "")
    content = skill["content"]
    path = skill["_path"]
    is_global = path.name.startswith("0__")

    if source:
        content += f"\n\n---\n*Source: {source}*"

    if force:
        conn.execute(
            f"DELETE FROM {schema}.skills WHERE name = %s AND created_by = 'import'",
            (name,),
        )

    try:
        cur = conn.execute(
            f"""INSERT INTO {schema}.skills (name, description, content, tags, global, enabled, status, created_by)
                VALUES (%s, %s, %s, %s, %s, true, 'active', 'import')
                ON CONFLICT (name) DO NOTHING
                RETURNING id""",
            (name, description, content, tags, is_global),
        )
        row = cur.fetchone()
        if row:
            label = "GLOBAL" if is_global else "local"
            print(f"  OK   {name} ({label}, id={row[0]})")
            return "ok"
        else:
            print(f"  SKIP {name} — already exists (use --force to overwrite)")
            return "skip"
    except Exception as e:
        print(f"  ERR  {name} — {e}")
        return "err"


def main():
    skills_dir = Path(__file__).resolve().parent.parent / "inotagent" / "skills"
    if not skills_dir.exists():
        print(f"Skills directory not found: {skills_dir}")
        sys.exit(1)

    # Parse args
    force = "--force" in sys.argv
    reset_name = None
    if "--reset" in sys.argv:
        idx = sys.argv.index("--reset")
        if idx + 1 < len(sys.argv):
            reset_name = sys.argv[idx + 1]
        else:
            print("Usage: --reset SKILL_NAME")
            sys.exit(1)

    # DB connection from env
    host = os.environ.get("POSTGRES_HOST", "localhost")
    port = os.environ.get("POSTGRES_PORT", "5432")
    db = os.environ.get("POSTGRES_DB", "inotives")
    user = os.environ.get("POSTGRES_USER", "postgres")
    password = os.environ.get("POSTGRES_PASSWORD", "")
    schema = os.environ.get("PLATFORM_SCHEMA", "platform")

    # Validate schema name (same check as inotagent/db/pool.py)
    if not re.match(r"^[a-z_][a-z0-9_]*$", schema):
        print(f"Invalid PLATFORM_SCHEMA: {schema!r}")
        sys.exit(1)

    conninfo = f"host={host} port={port} dbname={db} user={user} password={password}"

    skill_files = sorted(skills_dir.glob("*.md"))
    print(f"Found {len(skill_files)} skill files in {skills_dir}")

    # Parse all files
    skills = []
    for path in skill_files:
        skill = parse_skill_file(path)
        if skill:
            skills.append(skill)

    # Filter to specific skill if --reset
    if reset_name:
        skills = [s for s in skills if s["name"] == reset_name]
        if not skills:
            print(f"Skill '{reset_name}' not found in files")
            sys.exit(1)
        force = True  # reset implies force for that skill

    if force and not reset_name:
        print("Force mode: deleting all import-created skills before re-importing")

    imported = 0
    skipped = 0

    with psycopg.connect(conninfo, autocommit=True) as conn:
        if force and not reset_name:
            conn.execute(f"DELETE FROM {schema}.skills WHERE created_by = 'import'")
            print("  Deleted all import-created skills")

        for skill in skills:
            result = import_skill(conn, schema, skill, force=bool(reset_name))
            if result == "ok":
                imported += 1
            else:
                skipped += 1

    print(f"\nDone: {imported} imported, {skipped} skipped")


if __name__ == "__main__":
    main()
