"""ReAct agent definition for report generation."""

from __future__ import annotations

from pathlib import Path


def load_agent_prompt() -> str:
    """Load the agent system prompt from prompts/agent.md."""
    prompt_path = Path(__file__).parent / "prompts" / "agent.md"
    with open(prompt_path, "r", encoding="utf-8") as f:
        return f.read()
