"""Indexer tool for the ReAct agent: runs index_project with HITL interrupt."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Callable

from langchain_core.language_models import LanguageModelLike
from langchain_core.tools import tool
from langgraph.types import interrupt

from ..indexer import index_project


def create_indexer_tool(
    chat_model: LanguageModelLike,
    mmchat_model: LanguageModelLike,
    project_path: str,
    *,
    repo_root: str | Path | None = None,
) -> Callable:
    """Create a tool that runs the indexer and returns the index.md path."""

    @tool
    def run_indexer(background: str, output_lang: str, output_path: str) -> str:
        """Run the indexer to scan project files and generate captions.

        Args:
            background: Research background description.
            output_lang: Output language (e.g., "zh-CN", "en").
            output_path: Path to the output report file.

        Returns:
            The absolute path to the generated index.md file.
        """
        resolved_output_path = _resolve_output_path(output_path, repo_root)
        index_path = index_project(
            project_path=project_path,
            mmchat_model=mmchat_model,
            background=background,
            output_lang=output_lang,
            output_path=resolved_output_path,
            chat_model=chat_model,
        )
        # Trigger human-in-the-loop interrupt
        interrupt(
            {
                "type": "indexer_review",
                "index_path": index_path,
                "message": "Indexer 完成，请审阅。编辑后按 Enter 继续...",
            }
        )
        return index_path

    return run_indexer


def _resolve_output_path(output_path: str, repo_root: str | Path | None) -> str:
    """Resolve DeepAgents virtual paths while preserving legacy absolute paths."""
    if not repo_root or not output_path.startswith("/"):
        return output_path
    root = Path(repo_root).expanduser().resolve()
    candidate = (root / output_path.lstrip("/").replace("/", os.sep)).resolve()
    try:
        candidate.relative_to(root)
    except ValueError as exc:
        raise ValueError(f"Indexer output path escapes repository root: {output_path}") from exc
    return str(candidate)
