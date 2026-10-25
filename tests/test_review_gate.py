from __future__ import annotations

import io

from Brief.pipeline.review_gate import ReviewGate
from Brief.tools.indexer_tool import create_indexer_tool
from Brief.tools.outline_review import create_outline_review_tool


def test_explicit_auto_approve_overrides_environment(monkeypatch) -> None:
    monkeypatch.setenv("BRIEF_AUTO_APPROVE", "1")
    gate = ReviewGate(auto_approve=False, line_reader=lambda _timeout: "change it")

    assert gate.review("review") == "change it"


def test_explicit_interactive_review_does_not_auto_approve(monkeypatch) -> None:
    monkeypatch.setenv("BRIEF_AUTO_APPROVE", "1")
    gate = ReviewGate(
        auto_approve=False,
        output_stream=io.StringIO(),
        line_reader=lambda _timeout: "retitle figure 2",
    )

    assert gate.review("review") == "retitle figure 2"


def test_outline_review_returns_resume_feedback(monkeypatch) -> None:
    monkeypatch.setattr(
        "Brief.tools.outline_review.interrupt",
        lambda _payload: "Rewrite section 6",
    )

    result = create_outline_review_tool().func(outline_path="/tmp/outline.md")

    assert result == "Rewrite section 6"


def test_indexer_review_returns_resume_feedback(monkeypatch) -> None:
    monkeypatch.setattr(
        "Brief.tools.indexer_tool.index_project",
        lambda **_kwargs: "/tmp/index.md",
    )
    monkeypatch.setattr(
        "Brief.tools.indexer_tool.interrupt",
        lambda _payload: "Correct the QC caption",
    )
    run_indexer = create_indexer_tool(None, None, "/tmp/project").func

    result = run_indexer(
        background="background",
        output_lang="zh-CN",
        output_path="/tmp/project/output/report.md",
    )

    assert "index_path: /tmp/index.md" in result
    assert "review_feedback: Correct the QC caption" in result
