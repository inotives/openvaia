"""Prompt enhancer — single-pass LLM call to refine rough instructions."""

from __future__ import annotations

import logging

from inotagent.config.models import ModelConfig
from inotagent.config.platform import PromptGenConfig
from inotagent.llm.client import LLMMessage, LLMResponse
from inotagent.llm.factory import create_client

logger = logging.getLogger(__name__)

PROMPT_GEN_SYSTEM = """You are a prompt engineering expert for the OpenVAIA AI agent platform.

Your job: take the user's rough instruction and rewrite it into a clear, structured prompt that an AI agent can execute effectively.

The agents have these capabilities:
- Shell commands, file read/write, browser (web research)
- Task management (task_create, task_update, task_list)
- Memory (memory_store, memory_search)
- Research reports (research_store, research_search)
- Discord/Slack/Telegram messaging
- Git operations (clone, commit, push via shell)

When enhancing a prompt:
1. Clarify the objective — what exactly should the agent deliver?
2. Specify scope — what's in and out of bounds?
3. Define output format — report, code, summary, data?
4. Mention relevant tools if applicable
5. Add success criteria — how does the human know it's done?

Rules:
- Respond in a single pass. Do not ask follow-up questions.
- Return ONLY the enhanced prompt, no commentary or explanation.
- Keep it concise but thorough — aim for 100-300 words.
- Match the complexity to the task — simple tasks get simple prompts."""


async def enhance_prompt(
    instruction: str,
    config: PromptGenConfig,
    models: dict[str, ModelConfig],
) -> tuple[str, str]:
    """Enhance a rough instruction into a structured prompt.

    Returns (enhanced_prompt, model_used). Tries default model, then fallbacks.
    Raises RuntimeError if all models fail.
    """
    chain = [config.default_model] + config.fallbacks

    last_error = ""
    for model_id in chain:
        if model_id not in models:
            continue
        model_config = models[model_id]

        try:
            client = create_client(model_config)
            response: LLMResponse = await client.chat(
                model=model_config.model,
                system=PROMPT_GEN_SYSTEM,
                messages=[LLMMessage(role="user", content=instruction)],
                max_tokens=config.max_tokens,
            )
            content = response.content.strip()
            if content:
                logger.info(f"Prompt enhanced via {model_id} ({len(content)} chars)")
                return content, model_id
        except Exception as e:
            last_error = str(e)
            logger.warning(f"Prompt gen: {model_id} failed: {e}, trying next")

    raise RuntimeError(f"All prompt gen models failed. Last error: {last_error}")
