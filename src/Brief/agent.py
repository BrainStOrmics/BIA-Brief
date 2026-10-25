"""ReAct agent definition for report generation."""

from __future__ import annotations

from pathlib import Path


def load_agent_prompt(prompt_name: str = "agent.md") -> str:
    """Load an agent system prompt from the packaged prompts directory."""
    prompt_path = Path(__file__).parent / "prompts" / prompt_name
    if not prompt_path.is_file():
        raise FileNotFoundError(f"Agent prompt not found: {prompt_path}")
    with open(prompt_path, "r", encoding="utf-8") as f:
        return f.read()
