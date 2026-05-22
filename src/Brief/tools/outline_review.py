"""Outline review tool for human-in-the-loop workflow."""

from __future__ import annotations

from typing import Callable

from langchain_core.tools import tool
from langgraph.types import interrupt


def create_outline_review_tool() -> Callable:
    """Create a tool that pauses for human review of the report outline."""

    @tool
    def review_outline(outline_path: str) -> str:
        """Pause for human review of the report outline.

        After human review, the resume value contains the reviewer's feedback.
        Agent should re-generate the outline if feedback contains modification
        requests, or proceed to the next step if feedback indicates approval.

        Args:
            outline_path: Path to the outline file for review.

        Returns:
            Reviewer feedback string from resume value.
        """
        interrupt({
            "type": "outline_review",
            "outline_path": outline_path,
            "message": (
                f"Report outline 已生成，请审阅 {outline_path}。"
                "确认章节结构和图号分配。如有修改意见请输入，通过则按 Enter 继续。"
            ),
        })
        return "Outline 审阅完成"

    return review_outline
