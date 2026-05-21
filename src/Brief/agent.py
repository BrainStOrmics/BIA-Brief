"""ReAct agent definition for report generation."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

from langchain.agents import create_agent
from langchain_core.language_models import LanguageModelLike


def load_agent_prompt() -> str:
    """Load the agent system prompt from prompts/agent.md."""
    prompt_path = Path(__file__).parent / "prompts" / "agent.md"
    with open(prompt_path, "r", encoding="utf-8") as f:
        return f.read()


def create_brief_agent(
    chat_model: LanguageModelLike,
    *,
    system_prompt: str,
    tools: list,
    checkpointer=None,
    store=None,
    **kwargs,
):
    """Create a ReAct agent for bioinformatics report generation.

    Args:
        chat_model: The language model for the agent.
        system_prompt: System prompt defining the agent's role and workflow.
        tools: List of tools available to the agent.
        checkpointer: Optional checkpointer for persistence.
        store: Optional store for cross-thread persistence.
        **kwargs: Additional arguments passed to create_agent.

    Returns:
        CompiledStateGraph: The compiled agent graph.
    """
    return create_agent(
        model=chat_model,
        tools=tools,
        system_prompt=system_prompt,
        checkpointer=checkpointer,
        store=store,
        **kwargs,
    )
