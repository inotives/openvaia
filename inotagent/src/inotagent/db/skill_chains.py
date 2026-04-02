"""Skill chain matching and loading for dynamic skill equipping."""

from __future__ import annotations

import json
import logging

from inotagent.db.pool import get_connection, get_schema

logger = logging.getLogger(__name__)


async def match_chain(tags: list[str], title: str = "") -> dict | None:
    """Match a task to a skill chain by tags first, then keywords.

    Priority:
    1. Exact tag match (most specific first — more tags matched = better)
    2. Keyword match on title
    3. None (no chain matched — fall back to static skills)
    """
    schema = get_schema()

    if not tags and not title:
        return None

    async with get_connection() as conn:
        # Try tag matching — find chains where ANY match_tag overlaps with task tags
        if tags:
            cur = await conn.execute(
                f"""SELECT id, name, description, match_tags, match_keywords, steps,
                    (SELECT COUNT(*) FROM unnest(match_tags) mt WHERE mt = ANY(%s::text[])) AS match_count
                    FROM {schema}.skill_chains
                    WHERE is_active = true AND match_tags && %s::text[]
                    ORDER BY match_count DESC
                    LIMIT 1""",
                (tags, tags),
            )
            row = await cur.fetchone()
            if row:
                chain = dict(row)
                chain["steps"] = json.loads(chain["steps"]) if isinstance(chain["steps"], str) else chain["steps"]
                logger.info(f"Chain matched by tags: {chain['name']} (tags: {tags})")
                return chain

        # Try keyword matching on title
        if title:
            title_lower = title.lower()
            cur = await conn.execute(
                f"""SELECT id, name, description, match_tags, match_keywords, steps
                    FROM {schema}.skill_chains
                    WHERE is_active = true AND match_keywords IS NOT NULL""",
            )
            rows = await cur.fetchall()
            for row in rows:
                chain = dict(row)
                keywords = chain.get("match_keywords") or []
                for kw in keywords:
                    if kw.lower() in title_lower:
                        chain["steps"] = json.loads(chain["steps"]) if isinstance(chain["steps"], str) else chain["steps"]
                        logger.info(f"Chain matched by keyword '{kw}': {chain['name']} (title: {title})")
                        return chain

    return None


async def get_chain_step_skills(chain: dict, step_index: int = 0) -> list[str]:
    """Get skill names for a specific step in a chain."""
    steps = chain.get("steps", [])
    if not steps or step_index >= len(steps):
        return []
    step = steps[step_index]
    return step.get("skills", [])


async def set_task_chain_state(task_key: str, chain: dict) -> None:
    """Set initial chain_state on a task when it's first matched to a chain."""
    schema = get_schema()
    steps = chain.get("steps", [])
    if not steps:
        return

    state = json.dumps({
        "current_phase": steps[0].get("phase", ""),
        "current_step_index": 0,
        "completed_phases": [],
        "active_skills": steps[0].get("skills", []),
        "chain_name": chain["name"],
    })

    async with get_connection() as conn:
        await conn.execute(
            f"""UPDATE {schema}.tasks
                SET chain_id = %s, chain_state = %s
                WHERE key = %s AND chain_id IS NULL""",
            (chain["id"], state, task_key),
        )
    logger.info(f"Chain state set: task={task_key}, chain={chain['name']}, phase={steps[0].get('phase')}")


async def advance_chain_phase(task_key: str, completed_phase: str) -> dict | None:
    """Advance a task's chain to the next phase after a phase completes.

    If the next step has a gate (e.g., human_approval), the task is set to
    'review' status so human can approve before the agent continues.

    Returns the new step dict (with skills + gate) or None if chain is done.
    """
    schema = get_schema()

    async with get_connection() as conn:
        # Get current chain_state and chain steps
        cur = await conn.execute(
            f"""SELECT t.chain_state, sc.steps
                FROM {schema}.tasks t
                JOIN {schema}.skill_chains sc ON sc.id = t.chain_id
                WHERE t.key = %s AND t.chain_id IS NOT NULL""",
            (task_key,),
        )
        row = await cur.fetchone()
        if not row:
            return None

        state = row["chain_state"]
        if isinstance(state, str):
            state = json.loads(state)
        steps = row["steps"]
        if isinstance(steps, str):
            steps = json.loads(steps)

        # Advance to next step
        completed = state.get("completed_phases", [])
        if completed_phase not in completed:
            completed.append(completed_phase)

        current_idx = state.get("current_step_index", 0) + 1
        if current_idx >= len(steps):
            # Chain complete
            state["completed_phases"] = completed
            state["current_phase"] = "done"
            state["current_step_index"] = len(steps) - 1
            state["active_skills"] = []
        else:
            next_step = steps[current_idx]
            state["completed_phases"] = completed
            state["current_phase"] = next_step.get("phase", "")
            state["current_step_index"] = current_idx
            state["active_skills"] = next_step.get("skills", [])

        # Check if next step has a gate
        next_step = steps[current_idx] if current_idx < len(steps) else None
        has_gate = next_step and next_step.get("gate") == "human_approval"

        if has_gate:
            # Set task to 'review' — human must approve before agent continues
            state["gate_pending"] = True
            state["gate_type"] = "human_approval"
            state["gate_message"] = (
                f"Phase '{completed_phase}' complete. "
                f"Next phase '{next_step.get('phase', '')}' requires human approval. "
                f"Review the document and set task back to 'todo' to continue."
            )
            await conn.execute(
                f"UPDATE {schema}.tasks SET chain_state = %s, status = 'review' WHERE key = %s",
                (json.dumps(state), task_key),
            )
            logger.info(
                f"Chain gate: task={task_key}, completed={completed_phase}, "
                f"next={next_step.get('phase')} requires human_approval — task set to review"
            )
        else:
            await conn.execute(
                f"UPDATE {schema}.tasks SET chain_state = %s WHERE key = %s",
                (json.dumps(state), task_key),
            )

    new_phase = state.get("current_phase", "done")
    logger.info(f"Chain advanced: task={task_key}, completed={completed_phase}, now={new_phase}")

    if current_idx < len(steps):
        return steps[current_idx]
    return None


async def clear_gate(task_key: str) -> None:
    """Clear a pending gate on a task (after human approves)."""
    schema = get_schema()
    async with get_connection() as conn:
        cur = await conn.execute(
            f"SELECT chain_state FROM {schema}.tasks WHERE key = %s",
            (task_key,),
        )
        row = await cur.fetchone()
        if not row or not row["chain_state"]:
            return

        state = row["chain_state"]
        if isinstance(state, str):
            state = json.loads(state)

        state.pop("gate_pending", None)
        state.pop("gate_type", None)
        state.pop("gate_message", None)

        await conn.execute(
            f"UPDATE {schema}.tasks SET chain_state = %s WHERE key = %s",
            (json.dumps(state), task_key),
        )
    logger.info(f"Gate cleared: task={task_key}")


async def load_skills_by_names(skill_names: list[str]) -> list[dict]:
    """Load skills by their names. Returns list of {id, name, content}."""
    if not skill_names:
        return []

    schema = get_schema()
    async with get_connection() as conn:
        # Build parameterized query for IN clause
        placeholders = ", ".join(["%s"] * len(skill_names))
        cur = await conn.execute(
            f"""SELECT id, name, content
                FROM {schema}.skills
                WHERE name IN ({placeholders})
                  AND enabled = true
                  AND COALESCE(status, 'active') = 'active'""",
            skill_names,
        )
        rows = await cur.fetchall()
    return [dict(r) for r in rows]
