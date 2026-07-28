"""DeepAgents runtime assembly for report generation."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from deepagents import create_deep_agent
from deepagents.backends import FilesystemBackend
from deepagents.backends.protocol import WriteResult
from langgraph.checkpoint.memory import MemorySaver

from ..agent import load_agent_prompt
from ..tools.indexer_tool import create_indexer_tool
from ..tools.outline_review import create_outline_review_tool


class ReportFilesystemBackend(FilesystemBackend):
    """Filesystem adapter that permits safe replacement of report artifacts.

    DeepAgents' default ``write_file`` is intentionally create-only. Report
    generation is rerunnable, so replacing an existing report artifact is part
    of the pipeline contract. Path resolution and virtual-root checks remain
    delegated to ``FilesystemBackend``.
    """

    def write(self, file_path: str, content: str) -> WriteResult:
        try:
            resolved_path = self._resolve_path(file_path)
            resolved_path.parent.mkdir(parents=True, exist_ok=True)
            flags = os.O_WRONLY | os.O_CREAT | os.O_TRUNC
            if hasattr(os, "O_NOFOLLOW"):
                flags |= os.O_NOFOLLOW
            fd = os.open(resolved_path, flags, 0o644)
            with os.fdopen(fd, "w", encoding="utf-8", newline="") as stream:
                stream.write(content)
            return WriteResult(path=file_path)
        except (OSError, UnicodeEncodeError, RuntimeError) as exc:
            return WriteResult(error=f"Error writing file '{file_path}': {exc}")


def to_virtual_path(path: str | Path, repo_root: str | Path) -> str:
    """Convert an in-repository path to a safe DeepAgents virtual path."""
    root = Path(repo_root).expanduser().resolve()
    target = Path(path).expanduser().resolve()
    try:
        relative = target.relative_to(root)
    except ValueError as exc:
        raise ValueError(f"Agent path must be inside repository root: {target}") from exc
    return "/" + relative.as_posix()


def build_report_agent(
    *,
    chat_model: Any,
    mmchat_model: Any,
    project_path: str | Path,
    repo_root: str | Path,
    checkpointer: Any | None = None,
    store: Any | None = None,
    debug: bool = False,
):
    """Build the report agent and its Indexer sub-agent."""
    root = Path(repo_root).expanduser().resolve()
    backend = ReportFilesystemBackend(root_dir=root, virtual_mode=True)
    indexer_tool = create_indexer_tool(
        chat_model,
        mmchat_model,
        str(Path(project_path).expanduser().resolve()),
        repo_root=root,
    )
    indexer_subagent = {
        "name": "indexer",
        "description": "Scan project figures, scripts, and tables, then write index.md with captions and summaries.",
        "system_prompt": (
            "You are the project indexing sub-agent. Call run_indexer exactly once "
            "with the background, output language, and virtual output path supplied "
            "by the parent agent. After the tool resumes from review, report the "
            "virtual index.md path and stop. Do not write the report body."
        ),
        "model": chat_model,
        "tools": [indexer_tool],
    }
    return create_deep_agent(
        model=chat_model,
        tools=[create_outline_review_tool()],
        system_prompt=load_agent_prompt(),
        subagents=[indexer_subagent],
        backend=backend,
        checkpointer=checkpointer or MemorySaver(),
        store=store,
        debug=debug,
    )
