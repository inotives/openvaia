"""Delegate tool — spawn ephemeral sub-agents using skills as expertise."""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)

DELEGATE_TOOL = {
    "name": "delegate",
    "description": (
        "Delegate a task to a specialist sub-agent. The sub-agent uses a specific skill "
        "as its expertise and returns a focused result. Use for code review, QA checks, "
        "security scans, or any task where specialist knowledge improves quality."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "skill": {
                "type": "string",
                "description": "Skill name to use as the sub-agent's expertise (e.g., code_review, vulnerability_scanning)",
            },
            "task": {
                "type": "string",
                "description": "The task, question, or content for the sub-agent to analyze",
            },
            "model": {
                "type": "string",
                "description": "Optional: model override (default: your current model)",
            },
        },
        "required": ["skill", "task"],
    },
}

_DB_NOT_CONNECTED = "Error: Database not connected. Delegate tool requires DB for skill loading."


class DelegateTool:
    """Spawn ephemeral sub-agents that use a skill as their system prompt."""

    def __init__(self, agent_name: str, models: dict, config, db_available: bool = False):
        self.agent_name = agent_name
        self.models = models
        self.config = config
        self.db_available = db_available

    async def delegate(self, skill: str, task: str, model: str | None = None) -> str:
        if not self.db_available:
            return _DB_NOT_CONNECTED

        # Load skill from DB
        from inotagent.db.skills import load_skill_by_name
        skill_data = await load_skill_by_name(skill)
        if not skill_data:
            return f"Error: Skill '{skill}' not found. Check available skills in the Admin UI."

        # Resolve model
        model_id = model or self.config.model_id
        if model_id not in self.models:
            return f"Error: Model '{model_id}' not found in registry."

        # Single LLM call — no tools, no history, no memory
        from inotagent.llm.client import LLMMessage
        from inotagent.llm.factory import chat_with_fallback

        try:
            response = await chat_with_fallback(
                models=self.models,
                model_id=model_id,
                fallbacks=self.config.fallbacks,
                system=skill_data["content"],
                messages=[LLMMessage(role="user", content=task)],
                max_tokens=2048,
            )
            logger.info(
                f"[{self.agent_name}] Sub-agent ({skill}) via {model_id}: "
                f"{len(response.content)} chars"
            )
            return response.content
        except Exception as e:
            logger.error(f"[{self.agent_name}] Sub-agent ({skill}) failed: {e}")
            return f"Error: Sub-agent failed — {e}"
